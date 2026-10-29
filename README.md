# MedSEAS

An interactive, educational atlas of the Mediterranean's eight sub-basins: how they differ and how they change. It is not a beach-weather service, a flood warning or a risk assessment. The sea-level tool is an illustrative scenario only.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Master copy:** this repo. The "Mediterranean Basins" Claude artifact is an older snapshot — edit here, not there.

Static site, no build step: `index.html` plus a vendored MapLibre GL JS (`vendor/maplibre-gl/`, BSD-3-Clause) and generated map geometry (`data/geo.js`). The map opens from disk; the monthly temperature and terrain features need a web server. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

## How the page is organised

Four modes sit above the map. The map, the ranking, the selected-basin panel and the context line stay in step, and the selected basin is kept when you switch mode.

- **Temperature**, with three tabs:
  - *Seasonal patterns*: summer (July–September), winter (January–March) and the seasonal swing (summer minus winter) per basin. These are 1991–2020 climatological means of the Copernicus reanalysis over each basin's 0.25° cells, weighted by cos(latitude), computed from `data/sst_clim.png`.
  - *Monthly timeline*: a month slider over the monthly sea-surface temperature grid, with Play/Pause, an anomaly mode against 1991–2020 and a series for the selected basin. Playback stops when you leave the tab or the browser tab is hidden. The colour scale is fixed (12–29 °C, or ±3 °C for anomalies).
  - *Warming*: each basin's estimated long-run warming rate on the map, and the whole-Mediterranean anomaly chart with trends and recent extremes.
- **Salinity**: surface salinity and net evaporation, with a ranked "what drives salt" list.
- **Depth**: mean depth, maximum depth and surface area.
- **Sea level**: the sea-level scenarios (below).

A **context line** under the mode buttons states, for what is on screen: measure, unit, data category, period and source. The **selected-basin panel** keeps the measured figures, a "Curiosities" block (plankton layer, biggest tide, Posidonia meadows) and the basin's story.

## Data categories and sources

Every figure is classed as one of: satellite observation, reanalysis/model output, literature value, derived (computed here from other values or from the terrain), interpolated estimate (marked **est.**) or scenario output.

Sources are kept as one record per dataset in `index.html` (`DATASETS`): id, name, product, variable, unit, coverage, baseline, aggregation, resolution, method, retrieval or build date, data category and limitations. The context line, the "Where the data comes from" section and the CSV all read from these records. A field with no documented value shows "not documented"; nothing is filled in by guesswork.

Known gaps, stated on the page:

- Per-basin salinity and tide values have no documented source or reference period. Maximum depths are only partly sourced (Alboran, Adriatic and Aegean from web references; Tyrrhenian and Levantine from Wikipedia without a citation; Ligurian and Balearic not confirmed; Ionian is the 2020 Calypso Deep measurement). The plankton-layer depths follow a west-to-east gradient reported in the literature, with the per-basin values interpolated. The Posidonia area and decline are from Telesca et al. 2015; the per-basin ratings are not sourced. The Sources section lists exactly what is and is not documented.
- EMODnet Bathymetry is listed as a reference only. The measured depths and the sea-level scenarios use the AWS Terrain Tiles.

## Map

Rendered with MapLibre GL JS from vector data. Ctrl/Cmd + scroll zooms (so the page still scrolls), drag pans, and a basin click selects it. The ranked list and the full data table give the same figures without the map, and ranking rows work from the keyboard. The view covers the broader Mediterranean, with the seas outside the eight basins tinted grey.

- **Basins:** eight limit polygons (IHO-style straight lines between capes) clipped to the Natural Earth 1:10m coastline.
- **Measured figures:** each basin's area and mean depth are computed from its polygon and the terrain grid, so they describe what is drawn. Maximum depths are literature values.
- **Ranking:** the reference marker is the unweighted mean of the eight basins, and is labelled as such.
- **Seabed button:** depth classes from the terrain grid; the hover tooltip reports the approximate depth under the cursor.
- **Light and dark** follow the page theme.

## Sea-level scenarios

A slider and a numeric offset in metres (kept in sync), a "Reset to today" button and neutral presets (−120 m, today, +10 m, +70 m, −1,500 m). The supported range is −2,500 m to +200 m relative to today's sea level as represented in the terrain tiles, whose vertical datum is not documented here. Typed values are rounded to 0.5 m; values outside the range are set to the nearest limit with a message, and non-numbers are refused with a message.

What the code does:

- Each terrain cell (about 4 km) stores the sea level at which it first floods, computed by a **priority flood** from the open sea in `scripts/build_data.py`. Land floods only where the sea can reach it over lower ground, so inland hollows (Dead Sea, Qattara) stay dry until the rim is overtopped.
- Below −130 m the world ocean is held at −130 m and only the Mediterranean is lowered.
- The legend separates today's sea (no overlay), land flooded in the scenario, seabed exposed in the scenario and today's coastline (dashed).
- A city counts as reached when the water reaches any land cell within one cell (about 4 km) of it. A city whose surrounding cells are all sea on this grid counts as reached at the first rise.
- Not modelled: coastal defences, drainage, tides, waves, ice sheets, sediment and crustal rebound.

Data files, both generated:

- `data/geo.js`: land, basins (with measured area and mean depth) and non-basin water.
- `data/dem.png` (about 440 KB, fetched when the browser is idle; needs http(s)): one PNG on the Web Mercator grid holding each cell's flood level and some flags. Elevation and bathymetry come from the AWS/Mapzen terrain tiles ("terrarium", SRTM + GMTED + ETOPO1/GEBCO). If it cannot load, the page says so instead of drawing anything.

To change basin limits or the map extent, edit `scripts/build_data.py` and rebuild:

    pip install shapely numpy pillow
    python3 scripts/build_data.py

## Monthly sea-surface temperature

Monthly means from Copernicus Marine `MEDSEA_MULTIYEAR_PHY_006_004` (reanalysis, model output), coarsened to a 0.25° grid, for recent years only (the coverage is read from `data/sst.json`; the current grid runs 2015-01 to 2026-09 and was built on 2026-10-26). Anomalies use a 12-frame 1991–2020 monthly climatology (`data/sst_clim.png`).

- **Basin series:** the mean of the 0.25° cells whose centre lies in the basin, weighted by cos(latitude), computed from the grid itself (never from the Mediterranean-wide series). Months without data are left as gaps.
- **Missing data:** a stored code of 0 means land or no data, and such cells stay blank, never coloured as cold water. A true value of exactly the encoding base temperature would also read as missing; that is below any Mediterranean surface value on the scale.
- If the files cannot load, the tab shows an "unavailable" message instead of sample values.

One-off setup to publish the data:

1. Create a free Copernicus Marine account (marine.copernicus.eu).
2. Add repository secrets `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD`.
3. Settings > Actions > General: allow read and write permissions and "Allow GitHub Actions to create and approve pull requests".
4. Run the "Update SST grid" workflow (manual). It runs `scripts/build_sst.py` and opens a pull request with the data; merge it after checking the preview.

`scripts/build_sst.py` fetches one year at a time, reduces it and deletes the file, so memory stays small; the climatology is built once and reused.

## Warming chart

A bar chart of the Mediterranean's yearly sea-surface temperature anomaly (vs 1991–2020), 2015–2024, from Copernicus Marine's OMI file `MEDSEA_OMI_TEMPSAL_sst_area_averaged_anomalies` (satellite, reprocessed; monthly anomalies averaged per year here). The 1991–2020 anomaly baseline is the one stated in the Copernicus product user manual (Issue 5.0, November 2024); its change history lists the switch to this climatology in September 2024. Trends shown: +0.41 ± 0.06 °C/decade over 1982–2018 (Pisano et al. 2020, *Remote Sensing* 12, 132, DOI 10.3390/rs12010132: 0.041 ± 0.006 °C/year, computed on the same Copernicus satellite record), and +0.87 ± 0.46 °C/decade (95%, n = 10) over 2015–2024, an ordinary least-squares fit to the ten bars computed for this page. The short window has a wide interval and overstates the long-run rate. No per-basin anomalies are derived from this series. A "Recent extremes" list adds 2022–2025 heatwave facts from Copernicus Ocean State Report 8 and Mercator Ocean bulletins.

To refresh: the Copernicus file is re-issued yearly (currently ends Dec 2024). Download the new `.nc` from the product page, recompute annual means, and update `DATA` in the timeline script.

## CSV downloads

The sea-level tool has a **Download this scenario (CSV)** button: the offset, flooded or exposed area (whole map, about 4 km cells), which of the 33 cities are reached, and a `data_category` row marking it as scenario output. Areas are blank until the terrain has loaded and at offsets where they do not apply.

The button under the data table saves `medseas-basin-measures.csv`: one row per basin and measure, with `basin_id, basin, variable, value, unit, season, reference_period, anomaly_baseline, source_id, method, data_category, est_flag`. Text fields are quoted where needed; unavailable values would be left blank, never zero. (It replaces the older wide `medseas-basins.csv`.)

## Keeping data current

The page shows a "Data last reviewed" date under the headline figures. Only the headline SST figures and warming rates change (yearly, with Copernicus/C3S bulletins); depths, areas and basin outlines are fixed.

To refresh: ask Claude to review the figures against the latest bulletins. Changes are proposed as a pull request for approval, never pushed straight to `main`, and the review date is updated in the same PR.

## Extras

- **Submarine easter egg:** a yellow submarine surfaces at a random spot on the map now and then; clicking it shows a Calypso Deep fact. Decorative, `prefers-reduced-motion` friendly, no dependencies.

## Tests

`tests/smoke.html` is a zero-dependency browser test page (no build step, no packages). Serve the repo over http and open it:

    python3 -m http.server
    # then open http://localhost:8000/tests/smoke.html

It loads the page at desktop and phone width and runs about 40 checks: mode and tab switching, selection kept across modes, playback start, pause, hidden-tab pause and cleanup, date labels against the data file, fixed colour scale, latest-selection-wins under rapid switching, units, categories and sources for every measure, the seasonal values and the 2015–2024 trend recomputed from their inputs, both CSV exports (row counts, escaping, no blank values, filenames), sea-level slider and number agreement, clamping, invalid input, reset, and sea-level reference points (the Dead Sea and Qattara hollows stay dry at +10 m, the northern Adriatic shelf is exposed at −120 m, Venice floods within 2 m). These reference points are sanity checks against well-known geography, not a scientific validation of the model. It also checks that missing SST cells are drawn transparent, never as cold water, and that the anomaly baseline is stated with its source.

`scripts/check_dem.py` (needs numpy and Pillow, as `build_data.py` does) checks `data/dem.png` on its own: no unfilled pits, every flooded land cell connected to the sea at +0.5, 2, 10, 50, 100 and 200 m, sea cells at or below 0 m, and the Dead Sea and Qattara hollows protected (they flood at about +100 m and +60 m, when the rim is overtopped). This confirms the stored flood levels behave like a priority flood; it does not validate the underlying terrain tiles or the modelling assumptions.
