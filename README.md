# MedSEAS

Interactive dashboard of the Mediterranean's eight sub-basins: shade the map by temperature, salinity, depth or curiosities, zoom in, and click a basin for its profile.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Master copy:** this repo. The "Mediterranean Basins" Claude artifact is an older snapshot — edit here, not there.

Single static `index.html`, no build step. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

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
