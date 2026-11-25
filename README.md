# MedSEAS

Interactive atlas of the Mediterranean's eight sub-basins: sea-surface temperature, salinity, depth, and a sea-level scenario tool. Educational only. It is not a weather service, a flood warning or a risk assessment.

**Live:** https://sneakysquidz.github.io/MedSEAS/

## Features

- Seasonal and monthly sea-surface temperature, with anomalies and a warming chart
- Surface salinity and depth per basin
- Sea-level scenarios from −1,500 m to +200 m, with a global-warming control based on IPCC AR6
- CSV export of the basin figures and of each scenario
- Live now, refreshed daily: a sea-surface heat watch per basin and the latest Argo float positions
- A 3D view of the seabed

## Run locally

Static site, no build step.

```bash
python3 -m http.server
# open http://localhost:8000
```

The map opens straight from disk, but the monthly temperature and terrain features need a server.

The Live now panel reads `data/live.json`, which is built at deploy time and not committed. To see it locally, run `python scripts/build_live.py --no-heat` (Argo only, no account needed), or without the flag if you have Copernicus Marine credentials in the environment.

## Data

Copernicus Marine reanalysis (temperature), World Ocean Atlas 2023 (salinity), AWS Terrain Tiles (depth and sea level), Natural Earth (coastline). Live panel: Argo floats via Ifremer ERDDAP, and the Copernicus Marine near-real-time Mediterranean SST anomaly. Each figure is labelled with its category and source on the page, and known gaps are stated there.

## Tests and deploy

- Tests: serve the repo and open `tests/smoke.html`.
- Deploy: GitHub Pages, on every push to `main` and once a day (06:15 UTC) to refresh the live data.

More detail on methods, data refresh and settings: [docs/DETAILS.md](docs/DETAILS.md).
