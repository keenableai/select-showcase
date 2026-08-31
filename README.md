# SELECT showcase

A collection of selected WebQL reports with their full agent trajectories.

## Layout

- `reports/<slug>/` — raw data for one example:
  - `report.html` — the published report, verbatim from the DB.
  - `trajectory.json` — the full agent transcript: user and assistant
    messages, every tool call with its SQL, and tool results.
  - `meta.json` — artifact, conversation, and turn metadata.
  - `result_sets/<id>.json` — every result set the run produced, with
    full rows and notes. Stored in Git LFS.
  - `preview.png` — a full-page screenshot of the report (og-render).
- `site_assets/` — brand fonts (OFL) and logos for the site pages.
`scripts/build_site.py` generates the GitHub Pages site from `reports/`:
an index page plus, per example, the report and a rendered trajectory.
The deploy workflow runs it on every push to main and publishes the
result to GitHub Pages.

## Site

https://cuddly-adventure-1vz52mp.pages.github.io/
