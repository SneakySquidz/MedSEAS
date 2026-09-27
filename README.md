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
- **Submarine easter egg** — a small submarine surfaces at a random spot on the map every 25–90 seconds; clicking it shows a Calypso Deep dive fact. Purely decorative, `prefers-reduced-motion` friendly, adds no dependencies.

## Not added: a 2015–2025 heatwave timeline

Wanted, but blocked from this session: the actual per-year data (Copernicus Marine's OMI time series, or the CDS reanalysis) lives on servers this environment cannot reach at all (`data.marine.copernicus.eu`, `cds.climate.copernicus.eu`, NOAA's `psl.noaa.gov`/`coastwatch` mirrors — every option tried was refused by the network policy). Web search surfaced only three usable annual figures (2023: 96%, 2024: 97–99%, 2025: 93% of the basin under strong-or-higher heatwaves) plus one event year (2022), not a full 11-year series, so a defensible timeline can't be built from search alone.

To finish this: either (a) grant this environment network access to `data.marine.copernicus.eu` and/or `cds.climate.copernicus.eu` so a session can pull the OMI heatwave-extent indicator directly, or (b) download the yearly extent/anomaly figures yourself from the Copernicus Marine dashboard and hand them over as a CSV to build the chart from.
