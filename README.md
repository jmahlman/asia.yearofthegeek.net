# Kimchi, Katsu & a Very Big Boat

A day-by-day tracker for our Korea and Japan trip (Sep 29 to Oct 20, 2026), so family and friends can see where we are, what we're up to, and what time it is for us.

It's a plain Jekyll site with no plugins, so GitHub Pages builds it on its own. The timeline is the home page (built from `index.html`). Old `/map/` links redirect there.

## What's on the page

- **Day tiles.** One tile per stop, in order. Back-to-back days in the same place (same `title` and `coords`) are merged into one tile, with a section per day inside it.
- **Background map.** As you scroll, the map glides to the day in focus and marks it with a small dot. Sea days fade to a photo of the Celebrity Millennium, and travel days zoom out to show the flight path. The tiles before and after the focused one fade out.
- **Our avatar (the tracker).** The pixel-art us in `assets/img/us.png` stands wherever we *actually* are right now. It does not follow the reader's scrolling. Before and after the trip it's at home in Philly. During flights it moves along the flight path in real time.
- **Buttons (top right).**
  - **Start**: back to the top of the page. In the overview it reads **Reset** and zooms back out to the whole trip.
  - **Today**: jumps to today's tile, or zooms to today's stop in the overview. Only shown during the trip.
  - **Overview**: hides the tiles and shows the whole route with a marker per stop. The map becomes draggable and zoomable. Clicking a stop zooms in and offers **Open this day →**.
  - **Calendar**: a Sunday-to-Saturday grid of the trip. Click a day to jump to it.
- **Clocks (bottom).** "Your time" (the reader's device) next to our time, with the hour difference and where we are. Our side turns yellow when it's already a different date for us.
- **Time zone help on every tile.** For example: "Japan time, 13 hours ahead of you. Noon there is 11:00 PM the day before for you." Each schedule time also shows the reader's own time underneath, such as "Thu, Oct 8, 6:00 PM your time".
- **Today.** During the trip, the page opens on today's tile. It's highlighted yellow and marked "We are here!", and the header says where we are.
- **After the trip.** Once we've landed back in Philly, the header says we made it home, and a **We're home!** wrap-up tile appears at the end with trip stats (days, countries, ports, days at sea, miles flown, parties). The map zooms to Philly with us standing at home. This tile is the natural spot to add trip photos later.
- **Photos.** Tiles with photos get a **📷 Show pictures** button that opens a full-screen viewer (swipe or arrow keys, captions, who took it). Tiles without photos show nothing. See [Photos](#photos) below.
- **Parties.** A day with `celebrate:` gets a banner, plus confetti and balloons when it scrolls into focus (Alessa's 40th on Oct 6).
- **Phones and narrow windows (under 900px).** A "story map" layout: the focused tile sits at the bottom of the screen with the map showing above it. Details fold behind a **Show details** / **Show all N days** button.

People who've turned on "reduce motion" on their device get the same page without the animations.

## Editing the trip

Nearly everything comes from **`_data/days.yml`**, with one entry per calendar day. Keep the entries in date order. The calendar, overview, clocks and tile merging all follow automatically.

```yaml
- date: 2026-10-09
  emoji: "🌋"                   # shown on the timeline, calendar, and overview marker
  mode: land                    # land, sea, or air (sets colors and map behavior)
  tz: Asia/Tokyo                # time zone the schedule times are in
  coords: [31.5660, 130.5690]   # [lat, lng] for the map
  title: Kagoshima, Japan       # tiles with the same title + coords on consecutive days merge
  blurb: A city with an active volcano right across the bay.
  schedule:
    - time: "7:00 AM"           # "h:mm AM/PM" gets converted to the reader's time; anything else ("Evening") is shown as-is
      what: Arrive in port
      link: https://example.com # optional
      tz: Asia/Seoul            # optional, overrides the day's tz (flight days use this per airport)
      date: 2026-10-10          # optional, if this item happens on a different calendar day
  port: Kagoshima Port, Kagoshima, Japan   # optional, links to Google Maps
  stay:                         # optional hotel (name, address, phone)
    name: ...
    address: ...
    phone: "+81 ..."
  sleeping: Celebrity Millennium          # optional, shown when there's no stay
  celebrate: Happy birthday, Alessa!      # optional party banner
  celebrate_note: The big 4-0.            # optional line under the banner
```

Air days use `route:` (a list of `[lat, lng]` stops, e.g. PHL → SEA → ICN) instead of `coords`. Hotels that repeat across days use YAML anchors (`stay: &mondrian` … `stay: *mondrian`).

### Settings in `_config.yml`

| Key | What it does |
|---|---|
| `title`, `description` | Page title and description |
| `url` | `https://asia.yearofthegeek.net` |
| `travelers` | Name on our clock ("John and Alessa") |
| `ship_photo`, `ship_credit` | The sea-day background photo and its credit line in the footer |
| `home_title`, `home_message` | Heading and message on the wrap-up tile after the trip |

### Hard-coded in `index.html`

If the flights change, update these in the script at the bottom of `index.html`:

- `start` and `TRIP_END`: the first departure (Sep 29, 7:05 AM Philly) and the final arrival (Oct 20, 6:19 PM Philly). After `TRIP_END` the wrap-up tile appears.
- `flights`: when each flight is in the air (landing in Seoul, and leaving Tokyo), used for the clocks and moving the avatar
- `HOME`: Philly's coordinates, where the avatar waits before and after the trip
- "Today" follows the Korea/Japan calendar (UTC+9)

## Photos

Photos come from the **"Asia 2026" iCloud Shared Album** (Public Website turned on). Add photos from the Photos app as usual; they land on the day they were taken.

- A GitHub Action (`.github/workflows/sync-photos.yml`) runs `scripts/sync_photos.py` every 8 hours. To run it right away, go to the **Actions** tab > **Sync photos from iCloud** > **Run workflow**.
- Each photo is filed by the local date and time the phone recorded when it was taken. Photos from outside the trip dates are skipped.
- Photos are resized (1600px plus a 480px thumbnail) and all metadata, including GPS location, is stripped. They're saved to `assets/photos/`, and `_data/photos.json` lists them.
- **Captions:** the comment typed when adding photos to the album becomes the caption. It applies to every photo added in that batch, so add photos one at a time to caption them separately.
- **Removing a photo:** delete it from the shared album (or hide it). It comes off the site on the next sync.
- **Who can publish:** only the album owner, unless the `PHOTO_UPLOADERS` repository variable lists iCloud user IDs (comma-separated). The sync log prints the ID of anyone whose photos were skipped, so they can be added.
- Videos are skipped for now. Live Photos show as stills.

Setup: the album link is stored as the repository secret `ICLOUD_ALBUM_URL` (Settings > Secrets and variables > Actions).

Run it locally:

```bash
ICLOUD_ALBUM_URL="<album link>" uv run scripts/sync_photos.py
```

Add `--pretend-day 2026-10-02` to put photos taken outside the trip on that day, for testing. Don't commit those results.

## Previewing

- **Any day as "today":** add `?date=2026-10-06` to the URL. It moves the highlight, the avatar and the clocks (set to noon that day).
- **After the trip:** use any later date, like `?date=2026-10-21`, to see the wrap-up.
- **Phone layout:** use a narrow window or your browser's device mode.

## Run it locally

Needs Docker.

```bash
docker compose up -d
```

Open http://localhost:4000/. Edits to `_data/days.yml`, `index.html` and `assets/` rebuild automatically. Refresh if the page doesn't update. Changes to `_config.yml` need a restart:

```bash
docker compose restart jekyll
```

Stop it with `docker compose down`.

## Deploying

Push to `main`. GitHub Pages builds the site (repo Settings > Pages > Deploy from a branch > `main` / root), and `CNAME` points it at asia.yearofthegeek.net.

GitHub Pages builds with its own older Jekyll instead of the Gemfile's version. That's fine because the site uses no plugins, but check the live page after big changes.

## How it's built

| Piece | Where |
|---|---|
| Page and all the behavior | `index.html` (Liquid template + one inline script) |
| Styles | `assets/style.css` (colors are variables at the top) |
| Trip data | `_data/days.yml` |
| Avatar | `assets/img/us.png` |
| Map | [Leaflet](https://leafletjs.com/) with Esri World Topo tiles |
| Confetti | [canvas-confetti](https://github.com/catdad/canvas-confetti) |
| Photo sync | `scripts/sync_photos.py` + `.github/workflows/sync-photos.yml` |

Leaflet, canvas-confetti and the fonts load from CDNs. Nothing else is needed.

## Credits

- Map tiles © Esri, HERE, Garmin, © OpenStreetMap contributors (shown on the map)
- Ship photo: [Spaceaero2](https://commons.wikimedia.org/wiki/File:Celebrity_Millennium_at_Kurushima_Strait.jpg), CC BY-SA 3.0 (credited in the footer)
- Cruise schedule from Celebrity Cruises
