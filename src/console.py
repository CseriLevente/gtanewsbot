"""
ASCII-safe console output.

The Windows console here runs cp1250, which cannot encode the emoji used in
Discord embeds — printing one raises UnicodeEncodeError and kills the command.
Discord itself is fine (the payload is UTF-8 JSON); only the local echo breaks.

This mirrors the approach already used in tozsdeturbo-bot, where the CLI prints
an ASCII-safe summary while the emoji version goes to the messaging platform.
The rule: never let a cosmetic encoding problem crash an operator command.
"""
from __future__ import annotations

import sys

# Emoji → ASCII stand-ins. Keeps the label distinction visible in a cp1250 console.
_TRANSLITERATIONS = {
    "\U0001F7E2": "[OK]",      # green circle  — Official
    "\U0001F535": "[--]",      # blue circle   — Report
    "\U0001F7E0": "[??]",      # orange circle — Rumour
    "…": "...",           # ellipsis
    "·": "-",             # middle dot
    "—": "-",             # em dash
    "–": "-",             # en dash
    "→": "->",
    "←": "<-",
    "┌": "+",             # box drawing, used by the dry-run preview frame
    "│": "|",
    "└": "+",
    "─": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
}


def to_console(text: str) -> str:
    """
    Return *text* rendered safely for the current console encoding.

    Encodability is tested UP FRONT rather than by catching an exception,
    because stdout is reconfigured with errors="replace" at startup: print()
    therefore never raises, it silently emits '?'. Checking first is what lets
    us substitute a readable '[OK]' instead of an opaque '?'.

    On a UTF-8 console the text is returned untouched, so the emoji survive.
    """
    if not text:
        return text

    encoding = (getattr(sys.stdout, "encoding", None) or "utf-8")
    try:
        text.encode(encoding)
        return text  # console handles it; keep the original glyphs
    except (UnicodeEncodeError, LookupError):
        pass

    out = text
    for src, dst in _TRANSLITERATIONS.items():
        if src in out:
            out = out.replace(src, dst)
    try:
        out.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        # Anything still unrepresentable becomes '?' rather than an exception.
        out = out.encode(encoding, errors="replace").decode(encoding, errors="replace")
    return out


def safe_print(*parts: object, **kwargs) -> None:
    """print() that cannot raise UnicodeEncodeError and degrades readably."""
    text = to_console(" ".join(str(p) for p in parts))
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:  # pragma: no cover - defensive
        print(text.encode("ascii", errors="replace").decode("ascii"), **kwargs)
