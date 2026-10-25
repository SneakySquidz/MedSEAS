# MedSEAS

Interactive dashboard of the Mediterranean's eight sub-basins: shade the map by temperature, salinity, depth or curiosities, zoom in, and click a basin for its profile.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Master copy:** this repo. The "Mediterranean Basins" Claude artifact is an older snapshot — edit here, not there.

Static site, no build step: `index.html` plus a vendored MapLibre GL JS (`vendor/maplibre-gl/`, BSD-3-Clause) and generated map geometry (`data/geo.js`). Opens straight from disk. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

## Map

Rendered with MapLibre GL JS from vector data, not a drawn SVG. Ctrl/Cmd + scroll zooms (so the page still scrolls), drag pans, a basin click selects it, and the ranked list flies the map to a basin. The view covers the broader Mediterranean: the Atlantic approaches, the Black Sea and Sea of Azov, the Sea of Marmara and the head of the Red Sea. Seas outside the eight basins are tinted grey.

- **Basins:** eight limit polygons (IHO-style straight lines between capes) clipped to the Natural Earth 1:10m coastline, so outlines follow the real shore.
- **Measured figures:** each basin's area and mean depth are computed from its polygon and the terrain grid, so they describe what is drawn (the eight areas sum to the ~2.5 million km² of the sea). Maximum depths stay as literature values.
- **Seabed button:** depth classes (0 to 4,000 m+) from the terrain grid under the basin shading, and the hover tooltip reports the depth under the cursor.
- **Fun: raise or lower the sea:** a sea-level slider from 2,500 m below today to 200 m above, with presets (Last Ice Age, +10 m, ice-free Earth, a drained Mediterranean). Flooding uses a priority flood, so land only floods where the sea can reach it. It reports land gained or flooded and which of 33 cities the water reaches. It is a toy: today's terrain, no ice or crustal rebound, 4 km cells.
- **Light and dark** follow the page theme.

Data files, both generated:

- `data/geo.js`: land, basins (with measured area and mean depth) and non-basin water.
- `data/dem.js` (about 600 KB, fetched when the browser is idle): one PNG on the Web Mercator grid holding the sea-level at which each cell floods and some flags. Elevation and bathymetry come from the AWS/Mapzen terrain tiles ("terrarium", SRTM + GMTED + ETOPO1/GEBCO).

To change basin limits or the map extent, edit `scripts/build_data.py` and rebuild:

    pip install shapely numpy pillow
    python3 scripts/build_data.py

It downloads the Natural Earth files and terrain tiles it needs on first run and prints each basin's area and mean depth.

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
