# CLAUDE.md

Public collection of SELECT reports with their agent trajectories,
published to GitHub Pages.

## Commands

```bash
uv sync                                # install dependencies
uv run python scripts/build_site.py   # build the site into _site/
```

## Layout

- `reports/<slug>/` — source data, one directory per report: `report.html`,
  `trajectory.json`, `meta.json`, `result_sets/*.json` (Git LFS),
  `preview.png`.
- `site_assets/` — brand fonts and logos the site pages use.
- `scripts/build_site.py` — the site generator. Fire CLI.
- `_site/` — build output. Never commit it.
- `.github/workflows/deploy-pages.yaml` — builds and deploys the site to
  GitHub Pages on every push to main.

## Adding a report

1. Fetch the data and render the preview with the showcase scripts in the
   internal WebQL repository (`scripts/showcase/fetch_report.py` and
   `render_preview.py`), run from this directory.
2. Commit the new `reports/<slug>/` directory. CI builds and deploys.

## Rules

- This repo is public. Data under `reports/` must stay free of internal
  identifiers; `meta.json` carries only the report URL, title fields, the
  question, and timestamps.
- Do not hand-edit data under `reports/`; refetch it instead.
- `result_sets/*.json` go through Git LFS (`.gitattributes`).
