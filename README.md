# Keenable SELECT showcase

Selected reports made with [Keenable SELECT](https://app.keenable.ai/select/), each with the
full agent run behind it: every query, every tool result, and the result sets
the run produced.

**Site: https://keenableai.github.io/select-showcase/**

## Layout

- `reports/<slug>/` — one example:
  - `report.html` — the published report.
  - `trajectory.json` — the full agent transcript: user and assistant
    messages, every tool call with its SQL, and tool results.
  - `meta.json` — report title, question, and timestamps.
  - `result_sets/<id>.json` — the result sets of the run, with full rows
    and notes. Stored in Git LFS.
  - `preview.png` — a full-page screenshot of the report.
- `site_assets/` — brand fonts (SIL OFL) and logos for the site pages.
- `scripts/build_site.py` — generates the site into `_site/`.

## Build

```bash
uv sync
uv run python scripts/build_site.py
```

Every push to main runs the same build in CI and deploys `_site/` to
GitHub Pages.
