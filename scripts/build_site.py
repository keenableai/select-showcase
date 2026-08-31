"""Build the GitHub Pages site in _site/ from reports/ and site_assets/.

For each reports/<slug>/ directory (report.html, trajectory.json, meta.json,
optional preview.png) the script writes _site/<slug>/report.html (verbatim
copy) and _site/<slug>/trajectory.html (rendered transcript with every
query), then _site/index.html with one card per report. Brand fonts and
logos come from site_assets/. CI runs this on every push to main and
deploys _site/ to GitHub Pages.

Usage: python3 scripts/build_site.py
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
ASSETS = ROOT / "site_assets"
DOCS = ROOT / "_site"

GITHUB_URL = "https://github.com/keenableai/select-showcase"

HLJS_JS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"

# Palette and type roles from keenable-webql/docs/report-style.md.
PAGE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;color:#2A2A2A;font-family:'Stack Sans Headline',system-ui,sans-serif;
  font-weight:300;font-size:16px;line-height:1.5;letter-spacing:.010em}
.wrap{max-width:1100px;margin:0 auto;padding:0 24px 64px}
a{color:#0A57E8;text-decoration:none}
a:hover{text-decoration:underline}
header.site{display:flex;align-items:center;gap:14px;padding:22px 0;
  border-bottom:1px solid #DDDDDD;margin-bottom:44px}
header.site img{height:28px;display:block}
header.site .name{font-weight:400;font-size:18px;color:#2A2A2A}
header.site .spacer{flex:1}
header.site a.gh{font-family:'TASA Orbiter',system-ui;font-size:12px;
  letter-spacing:-.004em;color:#646464}
body.framed{display:flex;flex-direction:column;height:100vh}
.wrap.bar{width:100%;padding-bottom:0}
.wrap.bar header.site{margin-bottom:0}
.frame{flex:1;width:100%;border:0;display:block}
footer.site.foot{margin:0;padding:14px 0 18px;gap:12px}
footer.site.foot .spacer{flex:1}
footer.site.foot a.traj{color:#0A57E8}
h1.small{font-size:28px;line-height:1.05}
h1{font-weight:400;font-size:52px;line-height:.9;letter-spacing:0;
  margin-bottom:20px;max-width:900px}
.sub{color:#646464;margin-bottom:44px;max-width:700px}
.label{font-family:'TASA Orbiter',system-ui;font-size:12px;letter-spacing:-.004em;
  color:#8D8D8D;text-transform:none}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:24px}
.card{background:#fff;border:1px solid #DDDDDD;padding:0 0 20px;
  display:flex;flex-direction:column}
.card .shot{display:block;width:100%;height:220px;object-fit:cover;object-position:top;
  border-bottom:1px solid #DDDDDD;background:#F9F9F9}
.card .noshot{height:220px;border-bottom:1px solid #DDDDDD;background:#F9F9F9}
.card-foot{display:flex;justify-content:space-between;align-items:baseline;
  gap:12px;margin:16px 20px 0}
.card-foot a.traj{color:#0A57E8}
.card .meta{margin:0 20px}
.msg{border:1px solid #DDDDDD;margin:0 0 -1px}
.msg-head{padding:8px 16px;border-bottom:1px solid #DDDDDD;background:#F9F9F9}
.msg-user .msg-head{background:#DAEBFF}
.msg-body{padding:16px}
.msg-body p{white-space:pre-wrap;margin:0 0 10px}
.msg-body p:last-child{margin-bottom:0}
.tool-name{margin:0 0 8px}
pre{background:#F9F9F9;border:1px solid #DDDDDD;padding:14px 16px;overflow-x:auto;
  font-size:13px;line-height:1.5;margin:0 0 10px}
pre:last-child{margin-bottom:0}
pre code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:none;padding:0}
details summary{cursor:pointer;padding:10px 16px}
details pre{margin:0;border:0;border-top:1px solid #DDDDDD;max-height:420px;overflow:auto}
.rs{border-top:1px solid #DDDDDD;padding:12px 16px 16px}
.rs>.label{margin:0 0 10px}
.rs-scroll{overflow-x:auto;border:1px solid #DDDDDD;margin-bottom:12px}
.rs table{border-collapse:collapse;width:100%;font-size:12px;line-height:1.4}
.rs th{font-family:'TASA Orbiter',system-ui;font-weight:500;letter-spacing:-.004em;
  color:#8D8D8D;text-align:left;background:#F9F9F9}
.rs th,.rs td{padding:5px 10px;border-bottom:1px solid #DDDDDD;text-align:left;
  max-width:340px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rs tbody tr:last-child td{border-bottom:0}
.btn{display:inline-block;background:#005CFF;color:#fff;padding:9px 16px;
  font-family:'TASA Orbiter',system-ui;font-size:12px;letter-spacing:-.004em}
.btn:hover{background:#0151E2;text-decoration:none}
footer.site{margin-top:64px;padding-top:20px;border-top:1px solid #DDDDDD;
  display:flex;align-items:center;gap:20px}
footer.site img{height:16px;display:block}
footer.site a{font-family:'TASA Orbiter',system-ui;font-size:12px;
  letter-spacing:-.004em;color:#646464}
.hljs-keyword{color:#005CFF}
.hljs-string{color:#646464}
.hljs-number{color:#F25F34}
.hljs-comment{color:#8D8D8D}
.hljs-operator,.hljs-punctuation{color:#2A2A2A}
"""


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def render_assistant(message: dict) -> str:
    parts = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function", {})
        parts.append(
            f'<p class="tool-name label">tool call — {esc(fn.get("name", "?"))}</p>'
        )
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = None
        if isinstance(args, dict) and "query" in args:
            parts.append(f'<pre><code class="language-sql">{esc(args["query"])}</code></pre>')
            extras = {k: v for k, v in args.items() if k != "query"}
            if extras:
                parts.append(f"<pre>{esc(json.dumps(extras, indent=1))}</pre>")
        else:
            parts.append(f"<pre>{esc(fn.get('arguments', ''))}</pre>")
    content = message.get("content")
    if content:
        parts.append(f"<p>{esc(content)}</p>")
    return "".join(parts)


RESULT_SET_ID_RE = re.compile(r"result_set_id: (\S+)")
PREVIEW_ROWS = 5
CELL_CHARS = 160


def cell_text(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= CELL_CHARS else text[: CELL_CHARS - 1] + "…"


def render_result_set(result_set: dict, size_bytes: int) -> str:
    rows = result_set["rows"]
    columns = list(rows[0].keys()) if rows else []
    head = "".join(f"<th>{esc(column)}</th>" for column in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(cell_text(row.get(column)))}</td>" for column in columns)
        + "</tr>"
        for row in rows[:PREVIEW_ROWS]
    )
    return (
        f'<div class="rs"><p class="label">result set {esc(result_set["id"])}'
        f" — {len(rows)} rows</p>"
        f'<div class="rs-scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
        f'<a class="btn" href="result_sets/{esc(result_set["id"])}.json" download>'
        f"Download all {len(rows)} rows · {size_bytes / 1024:.0f} KB</a></div>"
    )


def render_message(message: dict, result_sets: dict[str, dict]) -> str:
    role = message.get("role", "?")
    if role == "tool":
        content = message.get("content") or ""
        body = (
            f'<details><summary class="label">tool result'
            f" ({len(content)} chars)</summary>"
            f"<pre>{esc(content)}</pre></details>"
        )
        for rs_id in RESULT_SET_ID_RE.findall(content):
            if rs_id in result_sets:
                body += render_result_set(**result_sets[rs_id])
        return f'<div class="msg msg-tool">{body}</div>'
    body = render_assistant(message) if role == "assistant" else (
        f"<p>{esc(message.get('content') or '')}</p>"
    )
    return (
        f'<div class="msg msg-{esc(role)}"><div class="msg-head label">{esc(role)}</div>'
        f'<div class="msg-body">{body}</div></div>'
    )


def trim_transcript(transcript: list[dict]) -> list[dict]:
    report_call_ids = {
        call.get("id")
        for message in transcript
        for call in message.get("tool_calls") or []
        if call.get("function", {}).get("name") == "generate_html_report"
    }
    trimmed = [
        message
        for message in transcript
        if not (message.get("role") == "tool" and message.get("tool_call_id") in report_call_ids)
    ]
    if trimmed and trimmed[-1].get("role") == "assistant" and not trimmed[-1].get("tool_calls"):
        trimmed.pop()
    return trimmed


def page_head(title: str, root: str) -> str:
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title>"
        f'<link rel="icon" href="{root}keenable-mark.svg" type="image/svg+xml">'
        f'<link rel="stylesheet" href="{root}fonts/brand.css">'
        f"<style>{PAGE_CSS}</style></head>"
    )


def site_header(root: str) -> str:
    return (
        '<header class="site">'
        f'<a href="{root}index.html"><img src="{root}keenable-mark.svg" alt="Keenable"></a>'
        f'<span class="name">SELECT showcase</span><span class="spacer"></span>'
        f'<a class="gh" href="{GITHUB_URL}">GitHub</a></header>'
    )


def page(title: str, body: str, root: str = "", scripts: str = "") -> str:
    return (
        f"{page_head(title, root)}<body>"
        f'<div class="wrap">{site_header(root)}'
        f"{body}"
        f'<footer class="site"><a href="https://keenable.ai">'
        f'<img src="{root}keenable-wordmark.svg" alt="Keenable"></a>'
        f'<a href="{GITHUB_URL}">Source and data on GitHub</a></footer>'
        f"</div>{scripts}</body></html>\n"
    )


def frame_page(title: str, frame_src: str, root: str, foot: str) -> str:
    return (
        f'{page_head(title, root)}<body class="framed">'
        f'<div class="wrap bar">{site_header(root)}</div>'
        f'<iframe class="frame" src="{frame_src}" title="{esc(title)}"></iframe>'
        f'<div class="wrap bar"><footer class="site foot">{foot}</footer></div>'
        "</body></html>\n"
    )


def brand_css() -> str:
    latin = (
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304,"
        " U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215,"
        " U+FEFF, U+FFFD"
    )
    latin_ext = (
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308,"
        " U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0,"
        " U+2113, U+2C60-2C7F, U+A720-A7FF"
    )
    faces = (
        ("Stack Sans Headline", "stack-sans-headline-latin.woff2", latin, "200 700"),
        ("Stack Sans Headline", "stack-sans-headline-latin-ext.woff2", latin_ext, "200 700"),
        ("TASA Orbiter", "tasa-orbiter-latin.woff2", latin, "400 500"),
        ("TASA Orbiter", "tasa-orbiter-latin-ext.woff2", latin_ext, "400 500"),
    )
    return "".join(
        "@font-face{"
        f"font-family:'{family}';font-style:normal;font-weight:{weights};"
        f"font-display:swap;src:url({file}) format('woff2');unicode-range:{ranges}"
        "}"
        for family, file, ranges, weights in faces
    )


def copy_assets() -> None:
    fonts = DOCS / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for item in (ASSETS / "fonts").iterdir():
        shutil.copyfile(item, fonts / item.name)
    (fonts / "brand.css").write_text(brand_css())
    for name in ("keenable-mark.svg", "keenable-wordmark.svg"):
        shutil.copyfile(ASSETS / name, DOCS / name)


def load_result_sets(src: Path, out: Path) -> dict[str, dict]:
    rs_dir = src / "result_sets"
    if not rs_dir.is_dir():
        return {}
    shutil.copytree(rs_dir, out / "result_sets", dirs_exist_ok=True)
    return {
        path.stem: {
            "result_set": json.loads(path.read_text()),
            "size_bytes": path.stat().st_size,
        }
        for path in rs_dir.glob("*.json")
    }


def build_report(slug: str) -> dict:
    src = REPORTS / slug
    meta = json.loads((src / "meta.json").read_text())
    transcript = trim_transcript(json.loads((src / "trajectory.json").read_text()) or [])

    out = DOCS / slug
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / "report.html", out / "report_frame.html")
    has_preview = (src / "preview.png").exists()
    if has_preview:
        shutil.copyfile(src / "preview.png", out / "preview.png")
    result_sets = load_result_sets(src, out)

    title = meta["artifact"]["title"]
    n_queries = sum(len(m.get("tool_calls") or []) for m in transcript)
    body = (
        f'<h1 class="small">{esc(title)}</h1>'
        f'<p class="sub label">Trajectory — {len(transcript)} messages, {n_queries} tool calls'
        f' &middot; <a href="report.html">report</a>'
        f' &middot; <a href="../index.html">all reports</a></p>'
        + "".join(render_message(m, result_sets) for m in transcript)
    )
    scripts = f'<script src="{HLJS_JS}"></script><script>hljs.highlightAll()</script>'
    (out / "trajectory.html").write_text(
        page(f"{title} — trajectory", body, root="../", scripts=scripts)
    )
    foot = (
        f'<span class="label">{len(transcript)} messages &middot; {n_queries} queries'
        f' behind this report</span><span class="spacer"></span>'
        f'<a class="traj label" href="trajectory.html">Trajectory &rarr;</a>'
    )
    (out / "report.html").write_text(
        frame_page(title, "report_frame.html", root="../", foot=foot)
    )
    return {
        "slug": slug,
        "created_at": meta["artifact"]["created_at"][:10],
        "n_messages": len(transcript),
        "n_queries": n_queries,
        "has_preview": has_preview,
    }


def build_index(entries: list[dict]) -> None:
    cards = []
    for e in sorted(entries, key=lambda e: e["created_at"], reverse=True):
        shot = (
            f'<a href="{e["slug"]}/report.html">'
            f'<img class="shot" src="{e["slug"]}/preview.png" alt=""></a>'
            if e["has_preview"]
            else '<div class="noshot"></div>'
        )
        cards.append(
            f'<div class="card">{shot}'
            f'<div class="card-foot"><span class="label">{e["created_at"]}'
            f' &middot; {e["n_messages"]} messages &middot; {e["n_queries"]} queries</span>'
            f'<a class="traj label" href="{e["slug"]}/trajectory.html">Trajectory &rarr;</a>'
            "</div></div>"
        )
    body = (
        f'<div class="cards">{"".join(cards)}</div>'
    )
    (DOCS / "index.html").write_text(page("SELECT showcase", body))


def main() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    copy_assets()
    slugs = sorted(p.name for p in REPORTS.iterdir() if (p / "meta.json").exists())
    entries = [build_report(slug) for slug in slugs]
    build_index(entries)
    print(f"Built _site/ with {len(entries)} report(s): {', '.join(e['slug'] for e in entries)}")


if __name__ == "__main__":
    main()
