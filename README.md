# MedSEAS

Interactive dashboard of the Mediterranean's eight sub-basins: shade the map by temperature, salinity, depth or curiosities, zoom in, and click a basin for its profile.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Master copy:** this repo. The "Mediterranean Basins" Claude artifact is an older snapshot — edit here, not there.

Single static `index.html`, no build step. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

Data: Copernicus Marine, Argo, EMODnet, Natural Earth — sources listed in the page footer.

## Keeping data current

The page shows a "Data last reviewed" date under the headline figures. Only the headline SST figures and warming rates change (yearly, with Copernicus/C3S bulletins); depths, areas and basin outlines are fixed.

To refresh: ask Claude to review the figures against the latest bulletins. Changes are proposed as a pull request for approval, never pushed straight to `main`, and the review date is updated in the same PR.
