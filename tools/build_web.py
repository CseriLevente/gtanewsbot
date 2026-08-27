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
    "2'%3E%3Crect width='32' height='32' rx='0' fill='%23cd412b'/%3E%3Ctext x"
    "='16' y='23' font-family='Arial,sans-serif' font-size='19' font-weight='7"
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


CSS = r"""
/* ---------------------------------------------------------------------------
   Bestrust Servers house style, applied to a news wire.

   Tokens below are lifted from bestrustservers.com rather than invented, so the
   two properties read as one brand: the near-black warm ground, the Roboto
   Condensed 400/700 pair, the red/yellow/green trio, and -- the single most
   recognisable trait of that site -- square corners on everything. 66 elements
   on their homepage carry border-radius:0; the only round thing is the logo.

   Deliberately single-theme. Bestrust is dark-only, so there is no light
   palette to switch to; every colour is still declared explicitly and
   color-scheme is pinned, so the page never borrows a host's background.

   Semantics use their palette rather than a new one:
     official -> green   (first-party, confirmed)
     rumour   -> yellow  (their caution colour)
     report   -> neutral warm white
   Red stays the brand accent, not a status, so it never competes with the
   confidence signal that the page exists to communicate.
   --------------------------------------------------------------------------- */
:root {
  color-scheme: dark;
  --bg:#0d0d0d;
  --panel:#141414;
  --panel-hi:#1a1a1a;
  --row-hover:rgba(255,255,255,.07);
  --rule:rgba(255,255,255,.12);
  --rule-soft:rgba(255,255,255,.055);
  --text:#e6e0da;
  --text-dim:#9a948e;
  --text-faint:#8b847c;
  --red:#cd412b;
  --red-dark:#a83421;
  --red-text:#e26150;
  --yellow:#d5a118;
  --green:#9cb54e;
  --chip-bg:rgba(255,255,255,.08);
  --warm:linear-gradient(135deg,#1c1a18 0%,#2c221c 60%,#3a2418 100%);
  --font:"Roboto Condensed","Arial Narrow",Arial,sans-serif;
}
* { box-sizing:border-box }
html { background:var(--bg) }
body {
  margin:0; background:var(--bg); color:var(--text);
  font-family:var(--font); font-size:16px; line-height:1.45;
  -webkit-font-smoothing:antialiased;
}
a { color:inherit }

/* Masthead --------------------------------------------------------------- */
.masthead {
  background:var(--warm);
  border-bottom:3px solid var(--red);
  padding:3rem 0 1.6rem;
  margin-bottom:0;
}
.masthead-inner { max-width:66rem; margin:0 auto; padding:0 1.5rem }
.eyebrow {
  font-size:.75rem; font-weight:700; letter-spacing:.14em;
  text-transform:uppercase; color:var(--red-text); margin:0 0 .55rem;
}
h1 {
  font-weight:700; text-transform:uppercase;
  font-size:clamp(2.4rem,8vw,4.75rem); line-height:.9; margin:0;
  letter-spacing:-.005em; text-wrap:balance;
}
h1 em { font-style:normal; color:var(--red) }
.standfirst {
  max-width:40rem; color:var(--text-dim); margin:1rem 0 0; font-size:1.02rem;
}

.wrap { max-width:66rem; margin:0 auto; padding:0 1.5rem 4rem }

/* Stat strip ------------------------------------------------------------- */
.stats {
  display:flex; flex-wrap:wrap; gap:.3rem 2rem;
  padding:.85rem 0; border-bottom:1px solid var(--rule);
  font-size:.78rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text-faint);
}
.stats b {
  color:var(--text); font-weight:700; font-variant-numeric:tabular-nums;
}
.legend {
  display:flex; flex-wrap:wrap; gap:.45rem 1.4rem; padding:.9rem 0 0;
  font-size:.78rem; color:var(--text-dim);
}
.legend span { display:inline-flex; align-items:center; gap:.5rem }
/* Squares, not circles. Nothing on this site is round. */
.dot { width:.6rem; height:.6rem; display:inline-block; flex:none }
.dot.official { background:var(--green) }
.dot.report { background:var(--text-dim) }
.dot.rumour { background:var(--yellow) }

.note {
  margin:1.5rem 0 0; padding:.9rem 1.05rem;
  background:var(--panel); border-left:4px solid var(--red);
  font-size:.95rem; color:var(--text-dim);
}
.note b { color:var(--text) }

/* Story rows ------------------------------------------------------------- */
main { display:flex; flex-direction:column; margin-top:2rem; gap:1px }
.story {
  display:grid; grid-template-columns:7rem 1fr; gap:0 1.6rem;
  padding:1.15rem 1.1rem; background:var(--panel);
  border-left:4px solid var(--text-faint);
  transition:background .12s linear;
}
.story:hover { background:var(--panel-hi) }
.story.official { border-left-color:var(--green) }
.story.report   { border-left-color:var(--text-dim) }
.story.rumour   { border-left-color:var(--yellow) }
.rail { display:flex; flex-direction:column; align-items:flex-start; gap:.15rem }
.label {
  font-size:.7rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
}
.story.official .label { color:var(--green) }
.story.report   .label { color:var(--text-dim) }
.story.rumour   .label { color:var(--yellow) }
.count {
  font-size:1.75rem; font-weight:700; line-height:1.05;
  font-variant-numeric:tabular-nums; color:var(--text); margin-top:.3rem;
}
.count-unit {
  font-size:.65rem; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--text-faint);
}
.body h2 {
  margin:0; font-size:1.2rem; font-weight:700; line-height:1.3;
  text-wrap:pretty; color:var(--text);
}
.body h2 a { color:var(--text); text-decoration:none }
.body h2 a:hover, .body h2 a:focus-visible {
  color:var(--red-text); text-decoration:underline; text-underline-offset:3px;
}
.meta {
  margin:.4rem 0 0; font-size:.78rem; color:var(--text-faint);
  display:flex; flex-wrap:wrap; align-items:center; gap:.45rem;
}
.lede { color:var(--text-dim); font-weight:700; text-transform:uppercase;
  letter-spacing:.05em }
.sep { color:var(--text-faint) }

/* Source chips ----------------------------------------------------------- */
ul.sources {
  list-style:none; display:flex; flex-wrap:wrap; gap:.3rem;
  margin:.8rem 0 0; padding:0;
}
.chip {
  display:inline-block; font-size:.72rem; font-weight:400;
  padding:.2rem .5rem; background:var(--chip-bg); color:var(--text-dim);
  border:1px solid transparent; text-decoration:none;
}
a.chip:hover, a.chip:focus-visible {
  border-color:var(--red); color:var(--text); background:rgba(205,65,43,.16);
}
.chip.t1 { font-weight:700; color:var(--green) }
/* Degree sign, not an arrow: this link goes to the outlet's front page, not to
   the article, and it must not look like the real thing. */
[data-homepage="1"]::after { content:" \00B0"; opacity:.55 }
h2 [data-homepage="1"]::after { font-size:.7em; vertical-align:.35em }
/* An outlet we can name but not link. Deliberately inert: no pointer, no
   hover, nothing that invites a click that would go nowhere. */
.chip-plain {
  color:var(--text-faint); background:transparent;
  border:1px solid var(--rule-soft); cursor:default;
}
.chip-more {
  color:var(--text-faint); background:transparent;
  border:1px dashed var(--rule);
}

footer {
  margin-top:3rem; padding-top:1.2rem; border-top:3px solid var(--red);
  font-size:.78rem; color:var(--text-faint);
  display:flex; flex-direction:column; gap:.4rem;
}
footer b { color:var(--text-dim) }

a:focus-visible, .chip:focus-visible {
  outline:2px solid var(--red); outline-offset:2px;
}
@media (max-width:640px) {
  .story { grid-template-columns:1fr; gap:.6rem; padding:1rem .9rem }
  .rail { flex-direction:row; align-items:baseline; gap:.55rem }
  .count { margin-top:0; font-size:1.3rem }
  .count-unit { align-self:center }
  .masthead { padding:2.2rem 0 1.3rem }
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
        'family=Roboto+Condensed:wght@400;700&display=swap">',
        "<style>" + CSS + "</style>",
        "</head>",
        "<body>",
        '<header class="masthead">',
        '  <div class="masthead-inner">',
        '    <p class="eyebrow">Bestrust Servers / GTA VI news desk</p>',
        "    <h1>Vice City <em>Wire</em></h1>",
        '    <p class="standfirst">Every GTA&nbsp;6 story our feeds carried today,'
        " grouped by event and ranked by how many outlets ran it. The chips beneath"
        " each headline name every outlet that ran the same story &mdash; that count,"
        " not any single report, is the thing worth reading.</p>",
        "  </div>",
        "</header>",
        '<div class="wrap">',
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
