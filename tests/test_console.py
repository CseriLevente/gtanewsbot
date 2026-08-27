"""
Console-safety tests.

This machine's console is cp1250. A digest preview contains emoji, which cp1250
cannot encode — and before this module existed, `digest --dry-run` (the
operator's main tool) died with UnicodeEncodeError. A cosmetic encoding problem
must never crash a command.

Note that cp1250 CAN encode em dash and middle dot, so those are deliberately
left untouched; only genuinely unrepresentable characters are substituted.
"""
from __future__ import annotations

import io
import sys

from src.console import safe_print, to_console


class _FakeStdout(io.StringIO):
    """A stdout whose declared encoding we control."""

    def __init__(self, encoding: str):
        super().__init__()
        self._encoding = encoding

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return self._encoding


def test_emoji_transliterated_on_cp1250(monkeypatch):
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    out = to_console("\U0001F7E2 **Official** and \U0001F7E0 **Rumour**")
    assert "[OK]" in out
    assert "[??]" in out
    assert "\U0001F7E2" not in out
    out.encode("cp1250")  # must not raise


def test_emoji_preserved_on_utf8(monkeypatch):
    """A UTF-8 console should keep the real glyphs."""
    monkeypatch.setattr(sys, "stdout", _FakeStdout("utf-8"))
    text = "\U0001F7E2 **Official**"
    assert to_console(text) == text


def test_em_dash_is_left_alone_on_cp1250(monkeypatch):
    """
    cp1250 contains U+2014, so substituting it would be gratuitous damage.
    This pins the 'only replace what is genuinely unrepresentable' rule.
    """
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    assert to_console("posted — ok") == "posted — ok"


def test_box_drawing_transliterated_on_cp1250(monkeypatch):
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    out = to_console("┌─ embed\n│ body\n└─")
    assert "┌" not in out and "│" not in out
    out.encode("cp1250")


def test_unknown_unencodable_char_degrades_without_raising(monkeypatch):
    """A character not in the table must still not blow up."""
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    out = to_console("weather ☄ comet")  # U+2604 not in the table
    out.encode("cp1250")
    assert "comet" in out


def test_safe_print_never_raises_on_ascii_only_console(monkeypatch):
    fake = _FakeStdout("ascii")
    monkeypatch.setattr(sys, "stdout", fake)
    safe_print("\U0001F7E2 official — done")  # must not raise
    assert "official" in fake.getvalue()


def test_empty_string_is_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    assert to_console("") == ""


def test_full_digest_preview_is_printable_on_cp1250(monkeypatch):
    """End-to-end: a real rendered payload must survive a cp1250 console."""
    from src import credibility
    from src.digest import DigestEntry, render_digest
    from src.discord_client import preview

    payload = render_digest(
        [
            DigestEntry(1, "Extended Look coming August 27", "https://x.test/a",
                        "Rockstar Games", credibility.LABEL_OFFICIAL),
            DigestEntry(2, "Leaked footage circulating", "https://x.test/b",
                        "Eurogamer", credibility.LABEL_RUMOUR),
        ],
        health_line="9 feeds · 8 ok · 1 failing",
        date_label="2026-08-25",
    )
    monkeypatch.setattr(sys, "stdout", _FakeStdout("cp1250"))
    to_console(preview(payload)).encode("cp1250")  # must not raise
