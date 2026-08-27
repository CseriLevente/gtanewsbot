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
            "published": 1756317600,
            "sources": [
                {"name": "Example", "url": "https://example.com/a",
                 "tier": 1, "wrapper": False},
                {"name": "Aggregated", "url": "https://news.google.com/rss/articles/X",
                 "tier": 2, "wrapper": True},
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


def test_aggregator_links_are_marked(page: pathlib.Path) -> None:
    # The footer promises readers that an arrow marks an aggregator link.
    html = page.read_text(encoding="utf-8")
    assert 'data-wrapper="1"' in html
    assert "2197" in html  # the ↗ glyph the CSS attaches to those chips
