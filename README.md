# medseas

A personal "second brain" dashboard — quick tasks and notes, as a backstop for day-to-day work.

## Status

MVP: static HTML/CSS/JS page with local-storage persistence (data stays in your browser only, nothing synced anywhere yet). No backend or database — that's a deliberate next step, not an oversight.

## Running it

Open `index.html` in a browser, or serve the folder with any static file server.

## Hosting

Deploys automatically to GitHub Pages on every push to `main`, via `.github/workflows/deploy-pages.yml`.

**One-time setup required:** in this repo's GitHub settings, go to **Settings → Pages → Build and deployment → Source**, and select **GitHub Actions**. After that, every push to `main` publishes automatically.

## Roadmap

- Real persistence (a database) so notes/tasks aren't stuck to one browser
- Possibly rebuilt/extended via Lovable once the shape of the thing is clearer

## Development

This repo is private and used for personal experimentation.
