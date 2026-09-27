# MedSEAS

Interactive dashboard of the Mediterranean's eight sub-basins: shade the map by temperature, salinity, depth or curiosities, zoom in, and click a basin for its profile.

- **Live:** https://sneakysquidz.github.io/MedSEAS/
- **Internal version:** the "Mediterranean Basins" Claude artifact (same page)

Single static `index.html`, no build step. Deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy-pages.yml`).

Data: Copernicus Marine, Argo, EMODnet, Natural Earth — sources listed in the page footer.
