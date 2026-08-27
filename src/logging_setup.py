"""
Centralised logging configuration with secret redaction.

Mirrors the pattern used by tozsdeturbo-bot. Three secrets can reach a log line
here, and each one is a real incident if it does:

  * DISCORD_BOT_TOKEN — appears in the Authorization header, and httpx logs
    request URLs at INFO. A leaked bot token lets anyone post as the bot.
  * a Discord WEBHOOK URL — the token is part of the URL path itself. Anyone
    holding it can post to the channel with an arbitrary username and avatar,
    i.e. impersonate this news bot perfectly. There is no rotate API; you
    delete and recreate.
  * ANTHROPIC_API_KEY — billable.
"""
from __future__ import annotations

import logging
import os
import re

# Discord bot tokens: 3 dot-separated base64url segments, first is a snowflake.
_DISCORD_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{20,30}\.[A-Za-z0-9_-]{6,10}\.[A-Za-z0-9_-]{25,110}\b")
# Discord webhook URLs — the trailing segment is the credential.
_WEBHOOK_RE = re.compile(r"https://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+")
# Anthropic keys.
_ANTHROPIC_RE = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")

_REDACTED_TOKEN = "<REDACTED_DISCORD_TOKEN>"
_REDACTED_WEBHOOK = "<REDACTED_DISCORD_WEBHOOK>"
_REDACTED_KEY = "<REDACTED_ANTHROPIC_KEY>"

# Env vars whose literal values must never appear in a log line.
_LIVE_SECRET_VARS = ("DISCORD_BOT_TOKEN", "ANTHROPIC_API_KEY", "DISCORD_WEBHOOK_URL")


def redact(text: str) -> str:
    """Return *text* with every known secret shape redacted."""
    if not text:
        return text
    out = _WEBHOOK_RE.sub(_REDACTED_WEBHOOK, text)
    out = _ANTHROPIC_RE.sub(_REDACTED_KEY, out)
    out = _DISCORD_TOKEN_RE.sub(_REDACTED_TOKEN, out)
    # Belt-and-braces: scrub the live values even if they don't match a pattern.
    for var in _LIVE_SECRET_VARS:
        live = os.environ.get(var, "").strip()
        if live and len(live) >= 12 and live in out:
            out = out.replace(live, f"<REDACTED_{var}>")
    return out


class RedactingFilter(logging.Filter):
    """Logging filter that redacts secrets from messages and args."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: redact(v) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                else:
                    record.args = tuple(
                        redact(a) if isinstance(a, str) else a for a in record.args
                    )
        except Exception:
            # Never let logging redaction raise.
            pass
        return True


def quiet_http_loggers() -> None:
    """Stop httpx/httpcore from logging request URLs (which carry credentials)."""
    for name in ("httpx", "httpcore", "anthropic"):
        logging.getLogger(name).setLevel(logging.WARNING)


def install_redaction(root: logging.Logger | None = None) -> RedactingFilter:
    """Attach the RedactingFilter to a logger (root by default) and its handlers."""
    target = root or logging.getLogger()
    flt = RedactingFilter()
    target.addFilter(flt)
    for h in target.handlers:
        h.addFilter(flt)
    return flt


def configure_logging() -> None:
    """Apply both protections. Safe to call multiple times."""
    quiet_http_loggers()
    install_redaction()
