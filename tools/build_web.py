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


# Highest tier number we will still send a reader to the outlet's homepage for.
# Above this the domain is not in the credibility list at all, and an unlabelled
# homepage link to an outlet we cannot vouch for is worth less than a plain name.
HOMEPAGE_TIER_MAX = 3


def link_target(url: str, *, wrapper: bool, tier: int, domain: str) -> tuple[str, str]:
    """
    Decide where a source may point, and how to mark it.

    Returns (href, marker_attr); an empty href means "render as text, not a link".

    The rule exists because most items reach the bot through Google News, whose
    RSS links are opaque redirects. They cannot be decoded -- the post-2024 blobs
    carry no address -- and following one lands on consent.google.com from the EU,
    so a reader without Google consent cookies gets a consent wall rather than the
    article. Emitting such a URL is worse than emitting none: it looks like a link
    to the outlet named beside it, and it is not one.

    So, in order:
      * a real publisher URL is linked as-is;
      * a wrapper from an outlet we recognise falls back to that outlet's
        homepage, marked as such, because it is honest and always resolves;
      * anything else renders as plain text.
    """
    if url and not wrapper:
        return url, ""
    if domain and tier <= HOMEPAGE_TIER_MAX:
        return "https://" + domain + "/", ' data-homepage="1"'
    return "", ""


def render_story(s: dict) -> str:
    label = LABELS.get(s["label"], "Report")
    cls = s["label"] if s["label"] in LABELS else "report"

    chips = []
    for src in s["sources"]:
        tier_cls = " t1" if int(src.get("tier") or 9) == 1 else ""
        href, marker = link_target(
            src.get("url") or "",
            wrapper=bool(src.get("wrapper")),
            tier=int(src.get("tier") or 9),
            domain=(src.get("domain") or ""),
        )
        if href:
            chips.append(
                '<li><a class="chip' + tier_cls + '" href="' + esc(href) + '"'
                ' target="_blank" rel="noopener noreferrer"' + marker + '>'
                + esc(src["name"]) + "</a></li>"
            )
        else:
            # Named but not linked. The outlet still counts as corroboration,
            # which is what the number on the left of the row is about.
            chips.append('<li><span class="chip chip-plain' + tier_cls + '">'
                         + esc(src["name"]) + "</span></li>")
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

    # 65 of 90 stories currently have every source wrapped, so an unlinked
    # headline is the common case here, not an edge case.
    h_href, h_marker = link_target(
        s.get("primary") or "",
        wrapper=bool(s.get("primary_wrapper")),
        tier=int(s.get("primary_tier") or 9),
        domain=(s.get("primary_domain") or ""),
    )
    if h_href:
        headline_html = ('<a href="' + esc(h_href) + '" target="_blank"'
                         ' rel="noopener noreferrer"' + h_marker + ">"
                         + esc(s["title"]) + "</a>")
    else:
        headline_html = esc(s["title"])

    return (
        '      <article class="story ' + cls + '">\n'
        '        <div class="rail">\n'
        '          <span class="label">' + label + "</span>\n"
        '          <span class="count">' + str(s["outlets"]) + "</span>\n"
        '          <span class="count-unit">' + plural + "</span>\n"
        "        </div>\n"
        '        <div class="body">\n'
        "          <h2>" + headline_html + "</h2>\n"
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
a.chip:hover, a.chip:focus-visible { border-color:var(--accent); color:var(--accent) }
.chip.t1 { font-weight:600; color:var(--official) }
/* Degree sign, not an arrow: this link goes to the outlet's front page, not to
   the article, and it must not look like the real thing. */
[data-homepage="1"]::after { content:" \\00B0"; opacity:.5 }
h2 [data-homepage="1"]::after { font-size:.7em; vertical-align:.35em }
/* An outlet we can name but not link. Deliberately inert: no pointer, no hover,
   nothing that invites a click that would go nowhere. */
.chip-plain { color:var(--ink-faint); background:transparent;
  border:1px solid var(--rule-soft); cursor:default }
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
        " grouped by event and ranked by how many outlets ran it. The chips beneath"
        " each headline name every outlet that ran the same story &mdash; that count,"
        " not any single report, is the thing worth reading.</p>",
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
        "    <span>Most stories reach us through a news aggregator, whose links are"
        " redirects rather than article addresses. We never pass one on: a"
        " <b>&deg;</b> means the link goes to that outlet's front page rather than"
        " to the article, and an outlet in grey is one we can name but not link."
        " A named source you cannot click still counts as corroboration.</span>",
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
