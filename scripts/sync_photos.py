# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.32",
#     "pillow>=11",
#     "pyyaml>=6",
# ]
# ///
"""Mirror the trip's iCloud shared album into the site.

Reads the album through its public link (no Apple ID sign-in), keeps photos
added by allowed people and taken during the trip, and writes:

  assets/photos/<id>.jpg        web-sized photo (location data stripped)
  assets/photos/<id>-thumb.jpg  thumbnail
  _data/photos.json             what the page reads

Photos removed from the album are removed from the site on the next run.

Environment:
  ICLOUD_ALBUM_URL   the shared album link (or just its token)
  PHOTO_UPLOADERS    comma-separated iCloud user IDs allowed to publish.
                     Empty means only the album owner.

Run locally:  ICLOUD_ALBUM_URL=... uv run scripts/sync_photos.py
"""

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "assets" / "photos"
DATA_FILE = ROOT / "_data" / "photos.json"
DAYS_FILE = ROOT / "_data" / "days.yml"

API = "https://ckdatabasews.icloud.com/database/1/com.apple.photos.cloud/production"
HEADERS = {"content-type": "text/plain", "Origin": "https://photos.icloud.com"}
PHOTO_EDGE = 1600  # longest side of the web-sized photo
THUMB_EDGE = 480


def album_token(value: str) -> str:
    """Accept the full link or just the token at the end of it."""
    match = re.search(r"([A-Za-z0-9_-]{20,})/?$", value.strip())
    if not match:
        sys.exit("ICLOUD_ALBUM_URL doesn't look like a shared album link")
    return match.group(1)


def resolve(token: str) -> dict:
    """Swap the link token for the album's zone and a short-lived read token."""
    r = requests.post(
        f"{API}/public/records/resolve",
        params={"remapEnums": "true", "getCurrentSyncToken": "true", "sharing_url_key": token},
        data=json.dumps({"shortGUIDs": [{"value": token}]}),
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()["results"][0]
    if "anonymousPublicAccess" not in result:
        sys.exit("The album link isn't public. Turn on Public Website for the shared album.")
    return result


def fetch_records(token: str, share: dict) -> list[dict]:
    access = share["anonymousPublicAccess"]
    base = access["databasePartition"].replace(":443", "")
    records, sync_token = [], None
    while True:
        zone = {"zoneID": share["zoneID"], "reverse": False}
        if sync_token:
            zone["syncToken"] = sync_token
        r = requests.post(
            f"{base}/database/1/com.apple.photos.cloud/production/shared/changes/zone",
            params={
                "remapEnums": "true",
                "getCurrentSyncToken": "true",
                "sharing_url_key": token,
                "publicAccessAuthToken": access["token"],
            },
            data=json.dumps({"zones": [zone]}),
            headers=HEADERS,
            timeout=60,
        )
        r.raise_for_status()
        page = r.json()["zones"][0]
        records += page.get("records", [])
        sync_token = page.get("syncToken")
        if not page.get("moreComing"):
            return records


def field(record: dict, name: str, default=None):
    return record.get("fields", {}).get(name, {}).get("value", default)


def trip_days() -> set[str]:
    days = yaml.safe_load(DAYS_FILE.read_text())
    return {str(d["date"]) for d in days}


def people(share: dict) -> dict[str, str]:
    """iCloud user ID -> first name, for the "added by" line. Never stores emails."""
    names = {}
    for p in share.get("share", {}).get("participants", []):
        ident = p.get("userIdentity", {})
        rid = ident.get("userRecordName")
        if rid:
            names[rid] = ident.get("nameComponents", {}).get("givenName", "")
    return names


def download(url: str) -> Image.Image:
    r = requests.get(url.replace("${f}", "photo.jpg"), timeout=120)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    # Bake in the rotation, then drop all metadata (GPS included) by saving fresh pixels.
    return ImageOps.exif_transpose(img).convert("RGB")


def save(img: Image.Image, edge: int, path: Path, quality: int) -> tuple[int, int]:
    img = img.copy()
    img.thumbnail((edge, edge), Image.LANCZOS)
    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return img.size


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--pretend-day",
        metavar="YYYY-MM-DD",
        help="testing only: put photos taken outside the trip on this day instead of skipping them",
    )
    args = ap.parse_args()

    token = album_token(os.environ.get("ICLOUD_ALBUM_URL", ""))
    share = resolve(token)
    records = fetch_records(token, share)
    names = people(share)

    owner = share["zoneID"]["ownerRecordName"]
    allowed = {u.strip() for u in os.environ.get("PHOTO_UPLOADERS", "").split(",") if u.strip()} or {owner}
    days = trip_days()

    masters = {r["recordName"]: r for r in records if r["recordType"] == "CPLMaster" and not r.get("deleted")}
    captions = {r["recordName"]: field(r, "caption", "") for r in records if r["recordType"] == "CPLPost"}

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    photos, skipped = [], {"outside trip": 0, "hidden": 0, "video": 0, "not allowed": 0}
    strangers = {}

    for asset in records:
        if asset["recordType"] != "CPLAsset" or asset.get("deleted"):
            continue
        if field(asset, "isHidden", 0) or field(asset, "trashReason", 0):
            skipped["hidden"] += 1
            continue
        by = asset.get("created", {}).get("userRecordName", "")
        if by not in allowed:
            skipped["not allowed"] += 1
            strangers[by] = names.get(by, "someone not in the album")
            continue
        master = masters.get((field(asset, "masterRef") or {}).get("recordName"))
        medium = master and field(master, "resJPEGMedRes")
        # Videos (for now) have a duration and no still JPEG. Live Photos count as photos.
        if not medium or field(asset, "duration", 0):
            skipped["video"] += 1
            continue

        # When and where-in-time it was taken: the phone records the UTC moment plus its offset.
        offset = dt.timedelta(seconds=field(asset, "timeZoneOffset", 0))
        taken = dt.datetime.fromtimestamp(field(asset, "assetDate") / 1000, dt.timezone(offset))
        day = taken.date().isoformat()
        if day not in days:
            if not args.pretend_day:
                skipped["outside trip"] += 1
                continue
            day = args.pretend_day

        pid = asset["recordName"].lower()
        big, thumb = PHOTO_DIR / f"{pid}.jpg", PHOTO_DIR / f"{pid}-thumb.jpg"
        if big.exists() and thumb.exists():
            with Image.open(big) as im:
                w, h = im.size
        else:
            print(f"downloading {pid} ({day})")
            img = download(medium["downloadURL"])
            w, h = save(img, PHOTO_EDGE, big, 82)
            save(img, THUMB_EDGE, thumb, 78)

        photos.append({
            "id": pid,
            "day": day,
            "taken": taken.isoformat(timespec="minutes"),
            "caption": captions.get(field(asset, "assetBatchId", ""), "") or "",
            "by": names.get(by, ""),
            "src": f"/assets/photos/{pid}.jpg",
            "thumb": f"/assets/photos/{pid}-thumb.jpg",
            "w": w,
            "h": h,
        })

    photos.sort(key=lambda p: p["taken"])

    # Anything no longer in the album comes off the site too.
    keep = {p["id"] for p in photos}
    for f in PHOTO_DIR.glob("*.jpg"):
        if f.stem.removesuffix("-thumb") not in keep:
            f.unlink()

    DATA_FILE.write_text(json.dumps(photos, indent=1, ensure_ascii=False) + "\n")

    skips = ", ".join(f"{n} {k}" for k, n in skipped.items() if n) or "none"
    print(f"{len(photos)} photos published; skipped: {skips}")
    for rid, name in strangers.items():
        print(f"  not published, added by {name}: {rid}  (add to PHOTO_UPLOADERS to allow)")


if __name__ == "__main__":
    main()
