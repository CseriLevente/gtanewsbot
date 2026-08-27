"""
Structural tests for the generated web edition.

This page began life as a Claude artifact, where the host wraps the uploaded
fragment in its own `<!doctype html><head>…<body>` skeleton. So the generator
emitted a fragment starting at `<title>` — correct for an artifact, silently
broken as a standalone website:

  * with no `<meta charset>` the browser guesses the encoding, and every
    curly apostrophe in a headline renders as "â€™";
  * with no `<meta name="viewport">` phones lay the page out at desktop width
    and zoom out, which is how most Discord members will open it;
  * with no doctype the browser drops into quirks mode.

None of those raise an error anywhere — the build succeeds, the file looks fine
in an editor, and only a human loading it on a phone notices. Hence these tests.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

build_web = pytest.importorskip("tools.build_web")


SAMPLE = {
    "generated_local": "27 Aug 2026, 20:08",
    "total_items": 3,
    "total_stories": 1,
    "stories": [
        {
            # A curly apostrophe and an en dash: the exact characters that
            # turned to mojibake when the charset was undeclared.
            "title": "Rockstar\u2019s GTA 6 trailer \u2013 what we learned",
            "label": "report",
            "size": 2,
            "outlets": 2,
            "primary": "https://example.com/a",
            "primary_name": "Example",
            "primary_domain": "example.com",
            "primary_tier": 1,
            "primary_wrapper": False,
            "published": 1756317600,
            "sources": [
                # A real publisher URL: linked as-is.
                {"name": "Example", "url": "https://example.com/a",
                 "tier": 1, "wrapper": False, "domain": "example.com"},
                # A wrapper from a recognised outlet: falls back to its homepage.
                {"name": "Known Outlet", "url": "https://news.google.com/rss/articles/X",
                 "tier": 2, "wrapper": True, "domain": "known.example"},
                # A wrapper from an outlet not in the credibility list: no link.
                {"name": "Unlisted Blog", "url": "https://news.google.com/rss/articles/Y",
                 "tier": 4, "wrapper": True, "domain": "unlisted.example"},
            ],
        }
    ],
}


@pytest.fixture()
def page(tmp_path, monkeypatch):
    data = tmp_path / "web_edition.json"
    data.write_text(json.dumps(SAMPLE), encoding="utf-8")
    out = tmp_path / "index.html"
    monkeypatch.setattr(build_web, "DATA", data)
    monkeypatch.setattr(build_web, "OUT", out)
    assert build_web.main() == 0
    return out


def test_is_a_complete_document(page: pathlib.Path) -> None:
    html = page.read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    for tag in ("<html lang=", "<head>", "</head>", "<body>", "</body>", "</html>"):
        assert tag in html, "missing " + tag


def test_declares_utf8_within_the_first_1024_bytes(page: pathlib.Path) -> None:
    # The HTML spec only requires a parser to look this far for the encoding
    # declaration, so "present somewhere" is not good enough.
    head = page.read_bytes()[:1024].lower()
    assert b'charset="utf-8"' in head


def test_declares_a_viewport(page: pathlib.Path) -> None:
    assert 'name="viewport"' in page.read_text(encoding="utf-8")


def test_non_ascii_survives_as_utf8(page: pathlib.Path) -> None:
    raw = page.read_bytes()
    # Decoding must succeed and the original characters must come back intact:
    # a mojibake round-trip would still decode, so assert on the characters.
    text = raw.decode("utf-8")
    assert "Rockstar\u2019s" in text
    assert "\u2013" in text
    assert "\u00e2\u20ac" not in text  # the "â€" signature of cp1252 mojibake


def test_never_emits_an_aggregator_href(page: pathlib.Path) -> None:
    """
    The invariant that matters most on this page.

    Google News RSS links are opaque redirects that cannot be decoded, and
    following one lands on consent.google.com from the EU. Passing one to a
    reader produces a link that looks like it goes to the outlet named beside
    it and does not. 88% of source chips came from that aggregator, so this is
    the common path, not a corner case.
    """
    html = page.read_text(encoding="utf-8")
    hrefs = re.findall(r'href="([^"]+)"', html)
    assert hrefs, "page emitted no links at all"
    assert not [u for u in hrefs if "news.google" in u]


def test_recognised_outlet_falls_back_to_its_homepage(page: pathlib.Path) -> None:
    html = page.read_text(encoding="utf-8")
    assert 'href="https://known.example/"' in html
    assert 'data-homepage="1"' in html  # marked, so it does not pose as the article


def test_unlisted_outlet_is_named_but_not_linked(page: pathlib.Path) -> None:
    html = page.read_text(encoding="utf-8")
    assert "Unlisted Blog" in html, "the outlet must still be named"
    assert 'href="https://unlisted.example/"' not in html
    assert "chip-plain" in html


def test_real_publisher_urls_are_still_linked_directly(page: pathlib.Path) -> None:
    # The gate must not cost us the links we actually have.
    assert 'href="https://example.com/a"' in page.read_text(encoding="utf-8")
