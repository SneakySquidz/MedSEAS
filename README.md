# MedSEAS

Interactive dashboard of the Mediterranean's eight sub-basins: shade the map by temperature, salinity, depth or curiosities, zoom in, and click a basin for its profile.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Master copy:** this repo. The "Mediterranean Basins" Claude artifact is an older snapshot — edit here, not there.

Static site, no build step: `index.html` plus a vendored MapLibre GL JS (`vendor/maplibre-gl/`, BSD-3-Clause) and generated map geometry (`data/geo.js`). Opens straight from disk. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

## Map

Rendered with MapLibre GL JS from vector data, not a drawn SVG. Ctrl/Cmd + scroll zooms (so the page still scrolls), drag pans, a basin click selects it, and the ranked list flies the map to a basin.

- **Basins:** eight limit polygons (IHO-style straight lines between capes) clipped to the Natural Earth 1:10m coastline, so outlines follow the real shore.
- **Seabed button:** fades the shading to reveal Natural Earth depth bands (200 / 1,000 / 2,000 / 3,000 / 4,000 m). Hovering a basin also reports the depth band under the cursor. The bands are generalised: the 5,109 m Calypso Deep is not resolved.
- **Light and dark** follow the page theme.

`data/geo.js` is generated; edit the limit polygons in `scripts/build_geo.py` and rebuild:

    pip install shapely
    python3 scripts/build_geo.py

The script downloads the Natural Earth files it needs on first run. It also prints each basin's polygon area. These differ from the literature `area` figures in `index.html` (the eight figures sum to ~1.7 million km² against ~2.5 million km² for the whole sea), which is left as is and flagged for review.

Data: Copernicus Marine, Argo, EMODnet, Natural Earth — sources listed in the page footer.

## Keeping data current

The page shows a "Data last reviewed" date under the headline figures. Only the headline SST figures and warming rates change (yearly, with Copernicus/C3S bulletins); depths, areas and basin outlines are fixed.

To refresh: ask Claude to review the figures against the latest bulletins. Changes are proposed as a pull request for approval, never pushed straight to `main`, and the review date is updated in the same PR.

## Added

- **CSV download** — a button under the data table exports all 8 basins' figures (temperature, salinity, evaporation, depth, area, warming rate, etc.) as a spreadsheet-ready CSV.
- **Net evaporation** — a new measure under Salinity, sourced from the eastern/western Mediterranean water budget (Frontiers in Climate, 2025). Only known at the whole-basin level (west vs. east), not per sub-basin, so every western basin shares one figure and every eastern basin shares another — noted in the footnotes and marked "est." in the UI.
- **Submarine easter egg** — a yellow submarine surfaces at a random spot on the map a few seconds after the map comes into view, then every ~20 seconds; clicking it shows a Calypso Deep dive fact. Purely decorative, `prefers-reduced-motion` friendly, adds no dependencies.

## Warming timeline

A bar chart of the Mediterranean's yearly sea-surface temperature anomaly (vs 1991–2020), 2015–2024, from Copernicus Marine's public OMI file `MEDSEA_OMI_TEMPSAL_sst_area_averaged_anomalies` (monthly anomalies, averaged per year here). Trends: +0.33 °C/decade over 1982–2024, +0.88 °C/decade over 2015–2024. A "Recent extremes" list adds 2022–2025 heatwave facts from Copernicus Ocean State Report 8 and Mercator Ocean bulletins.

Not included: a year-by-year heatwave *extent* series. Copernicus publishes no Mediterranean marine-heatwave extent indicator file, only yearly bulletin figures.

To refresh: the Copernicus file is re-issued yearly (currently ends Dec 2024). Download the new `.nc` from the product page, recompute annual means, and update `DATA` in the timeline script.
