# Trip timeline

Plain Jekyll, no plugins, so GitHub Pages builds it on its own. The timeline lives at `/map/`.

- Edit the days in `_data/days.yml` (each day has `coords` or `route` for the map, and a `tz` time zone)
- Add `celebrate:` to a day to throw it a party
- Styles live in `assets/style.css`, the tracker avatar is `assets/img/us.png`
- Preview any day as "today" by adding `?date=2026-10-08` to the URL

## Run it locally

```bash
docker compose up -d
```

Then open http://localhost:4000/map/. Changes to `_config.yml` need `docker compose restart jekyll`.

Turn it on: repo Settings > Pages > Deploy from a branch > `main` / root.
