# SELECT showcase

A collection of selected WebQL reports with their full agent trajectories.

## Layout

- `reports/<slug>/` — raw data for one example:
  - `report.html` — the published report, verbatim from the DB.
  - `trajectory.json` — the full agent transcript: user and assistant
    messages, every tool call with its SQL, and tool results.
  - `meta.json` — artifact, conversation, and turn metadata.
- `docs/` — the GitHub Pages site, generated from `reports/`:
  an index page plus, per example, the report and a rendered trajectory.

## Site

https://keenableai.github.io/select-showcase/
