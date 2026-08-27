"""
Build the web edition of the digest.

The Discord digest shows the top 8 stories; this page shows every one. That
pairing is why the "+N more not shown" line could be dropped from the embed:
nothing is hidden, it just lives somewhere with room for it.

Design intent: the reader's real question is "how well-sourced is this?", so the
page is an information display, not an article. Stories rank by how many outlets
carried them, that count is the most prominent element in each row, and every
outlet is listed as a link so a reader can go straight to the original.

Run:  python tools/build_web.py
Output is a complete standalone HTML document, servable by any static host.
It must declare its own charset and viewport: without them a browser guesses
the encoding (every apostrophe becomes mojibake) and phones render it at
desktop width.
"""
from __future__ import annotations

import datetime
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "web_edition.json"
OUT = ROOT / "web" / "index.html"

LABELS = {"official": "Official", "report": "Report", "rumour": "Rumour"}

# Inlined so the page has no external image dependency and no favicon 404.
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 3"
    "2'%3E%3Crect width='32' height='32' rx='7' fill='%23A31D5B'/%3E%3Ctext x"
    "='16' y='23' font-family='Georgia,serif' font-size='19' font-weight='7"
    "00' fill='%23fff' text-anchor='middle'%3EW%3C/text%3E%3C/svg%3E"
)


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def render_story(s: dict) -> str:
    label = LABELS.get(s["label"], "Report")
    cls = s["label"] if s["label"] in LABELS else "report"

    chips = []
    for src in s["sources"]:
        wrapper = ' data-wrapper="1"' if src.get("wrapper") else ""
        tier_cls = " t1" if int(src.get("tier") or 9) == 1 else ""
        chips.append(
            '<li><a class="chip' + tier_cls + '" href="' + esc(src["url"]) + '"'
            ' target="_blank" rel="noopener noreferrer"' + wrapper + '>'
            + esc(src["name"]) + "</a></li>"
        )
    hidden = int(s["outlets"]) - len(s["sources"])
    if hidden > 0:
        chips.append('<li><span class="chip chip-more">+' + str(hidden)
                     + " more</span></li>")

    when = ""
    if s.get("published"):
        when = datetime.datetime.fromtimestamp(s["published"]).strftime("%d %b, %H:%M")
    time_html = ""
    if when:
        time_html = '<span class="sep">/</span><time>' + esc(when) + "</time>"

    plural = "outlets" if int(s["outlets"]) != 1 else "outlet"

    return (
        '      <article class="story ' + cls + '">\n'
        '        <div class="rail">\n'
        '          <span class="label">' + label + "</span>\n"
        '          <span class="count">' + str(s["outlets"]) + "</span>\n"
        '          <span class="count-unit">' + plural + "</span>\n"
        "        </div>\n"
        '        <div class="body">\n'
        "          <h2><a href=\"" + esc(s["primary"]) + '" target="_blank"'
        ' rel="noopener noreferrer">' + esc(s["title"]) + "</a></h2>\n"
        '          <p class="meta"><span class="lede">' + esc(s["primary_name"])
        + "</span>" + time_html + "</p>\n"
        '          <ul class="sources">\n'
        + "\n".join(chips) + "\n"
        "          </ul>\n"
        "        </div>\n"
        "      </article>"
    )


CSS = """
:root {
  --ground:#FAF8F9; --surface:#FFFFFF; --rule:#E3DADE; --rule-soft:#F0EAEC;
  --ink:#241C20; --ink-soft:#6B5D63; --ink-faint:#9A8C92;
  --accent:#A31D5B;
  --official:#1F6F4A; --report:#2A5AA8; --rumour:#A2540F;
  --chip:#F4EFF1; --chip-ink:#4C4046;
  --serif:"Instrument Serif",Georgia,"Times New Roman",serif;
  --sans:"Archivo","Helvetica Neue",Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark) {
  :root:not([data-theme="light"]) {
    --ground:#161215; --surface:#1D1719; --rule:#332A2E; --rule-soft:#241E21;
    --ink:#F2EAED; --ink-soft:#B0A2A8; --ink-faint:#7C6E74;
    --accent:#FF6BA6;
    --official:#5FD39B; --report:#7FB0F5; --rumour:#E8A75C;
    --chip:#251E21; --chip-ink:#C6B8BE;
  }
}
:root[data-theme="dark"] {
  --ground:#161215; --surface:#1D1719; --rule:#332A2E; --rule-soft:#241E21;
  --ink:#F2EAED; --ink-soft:#B0A2A8; --ink-faint:#7C6E74;
  --accent:#FF6BA6;
  --official:#5FD39B; --report:#7FB0F5; --rumour:#E8A75C;
  --chip:#251E21; --chip-ink:#C6B8BE;
}
* { box-sizing:border-box }
body {
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:16px; line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
.wrap { max-width:62rem; margin:0 auto; padding:0 1.5rem 4rem }
header.masthead { padding:3.5rem 0 1.25rem; border-bottom:2px solid var(--ink) }
.eyebrow {
  font-family:var(--mono); font-size:.7rem; letter-spacing:.16em;
  text-transform:uppercase; color:var(--accent); margin:0 0 .7rem;
}
h1 {
  font-family:var(--serif); font-weight:400;
  font-size:clamp(2.6rem,7vw,4.5rem); line-height:.95; margin:0;
  letter-spacing:-.01em; text-wrap:balance;
}
h1 em { font-style:italic; color:var(--accent) }
.standfirst { max-width:36rem; color:var(--ink-soft); margin:1.1rem 0 0 }
.stats {
  display:flex; flex-wrap:wrap; gap:.3rem 2rem; padding:.9rem 0;
  border-bottom:1px solid var(--rule); font-family:var(--mono);
  font-size:.73rem; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-faint);
}
.stats b { color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums }
.legend {
  display:flex; flex-wrap:wrap; gap:.45rem 1.3rem; padding:.95rem 0 0;
  font-family:var(--mono); font-size:.72rem; color:var(--ink-soft);
}
.legend span { display:inline-flex; align-items:center; gap:.45rem }
.dot { width:.55rem; height:.55rem; border-radius:50%; display:inline-block }
.dot.official { background:var(--official) }
.dot.report { background:var(--report) }
.dot.rumour { background:var(--rumour) }
.note {
  margin:1.6rem 0 0; padding:.95rem 1.1rem; background:var(--surface);
  border:1px solid var(--rule); border-left:3px solid var(--accent);
  font-size:.92rem; color:var(--ink-soft);
}
.note b { color:var(--ink) }
main { display:flex; flex-direction:column; margin-top:2.5rem }
.story {
  display:grid; grid-template-columns:7.5rem 1fr; gap:0 1.75rem;
  padding:1.5rem 0; border-bottom:1px solid var(--rule-soft);
}
.story:first-child { border-top:1px solid var(--rule) }
.rail {
  display:flex; flex-direction:column; align-items:flex-start; gap:.1rem;
  border-left:3px solid var(--rule); padding-left:.85rem;
}
.story.official .rail { border-left-color:var(--official) }
.story.report .rail { border-left-color:var(--report) }
.story.rumour .rail { border-left-color:var(--rumour) }
.label {
  font-family:var(--mono); font-size:.66rem; font-weight:600;
  letter-spacing:.12em; text-transform:uppercase;
}
.story.official .label { color:var(--official) }
.story.report .label { color:var(--report) }
.story.rumour .label { color:var(--rumour) }
.count {
  font-family:var(--mono); font-size:1.45rem; font-weight:500; line-height:1.15;
  font-variant-numeric:tabular-nums; color:var(--ink); margin-top:.4rem;
}
.count-unit {
  font-family:var(--mono); font-size:.62rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ink-faint);
}
.body h2 {
  margin:0; font-size:1.16rem; font-weight:600; line-height:1.35;
  letter-spacing:-.005em; text-wrap:pretty;
}
.body h2 a {
  color:var(--ink); text-decoration:none; text-underline-offset:3px;
}
.body h2 a:hover, .body h2 a:focus-visible {
  color:var(--accent); text-decoration:underline;
  text-decoration-color:var(--accent);
}
.meta {
  margin:.45rem 0 0; font-family:var(--mono); font-size:.72rem;
  color:var(--ink-faint); display:flex; flex-wrap:wrap; align-items:center;
  gap:.45rem;
}
.lede { color:var(--ink-soft); font-weight:500 }
.sep { color:var(--rule) }
ul.sources {
  list-style:none; display:flex; flex-wrap:wrap; gap:.35rem;
  margin:.85rem 0 0; padding:0;
}
.chip {
  display:inline-block; font-family:var(--mono); font-size:.68rem;
  padding:.22rem .5rem; background:var(--chip); color:var(--chip-ink);
  border:1px solid transparent; text-decoration:none; border-radius:2px;
}
.chip:hover, .chip:focus-visible { border-color:var(--accent); color:var(--accent) }
.chip.t1 { font-weight:600; color:var(--official) }
.chip[data-wrapper="1"]::after { content:" \\2197"; opacity:.45 }
.chip-more {
  color:var(--ink-faint); background:transparent; border:1px dashed var(--rule);
}
footer {
  margin-top:3.5rem; padding-top:1.3rem; border-top:2px solid var(--ink);
  font-family:var(--mono); font-size:.72rem; color:var(--ink-faint);
  display:flex; flex-direction:column; gap:.4rem;
}
a:focus-visible, .chip:focus-visible { outline:2px solid var(--accent); outline-offset:2px }
@media (max-width:640px) {
  .story { grid-template-columns:1fr; gap:.75rem }
  .rail { flex-direction:row; align-items:baseline; gap:.55rem }
  .count { margin-top:0; font-size:1.05rem }
  .count-unit { align-self:center }
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; animation:none !important } }
"""


def main() -> int:
    if not DATA.exists():
        print("missing " + str(DATA) + " — run the exporter first", file=sys.stderr)
        return 1
    d = json.loads(DATA.read_text(encoding="utf-8"))
    counts = {k: sum(1 for s in d["stories"] if s["label"] == k) for k in LABELS}
    stories = "\n".join(render_story(s) for s in d["stories"])

    blurb = (
        "Every GTA 6 story our feeds carried today: "
        + str(d["total_stories"]) + " stories from " + str(d["total_items"])
        + " articles, grouped by event and ranked by how many outlets ran it."
    )

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="light dark">',
        "<title>Vice City Wire</title>",
        '<meta name="description" content="' + esc(blurb) + '">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Vice City Wire">',
        '<meta property="og:title" content="Vice City Wire">',
        '<meta property="og:description" content="' + esc(blurb) + '">',
        '<meta name="twitter:card" content="summary">',
        '<link rel="icon" href="' + FAVICON + '">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        "family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600"
        '&family=Instrument+Serif:ital@0;1&display=swap">',
        "<style>" + CSS + "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '  <header class="masthead">',
        '    <p class="eyebrow">Leonida desk / automated wire</p>',
        "    <h1>Vice City <em>Wire</em></h1>",
        '    <p class="standfirst">Every GTA&nbsp;6 story our feeds carried today,'
        " grouped by event and ranked by how many outlets ran it. Each headline links"
        " to the outlet that carried it first; the chips beneath list everyone else"
        " who ran the same story.</p>",
        "  </header>",
        '  <div class="stats">',
        "    <span><b>" + str(d["total_stories"]) + "</b> stories</span>",
        "    <span><b>" + str(d["total_items"]) + "</b> articles</span>",
        "    <span><b>" + str(counts["official"]) + "</b> official</span>",
        "    <span><b>" + str(counts["report"]) + "</b> reports</span>",
        "    <span><b>" + str(counts["rumour"]) + "</b> rumours</span>",
        "    <span>compiled <b>" + esc(d["generated_local"]) + "</b></span>",
        "  </div>",
        '  <div class="legend">',
        '    <span><i class="dot official"></i> Official &mdash; first-party Rockstar'
        " or Take-Two</span>",
        '    <span><i class="dot report"></i> Report &mdash; established outlet,'
        " reported as fact</span>",
        '    <span><i class="dot rumour"></i> Rumour &mdash; unconfirmed, or sourced'
        " from leaked material</span>",
        "  </div>",
        '  <p class="note"><b>On leaks:</b> a claim whose only source is leaked'
        " material stays labelled a rumour permanently, however many outlets repeat"
        " it. We describe what those reports <em>claim</em> and link the journalism"
        " that reported it &mdash; never the leaked material itself.</p>",
        "  <main>",
        stories,
        "  </main>",
        "  <footer>",
        "    <span>Compiled automatically from " + str(d["total_items"])
        + " articles across 10 feeds. Headlines and links belong to their"
        " publishers.</span>",
        "    <span>An arrow marks an aggregator link, used where the publisher's own"
        " URL could not be resolved.</span>",
        "  </footer>",
        "</div>",
        "</body>",
        "</html>",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print("wrote " + str(OUT) + ": " + str(OUT.stat().st_size) + " bytes, "
          + str(d["total_stories"]) + " stories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
