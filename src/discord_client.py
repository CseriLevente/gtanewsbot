"""
Discord REST client — post-only.

No gateway, no discord.py, no intents: this bot only sends messages. A bot
TOKEN is used rather than a webhook because AutoMod configuration lives on
/guilds/{id}/auto-moderation/rules and requires MANAGE_GUILD, which a webhook
token can never reach. We hold the token anyway, so a webhook would be a second
credential for no gain.

Two rules that are not negotiable:

  1. `User-Agent: DiscordBot (<url>, <version>)` is MANDATORY. httpx's default
     UA can be Cloudflare-blocked, and the failure is opaque.
  2. 401 and 403 are FATAL and must never be retried. 10,000 invalid requests
     in 10 minutes earns a Cloudflare IP ban — on a residential connection that
     takes the whole household off Discord, including the operator's own client.
     So an auth failure latches a PERSISTED kill switch: the process is
     short-lived, so an in-memory flag would reset in 15 minutes and resume
     hammering.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx

from src import digest, storage
from src.console import safe_print

logger = logging.getLogger(__name__)

API_BASE = "https://discord.com/api/v10"
BOT_VERSION = "1.0"
BOT_URL = "https://github.com/your-name/gta6-news-bot"

MAX_RETRIES = 3


class DiscordFatalError(RuntimeError):
    """Auth/permission failure. Never retry; kill switch is engaged."""


class DiscordPostResult:
    def __init__(self, *, sent: bool, message_id: str | None, dry_run: bool, detail: str = ""):
        self.sent = sent
        self.message_id = message_id
        self.dry_run = dry_run
        self.detail = detail


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        # Mandatory and specifically formatted. Do not replace with a browser UA.
        "User-Agent": f"DiscordBot ({BOT_URL}, {BOT_VERSION})",
    }


def preview(payload: dict) -> str:
    """Render a payload as text for --dry-run, mirroring what readers would see."""
    lines: list[str] = []
    if payload.get("content"):
        lines.append(f"[content] {payload['content']}")
    for i, e in enumerate(payload.get("embeds", [])):
        lines.append(f"┌─ embed[{i}] colour=#{e.get('color', 0):06X}")
        if (e.get("author") or {}).get("name"):
            lines.append(f"│ author: {e['author']['name']}")
        if e.get("title"):
            lines.append(f"│ TITLE: {e['title']}")
        if e.get("description"):
            for ln in e["description"].split("\n"):
                lines.append(f"│ {ln}")
        if (e.get("footer") or {}).get("text"):
            lines.append(f"│ footer: {e['footer']['text']}")
        lines.append("└─")
    total = digest.embed_total_chars(payload)
    lines.append(
        f"[limits] embed chars {total}/{digest.EMBED_TOTAL_MAX} · "
        f"embeds {len(payload.get('embeds', []))}/10 · "
        f"allowed_mentions={json.dumps(payload.get('allowed_mentions'))}"
    )
    return "\n".join(lines)


async def post_message(
    conn,
    *,
    token: str | None,
    channel_id: str | None,
    payload: dict,
    dry_run: bool,
    kind: str,
    item_id: int | None = None,
) -> DiscordPostResult:
    """
    Post one message to a channel.

    Validates limits first, honours the persisted kill switch, and treats auth
    failures as terminal.
    """
    digest.assert_within_limits(payload)

    if dry_run:
        safe_print(preview(payload))
        await storage.log_post(conn, kind=kind, item_id=item_id,
                               discord_message_id=None, dry_run=True)
        return DiscordPostResult(sent=False, message_id=None, dry_run=True,
                                 detail="dry-run: nothing sent")

    if await storage.kill_switch_engaged(conn):
        reason = await storage.get_flag(conn, "discord_kill_switch_reason", "unknown")
        return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                                 detail=f"kill switch engaged: {reason}")

    if not token or not channel_id:
        return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                                 detail="DISCORD_BOT_TOKEN or DISCORD_NEWS_CHANNEL_ID not set")

    url = f"{API_BASE}/channels/{channel_id}/messages"
    async with httpx.AsyncClient(timeout=20.0, headers=_headers(token)) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(url, json=payload)
            except Exception as exc:
                if attempt == MAX_RETRIES:
                    return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                                             detail=f"transport error: {exc}")
                await asyncio.sleep(2 ** attempt)
                continue

            if resp.status_code in (401, 403):
                # FATAL. Do not retry, do not loop, latch the switch.
                body = resp.text[:300]
                await storage.engage_kill_switch(
                    conn, f"HTTP {resp.status_code} from Discord: {body}"
                )
                raise DiscordFatalError(
                    f"Discord returned {resp.status_code} — token invalid or missing "
                    f"permissions. Posting has been disabled and will stay disabled "
                    f"until you clear the kill switch (`clear-kill-switch`). "
                    f"Retrying auth failures risks a Cloudflare IP ban. Body: {body}"
                )

            if resp.status_code == 429:
                retry_after = 1.0
                try:
                    retry_after = float(resp.json().get("retry_after", 1.0))
                except Exception:
                    retry_after = float(resp.headers.get("Retry-After", "1") or 1)
                scope = resp.headers.get("X-RateLimit-Scope", "?")
                logger.warning(
                    "Discord 429 (scope=%s, bucket=%s) — sleeping %.2fs",
                    scope, resp.headers.get("X-RateLimit-Bucket", "?"), retry_after,
                )
                if attempt == MAX_RETRIES:
                    return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                                             detail=f"rate limited (scope={scope})")
                await asyncio.sleep(min(retry_after + 0.5, 30))
                continue

            if 200 <= resp.status_code < 300:
                mid = None
                try:
                    mid = str(resp.json().get("id"))
                except Exception:
                    pass
                await storage.log_post(conn, kind=kind, item_id=item_id,
                                       discord_message_id=mid, dry_run=False)
                return DiscordPostResult(sent=True, message_id=mid, dry_run=False,
                                         detail="sent")

            if resp.status_code == 400:
                # Our payload is malformed. Retrying cannot help, and 400s count
                # toward the invalid-request ban budget.
                return DiscordPostResult(
                    sent=False, message_id=None, dry_run=False,
                    detail=f"HTTP 400 rejected the message: {resp.text[:300]}",
                )

            if attempt == MAX_RETRIES:
                return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                                         detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
            await asyncio.sleep(2 ** attempt)

    return DiscordPostResult(sent=False, message_id=None, dry_run=False,
                             detail="exhausted retries")


async def digest_already_in_channel(
    *, token: str | None, channel_id: str | None, date_label: str,
    limit: int = 15, timeout: float = 20.0,
) -> tuple[bool | None, str]:
    """
    Ask Discord whether today's digest is already in the channel.

    Returns (found, detail); `found` is None when the question could not be
    answered (no credentials, network error, missing permission), so the caller
    can decide how to treat an inconclusive answer.

    WHY THIS EXISTS
    ---------------
    The once-per-day guarantee was backed only by a `digest_runs` row. On this
    operator's machine (2026-08-27) commits made by the Task Scheduler process
    were visible to that process but never reached the shared database file,
    while the same code run interactively persisted normally. The digest posted
    correctly two days running while `digest_runs` stayed empty — so the guard
    was inert, and nothing but luck prevented a repeat post every 15 minutes.

    A guard whose evidence lives in the same place as the failure is no guard.
    Discord is the authority on what is in the channel, it is the system a
    duplicate would appear in, and reading the last few messages costs one
    request. This makes the check immune to local storage problems entirely.

    Requires READ_MESSAGE_HISTORY, which the recommended #news overwrite grants.
    """
    if not token or not channel_id:
        return None, "no credentials to check the channel with"
    url = f"{API_BASE}/channels/{channel_id}/messages?limit={int(limit)}"
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=_headers(token)) as client:
            resp = await client.get(url)
    except Exception as exc:
        return None, f"could not read channel history: {type(exc).__name__}: {exc}"

    if resp.status_code == 403:
        return None, ("cannot read channel history (403) — grant the bot "
                      "READ_MESSAGE_HISTORY in the news channel to enable the "
                      "duplicate-digest guard")
    if resp.status_code != 200:
        return None, f"channel history returned HTTP {resp.status_code}"

    try:
        messages = resp.json()
    except Exception:
        return None, "channel history was not valid JSON"

    for m in messages:
        # Only our own messages count, and only a digest embed for THIS date.
        if not (m.get("author") or {}).get("bot"):
            continue
        for e in m.get("embeds") or []:
            title = e.get("title") or ""
            if date_label in title and "Digest" in title:
                return True, f"digest for {date_label} already in channel (message {m.get('id')})"
    return False, f"no digest for {date_label} found in the last {len(messages)} messages"


async def title_already_in_channel(
    *, token: str | None, channel_id: str | None, title: str,
    limit: int = 30, timeout: float = 20.0,
) -> tuple[bool | None, str]:
    """
    Has this exact story already been announced in the channel?

    The instant-alert equivalent of digest_already_in_channel(), and needed for
    the same reason: the "already alerted" flag lives in `items.state`, and on
    this machine commits from the scheduled process do not reach the shared
    database. Without an external check, a first-party story could be announced
    — and the opt-in role pinged — on every 15-minute run until the feed item
    aged out. Repeated 03:00 pings is the worst outcome this bot can produce.

    Matches on the embed title, which for an instant alert is the item headline
    verbatim. Returns None when the question cannot be answered.
    """
    if not token or not channel_id:
        return None, "no credentials to check the channel with"
    needle = " ".join((title or "").split()).casefold()
    if len(needle) < 12:
        return None, "title too short to match reliably"

    url = f"{API_BASE}/channels/{channel_id}/messages?limit={int(limit)}"
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=_headers(token)) as client:
            resp = await client.get(url)
    except Exception as exc:
        return None, f"could not read channel history: {type(exc).__name__}: {exc}"
    if resp.status_code == 403:
        return None, ("cannot read channel history (403) — grant READ_MESSAGE_HISTORY "
                      "to enable the duplicate-alert guard")
    if resp.status_code != 200:
        return None, f"channel history returned HTTP {resp.status_code}"
    try:
        messages = resp.json()
    except Exception:
        return None, "channel history was not valid JSON"

    for m in messages:
        if not (m.get("author") or {}).get("bot"):
            continue
        for e in m.get("embeds") or []:
            existing = " ".join((e.get("title") or "").split()).casefold()
            if existing and existing == needle:
                return True, f"already announced (message {m.get('id')})"
    return False, f"not found in the last {len(messages)} messages"
