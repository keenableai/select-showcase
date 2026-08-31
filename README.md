# SELECT showcase

A collection of selected WebQL reports with their full agent trajectories.

## Layout

- `reports/<slug>/` — raw data for one example:
  - `report.html` — the published report, verbatim from the DB.
  - `trajectory.json` — the full agent transcript: user and assistant
    messages, every tool call with its SQL, and tool results.
  - `meta.json` — artifact, conversation, and turn metadata.
The GitHub Pages site is generated from `reports/` and lives on the
`gh-pages` branch: an index page plus, per example, the report and a
rendered trajectory. A push to `gh-pages` triggers the deploy workflow
on that branch, which publishes the site.

## Site

https://cuddly-adventure-1vz52mp.pages.github.io/
