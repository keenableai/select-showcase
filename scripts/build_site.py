"""Build the GitHub Pages site in _site/ from reports/ and site_assets/.

For each reports/<slug>/ directory (report.html, trajectory.json, meta.json,
optional preview.png) the script writes _site/<slug>/report.html (verbatim
copy) and _site/<slug>/trajectory.html (rendered transcript with every
query), then _site/index.html with one card per report. Brand fonts and
logos come from site_assets/. CI runs this on every push to main and
deploys _site/ to GitHub Pages.

Usage: uv run python scripts/build_site.py
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path

import fire
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
ASSETS = ROOT / "site_assets"
DOCS = ROOT / "_site"

GITHUB_URL = "https://github.com/keenableai/select-showcase"
SITE_URL = "https://keenableai.github.io/select-showcase/"
SELECT_URL = "https://app.keenable.ai/select/start"
INDEX_TITLE = "Keenable SELECT: an agent that searches the web in SQL"
INDEX_DESCRIPTION = (
    "Research reports built by Keenable SELECT, an agent that searches the web in"
    " SQL. Each report is published with the full run behind it: every query,"
    " every tool result, every result set."
)
THUMB_WIDTH = 720
THUMB_HEIGHT = 480

HLJS_JS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"

# Palette and type from keenable-webql/docs/report-style.md and needle/dashboard.
PAGE_CSS = """
:root{
  --font-display:"Stack Sans","Stack Sans Headline",-apple-system,BlinkMacSystemFont,
    "Segoe UI","Helvetica Neue",Arial,sans-serif;
  --font-body:"Stack Sans","Stack Sans Headline",-apple-system,BlinkMacSystemFont,
    "Segoe UI","Helvetica Neue",Arial,sans-serif;
  --font-utility:"TASA Orbiter",-apple-system,BlinkMacSystemFont,
    "Segoe UI","Helvetica Neue",Arial,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;color:#2A2A2A;font:400 15px/1.5 var(--font-body);
  letter-spacing:.010em}
.wrap{max-width:1100px;margin:0 auto;padding:0 24px 64px}
a{color:#0A57E8;text-decoration:none}
a:hover{text-decoration:underline}
header.site{display:flex;align-items:center;gap:14px;padding:22px 0;
  border-bottom:1px solid #DDDDDD;margin-bottom:44px}
header.site img{height:28px;display:block}
header.site a.brand{display:flex;align-items:center;gap:14px}
header.site a.brand:hover{text-decoration:none}
header.site .name{font-weight:400;font-size:18px;color:#2A2A2A}
header.site .spacer{flex:1}
header.site a.gh{font-family:var(--font-utility);font-size:12px;
  letter-spacing:-.004em;color:#646464;margin-left:20px}
header.site a.ask{color:#0A57E8}
.intro{margin:0 0 36px;font-size:17px;color:#333}
h2.section{font-weight:400;font-size:34px;line-height:.95;margin:0 0 22px}
.doc{margin:64px 0 0}
.doc p{margin:0 0 14px;color:#333}
.doc h3{font-weight:400;font-size:22px;margin:28px 0 12px}
.doc ul{margin:0 0 14px 22px}
.doc li{margin-bottom:8px;color:#333}
.doc code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.88em;
  background:#F9F9F9;border:1px solid #DDDDDD;padding:1px 4px}
.doc-scroll{overflow-x:auto;border:1px solid #DDDDDD;margin:0 0 14px}
.doc table{border-collapse:collapse;width:100%;font-size:14px}
.doc th{font-family:var(--font-utility);font-weight:500;letter-spacing:-.004em;
  color:#8D8D8D;text-align:left;background:#F9F9F9}
.doc th,.doc td{padding:8px 12px;border-bottom:1px solid #DDDDDD;vertical-align:top}
.doc tbody tr:last-child td{border-bottom:0}
.how{display:flex;align-items:stretch;gap:0;border:1px solid #DDDDDD;
  margin-bottom:52px;background:#F9F9F9}
.how-step{flex:1;min-width:0;padding:24px;display:flex;flex-direction:column;gap:14px}
.how-label{font-family:var(--font-utility);font-size:13px;font-weight:500;
  letter-spacing:-.004em;color:#2A2A2A;margin:0}
.how-prompt{font-size:17px;line-height:1.55;font-style:italic;color:#2A2A2A}
.how-step pre{margin:0;background:none;border:0;padding:0;font-size:11px;line-height:1.6;
  white-space:pre-wrap;overflow-wrap:break-word}
.how-step pre .kw{color:#005CFF;font-weight:600}
.how-arrow{align-self:center;color:#8D8D8D;font-size:24px;padding:0 4px}
.how-shot{flex:1;display:flex;align-items:center}
.how-shot img{max-width:100%;max-height:220px;display:block}
mark.hl-a{background:#FFE1D6;color:#2A2A2A;padding:1px 3px}
mark.hl-b{background:#DAEBFF;color:#2A2A2A;padding:1px 3px}
mark.hl-c{background:#E1E1E1;color:#2A2A2A;padding:1px 3px}
@media (max-width:900px){
  .how{flex-direction:column}
  .how-arrow{transform:rotate(90deg);padding:2px 0}
}
h1.small{font-size:28px;line-height:1.05}
h1{font-weight:400;font-size:52px;line-height:.9;letter-spacing:0;
  margin-bottom:20px;max-width:900px}
.sub{color:#646464;margin-bottom:44px;max-width:700px}
.label{font-family:var(--font-utility);font-size:12px;letter-spacing:-.004em;
  color:#8D8D8D;text-transform:none}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:24px}
.card{background:#fff;border:1px solid #DDDDDD;padding:0 0 20px;
  display:flex;flex-direction:column}
.card .shot{display:block;width:100%;height:230px;object-fit:contain;object-position:center;
  padding:16px;border-bottom:1px solid #DDDDDD;background:#fff}
.card .noshot{height:230px;border-bottom:1px solid #DDDDDD;background:#F9F9F9}
.card-foot{display:flex;flex-direction:column;gap:10px;margin:16px 20px 0;flex:1}
.card-foot h2{font-weight:400;font-size:20px;line-height:1.15;margin:0;flex:1}
.card-foot h2 a{color:#2A2A2A}
.card-meta{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.card-foot a.traj{color:#0A57E8;white-space:nowrap}
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
.rs th{font-family:var(--font-utility);font-weight:500;letter-spacing:-.004em;
  color:#8D8D8D;text-align:left;background:#F9F9F9}
.rs th,.rs td{padding:5px 10px;border-bottom:1px solid #DDDDDD;text-align:left;
  max-width:340px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rs tbody tr:last-child td{border-bottom:0}
.btn{display:inline-block;background:#005CFF;color:#fff;padding:9px 16px;
  font-family:var(--font-utility);font-size:12px;letter-spacing:-.004em}
.btn:hover{background:#0151E2;text-decoration:none}
footer.site{margin-top:64px;padding-top:20px;border-top:1px solid #DDDDDD;
  display:flex;align-items:center;gap:20px}
footer.site img{height:16px;display:block}
footer.site a{font-family:var(--font-utility);font-size:12px;
  letter-spacing:-.004em;color:#646464}
@media (max-width:640px){
  .wrap{padding:0 16px 48px}
  header.site{flex-wrap:wrap;gap:10px 14px;padding:16px 0}
  header.site a.gh{margin-left:0}
  h1{font-size:32px;line-height:1.05}
  .intro{font-size:15px}
  .card-foot{flex-wrap:wrap}
}
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
            f'<p class="tool-name label">tool call &middot; {esc(fn.get("name", "?"))}</p>'
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
        f" &middot; {len(rows)} rows</p>"
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


def page_head(title: str, root: str, description: str = "", og: bool = False) -> str:
    meta = ""
    if description:
        meta += f'<meta name="description" content="{html.escape(description)}">'
    if og:
        meta += (
            f'<meta property="og:title" content="{html.escape(title)}">'
            f'<meta property="og:description" content="{html.escape(description)}">'
            f'<meta property="og:image" content="{SITE_URL}og.png">'
            f'<meta property="og:url" content="{SITE_URL}">'
            '<meta property="og:type" content="website">'
            '<meta name="twitter:card" content="summary_large_image">'
        )
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title>{meta}"
        f'<link rel="icon" href="{root}keenable-mark.svg" type="image/svg+xml">'
        f'<link rel="stylesheet" href="{root}fonts/brand.css">'
        f"<style>{PAGE_CSS}</style></head>"
    )


def site_header(root: str) -> str:
    return (
        '<header class="site">'
        f'<a class="brand" href="{root}index.html">'
        f'<img src="{root}keenable-mark.svg" alt="Keenable">'
        f'<span class="name">Keenable SELECT showcase</span></a><span class="spacer"></span>'
        f'<a class="gh ask" href="{SELECT_URL}">Ask your own question &rarr;</a>'
        f'<a class="gh" href="{GITHUB_URL}">GitHub</a></header>'
    )


def page(
    title: str,
    body: str,
    root: str = "",
    scripts: str = "",
    description: str = "",
    og: bool = False,
) -> str:
    return (
        f"{page_head(title, root, description, og)}<body>"
        f'<div class="wrap">{site_header(root)}'
        f"{body}"
        f'<footer class="site"><a href="https://keenable.ai">'
        f'<img src="{root}keenable-wordmark.svg" alt="Keenable"></a>'
        f'<a href="{GITHUB_URL}">Source and data on GitHub</a></footer>'
        f"</div>{scripts}</body></html>\n"
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
    if (ASSETS / "og.png").exists():
        shutil.copyfile(ASSETS / "og.png", DOCS / "og.png")


def write_thumb(src: Path, dest: Path) -> tuple[int, int]:
    with Image.open(src) as source:
        scale = min(THUMB_WIDTH / source.width, THUMB_HEIGHT / source.height, 1)
        thumb = source.resize(
            (round(source.width * scale), round(source.height * scale)), Image.LANCZOS
        )
        thumb.save(dest, "WEBP", quality=82)
        return thumb.width, thumb.height


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
    thumb_src = next(
        (src / name for name in ("hero.png", "preview.png") if (src / name).exists()), None
    )
    thumb_size = None
    thumb_version = ""
    if thumb_src is not None:
        thumb_size = write_thumb(thumb_src, out / "thumb.webp")
        thumb_version = hashlib.sha256((out / "thumb.webp").read_bytes()).hexdigest()[:8]
    result_sets = load_result_sets(src, out)

    title = meta["artifact"]["title"]
    report_url = meta["report_url"]
    n_queries = sum(len(m.get("tool_calls") or []) for m in transcript)
    body = (
        f'<h1 class="small">{esc(title)}</h1>'
        f'<p class="sub label">Trajectory &middot; {len(transcript)} messages, {n_queries} tool calls'
        f' &middot; <a href="{report_url}">report</a>'
        f' &middot; <a href="../index.html">all reports</a></p>'
        + "".join(render_message(m, result_sets) for m in transcript)
    )
    scripts = f'<script src="{HLJS_JS}"></script><script>hljs.highlightAll()</script>'
    if transcript:
        (out / "trajectory.html").write_text(
            page(
                f"{title} &middot; trajectory",
                body,
                root="../",
                scripts=scripts,
                description=f"The full agent run behind “{title}”: every SQL query,"
                " tool result, and result set.",
            )
        )
    return {
        "slug": slug,
        "title": title,
        "report_url": report_url,
        "created_at": meta["artifact"]["created_at"][:10],
        "n_messages": len(transcript),
        "n_queries": n_queries,
        "has_trajectory": bool(transcript),
        "thumb_size": thumb_size,
        "thumb_version": thumb_version,
    }


EXPLAINER_SLUG = "frontier-ai-researcher-moves-since-2025"

EXPLAINER_PROMPT = (
    "“Which <mark class='hl-a'>AI researchers moved between frontier labs</mark>"
    " since <mark class='hl-c'>2025</mark>?"
    " For each move list <mark class='hl-b'>the researcher</mark>,"
    " <mark class='hl-b'>the lab they left</mark>,"
    " <mark class='hl-b'>where they went</mark> and"
    " <mark class='hl-b'>the month</mark>.”"
)

EXPLAINER_SQL = (
    "<span class='kw'>SELECT</span>\n"
    "  SEM_EXTRACT(content, <mark class='hl-b'>'researcher'</mark>),\n"
    "  SEM_EXTRACT(content, <mark class='hl-b'>'left lab'</mark>),\n"
    "  SEM_EXTRACT(content, <mark class='hl-b'>'joined lab'</mark>),\n"
    "  SEM_EXTRACT(content, <mark class='hl-b'>'move month'</mark>)\n"
    "<span class='kw'>FROM</span> WEB_SEARCH(8 diverse queries)\n"
    "<span class='kw'>WHERE</span> SEM_MATCH(content,\n"
    "  <mark class='hl-a'>'named researcher moving\n"
    "   between frontier labs</mark>, <mark class='hl-c'>2025+</mark>')"
)


def explainer(entries: list[dict]) -> str:
    example = next((e for e in entries if e["slug"] == EXPLAINER_SLUG), None)
    if example is None or example["thumb_size"] is None:
        return ""
    shot = (
        f'<a href="{example["report_url"]}">'
        f'<img src="{example["slug"]}/thumb.webp?v={example["thumb_version"]}" alt=""></a>'
    )
    return (
        '<h2 class="section">How it works</h2>'
        '<div class="how">'
        f'<div class="how-step"><p class="how-label">You ask</p>'
        f'<p class="how-prompt">{EXPLAINER_PROMPT}</p></div>'
        '<div class="how-arrow">&rarr;</div>'
        f'<div class="how-step"><p class="how-label">Keenable SELECT runs SQL on the web</p>'
        f"<pre>{EXPLAINER_SQL}</pre></div>"
        '<div class="how-arrow">&rarr;</div>'
        f'<div class="how-step"><p class="how-label">You get a report</p>'
        f'<div class="how-shot">{shot}</div></div>'
        "</div>"
    )


# Copied from https://paste.keenable.ai/how-select-works.
DOC_HTML = """
<div class="doc">
<h2 class="section">The system behind the reports</h2>
<p>Keenable SELECT is an MCP server with one main tool: <code>select</code>. The tool runs
read-only DuckDB <code>SELECT</code> queries on live web data. The SQL can hold web
operators and semantic operators. The server runs these operators outside
DuckDB, puts their output back into the row set, and then runs the final SQL
in DuckDB.</p>
<p>A traditional web search gives an agent ten links. The agent must then read each
page and build the answer from expensive tokens. SELECT moves this work into
the query. One call can search more than 1,000 pages, filter them with an
exact <code>WHERE</code> clause at no LLM cost, extract fields with one small LLM call
per row, and group the rows.</p>
<h3>MCP tools</h3>
<ul>
<li><code>select</code> takes DuckDB <code>SELECT</code> queries and returns the rows. The
server saves every query result as a result set with an id, and a later
query can read from that id.</li>
<li><code>generate_html_report</code> takes a brief and result set ids. A report model on
the server writes an HTML report from the rows and returns a shareable
link.</li>
</ul>
<h3>Semantic operators</h3>
<p>The operators live inside normal SQL. The server finds them in the parsed
statement, runs them, and replaces them with plain columns. Exact SQL filters
run first, so only the surviving rows go to the LLM operators.</p>
<div class="doc-scroll"><table>
<thead><tr><th>Operator</th><th>What it does</th></tr></thead>
<tbody>
<tr><td><code>WEB_SEARCH('q1', 'q2', ...)</code></td><td>Searches all queries at the same time, merges ranked results, and removes repeated URLs.</td></tr>
<tr><td><code>WEB_FETCH('https://a.com', ...)</code></td><td>Gets the given URLs as Markdown, one row per page.</td></tr>
<tr><td><code>SEM_EXTRACT(column, 'field description')</code></td><td>One LLM call per row. It returns one field, or null when the text does not give the value.</td></tr>
<tr><td><code>SEM_EXTRACT_ALL(column, 'what one value is')</code></td><td>Like <code>SEM_EXTRACT</code>, but returns all matching values in a list.</td></tr>
<tr><td><code>SEM_MATCH(column, 'predicate')</code></td><td>An LLM test per row. Use it as a meaning-based <code>WHERE</code> filter.</td></tr>
<tr><td><code>SEM_SCORE(column, 'query')</code></td><td>A low-cost embedding score per row. Use <code>ORDER BY ... DESC LIMIT k</code>.</td></tr>
<tr><td><code>SEM_NORM(column)</code></td><td>Gives the same key to values with the same meaning. Use it in <code>GROUP BY</code>.</td></tr>
</tbody>
</table></div>
<p><code>WEB_SEARCH</code> and <code>WEB_FETCH</code> can also run per row. Their arguments can use
row columns, for example <code>WEB_SEARCH(name || ' founding year')</code>.</p>
<h3>Main agent</h3>
<p>Every report in this gallery comes from two agents: a research agent that
uses the MCP server to gather the data, and a report agent that runs inside
<code>generate_html_report</code> on the server and writes the page.</p>
<p>The research agent is a plain tool loop: an LLM with the <code>select</code> tool. It
writes and runs its own queries until it can answer, and streams its tool
calls, results, and answer as events. A follow-up question continues the
conversation on top of the stored transcript. Every run in this showcase asks
for an HTML report, so the agent ends each answer with the report link.</p>
<h3>Report agent</h3>
<p>A second agent writes each report on the server. It gets the brief, the rows
of the result sets, and an authoring guide. It builds the page in a sandboxed
Python session that holds the result sets as dataframes, so the data reaches
the page without the model retyping it. After each publish, the server
renders the draft and returns screenshots and the page's JavaScript error
count; the agent fixes the document and publishes again, under a fixed
budget. Only the final draft stays live, published as a link.</p>
</div>
"""


def build_index(entries: list[dict]) -> None:
    cards = []
    for e in sorted(entries, key=lambda e: e["created_at"], reverse=True):
        if e["thumb_size"] is not None:
            width, height = e["thumb_size"]
            shot = (
                f'<a href="{e["report_url"]}">'
                f'<img class="shot" src="{e["slug"]}/thumb.webp?v={e["thumb_version"]}" alt=""'
                f' loading="lazy" width="{width}" height="{height}"></a>'
            )
        else:
            shot = '<div class="noshot"></div>'
        if e["has_trajectory"]:
            stats = (
                f'{e["created_at"]} &middot; {e["n_messages"]} messages'
                f' &middot; {e["n_queries"]} queries'
            )
            traj = f'<a class="traj label" href="{e["slug"]}/trajectory.html">Trajectory &rarr;</a>'
        else:
            stats = e["created_at"]
            traj = ""
        cards.append(
            f'<div class="card">{shot}'
            f'<div class="card-foot"><h2><a href="{e["report_url"]}">{esc(e["title"])}</a></h2>'
            f'<div class="card-meta"><span class="label">{stats}</span>{traj}</div></div></div>'
        )
    body = (
        '<p class="intro">Research reports built by'
        f' <a href="{SELECT_URL}">Keenable SELECT</a>, an agent that searches the web'
        " in SQL.<br>Every card links the finished report and the full trajectory behind"
        " it: each query, tool result, and result set.</p>"
        f"{explainer(entries)}"
        '<h2 class="section">Gallery</h2>'
        f'<div class="cards">{"".join(cards)}</div>'
        f"{DOC_HTML}"
    )
    (DOCS / "index.html").write_text(
        page(INDEX_TITLE, body, description=INDEX_DESCRIPTION, og=True)
    )


def main() -> None:
    if DOCS.exists():
        shutil.rmtree(DOCS)
    copy_assets()
    slugs = sorted(p.name for p in REPORTS.iterdir() if (p / "meta.json").exists())
    entries = [build_report(slug) for slug in slugs]
    build_index(entries)
    print(f"Built _site/ with {len(entries)} report(s): {', '.join(e['slug'] for e in entries)}")


if __name__ == "__main__":
    fire.Fire(main)
