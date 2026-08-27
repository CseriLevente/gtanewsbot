"""
Apply AutoMod rules via the Discord API.

The bot already holds MANAGE_GUILD, which is the permission AutoMod requires, so
the rules can be created from config instead of hand-typed into the UI. That
matters here for a boring reason: the file-host rule alone is ~48 entries, and
transcribing 150+ keywords by hand is where mistakes happen.

Design constraints:
  * DRY RUN BY DEFAULT. This mutates a live server, so nothing happens without
    an explicit --yes.
  * IDEMPOTENT. A rule whose name already exists is skipped, never duplicated
    and never silently overwritten. Re-running is safe.
  * NO TIMEOUT ACTIONS. A TIMEOUT action needs the bot to hold
    MODERATE_MEMBERS (1 << 40), which is not in the recommended invite. Rules
    are created with BLOCK_MESSAGE + SEND_ALERT_MESSAGE only; add timeouts by
    hand if you want them.

WHAT THIS CANNOT DO: AutoMod does not scan attachments, images or video at all.
The real threat in a GTA 6 server is a dragged-in .mp4, which no rule here can
see. That control is a permission — deny Attach Files and Embed Links to
@everyone server-wide.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

from src import paths

logger = logging.getLogger(__name__)

API_BASE = "https://discord.com/api/v10"

# Trigger types
TRIGGER_KEYWORD = 1
# Event types
EVENT_MESSAGE_SEND = 1
# Action types
ACTION_BLOCK_MESSAGE = 1
ACTION_SEND_ALERT = 2
ACTION_TIMEOUT = 3

TRIGGER_NAMES = {1: "KEYWORD", 3: "SPAM", 4: "KEYWORD_PRESET",
                 5: "MENTION_SPAM", 6: "MEMBER_PROFILE"}
ACTION_NAMES = {1: "BLOCK_MESSAGE", 2: "SEND_ALERT_MESSAGE", 3: "TIMEOUT",
                4: "BLOCK_MEMBER_INTERACTION"}

# Documented limits.
MAX_KEYWORD_RULES = 6
MAX_KEYWORDS_PER_RULE = 1000
MAX_REGEX_PER_RULE = 10
MAX_REGEX_CHARS = 260
MAX_CUSTOM_MESSAGE = 150

AUTOMOD_JSON = os.path.join(paths.CONFIG_DIR, "automod.json")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/your-name/gta6-news-bot, 1.0)",
    }


def load_rules(path: str | None = None) -> list[dict]:
    with open(path or AUTOMOD_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)["rules"]


def validate(rules: list[dict]) -> list[str]:
    """Check every rule against the documented limits. Returns problems."""
    problems: list[str] = []
    keyword_rules = [r for r in rules if r.get("enabled", True)]
    if len(keyword_rules) > MAX_KEYWORD_RULES:
        problems.append(
            f"{len(keyword_rules)} enabled KEYWORD rules exceeds the limit of "
            f"{MAX_KEYWORD_RULES} per guild"
        )
    for r in rules:
        name = r.get("name", "<unnamed>")
        kws = r.get("keywords") or []
        rxs = r.get("regex_patterns") or []
        if not kws and not rxs:
            problems.append(f"{name}: has neither keywords nor regex_patterns")
        if len(kws) > MAX_KEYWORDS_PER_RULE:
            problems.append(f"{name}: {len(kws)} keywords exceeds {MAX_KEYWORDS_PER_RULE}")
        if len(rxs) > MAX_REGEX_PER_RULE:
            problems.append(f"{name}: {len(rxs)} regex patterns exceeds {MAX_REGEX_PER_RULE}")
        for rx in rxs:
            if len(rx) > MAX_REGEX_CHARS:
                problems.append(f"{name}: a regex is {len(rx)} chars, over {MAX_REGEX_CHARS}")
            for bad, why in (("(?=", "lookahead"), ("(?!", "negative lookahead"),
                             ("(?<", "lookbehind"), ("\\1", "backreference")):
                if bad in rx:
                    problems.append(
                        f"{name}: regex uses {why} ('{bad}'), which Rust regex does not support"
                    )
        msg = r.get("custom_message") or ""
        if len(msg) > MAX_CUSTOM_MESSAGE:
            problems.append(
                f"{name}: custom_message is {len(msg)} chars, over {MAX_CUSTOM_MESSAGE}"
            )
        if r.get("block") and not msg:
            problems.append(f"{name}: blocks messages but has no custom_message")
    return problems


def build_payload(rule: dict, *, alert_channel_id: str | None) -> dict:
    """Turn a config rule into a Create Auto Moderation Rule body."""
    actions: list[dict] = []
    if rule.get("block"):
        actions.append({
            "type": ACTION_BLOCK_MESSAGE,
            "metadata": {"custom_message": rule["custom_message"]},
        })
    if alert_channel_id:
        actions.append({
            "type": ACTION_SEND_ALERT,
            "metadata": {"channel_id": str(alert_channel_id)},
        })
    if not actions:
        # An alert-only rule with no alert channel would do literally nothing.
        raise ValueError(
            f"rule {rule['name']!r} would have no actions — it does not block and "
            f"no alert channel was given. Pass --alert-channel."
        )

    metadata: dict = {}
    if rule.get("keywords"):
        metadata["keyword_filter"] = rule["keywords"]
    if rule.get("regex_patterns"):
        metadata["regex_patterns"] = rule["regex_patterns"]

    return {
        "name": rule["name"],
        "event_type": EVENT_MESSAGE_SEND,
        "trigger_type": TRIGGER_KEYWORD,
        "trigger_metadata": metadata,
        "actions": actions,
        "enabled": bool(rule.get("enabled", True)),
        "exempt_roles": [str(r) for r in (rule.get("exempt_roles") or [])],
        # Deliberately empty: there is no channel where leak links are acceptable.
        "exempt_channels": [],
    }


async def list_rules(token: str, guild_id: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=20.0, headers=_headers(token)) as client:
        resp = await client.get(f"{API_BASE}/guilds/{guild_id}/auto-moderation/rules")
        if resp.status_code == 403:
            raise PermissionError(
                "403 reading AutoMod rules — the bot lacks MANAGE_GUILD. Re-invite it "
                "with `python -m src.main invite-url` (which includes MANAGE_GUILD)."
            )
        resp.raise_for_status()
        return resp.json()


async def guild_id_for_channel(token: str, channel_id: str) -> str:
    async with httpx.AsyncClient(timeout=20.0, headers=_headers(token)) as client:
        resp = await client.get(f"{API_BASE}/channels/{channel_id}")
        resp.raise_for_status()
        return str(resp.json()["guild_id"])


async def apply_rules(
    *,
    token: str,
    guild_id: str,
    rules: list[dict],
    alert_channel_id: str | None,
    dry_run: bool = True,
) -> list[tuple[str, str]]:
    """
    Create any rule whose name is not already present.

    Returns a list of (rule_name, outcome) where outcome is one of
    created / would-create / skipped-exists / error: ...
    """
    existing = await list_rules(token, guild_id)
    existing_names = {r["name"] for r in existing}
    results: list[tuple[str, str]] = []

    async with httpx.AsyncClient(timeout=30.0, headers=_headers(token)) as client:
        for rule in rules:
            name = rule["name"]
            if name in existing_names:
                results.append((name, "skipped-exists"))
                continue
            try:
                payload = build_payload(rule, alert_channel_id=alert_channel_id)
            except ValueError as exc:
                results.append((name, f"error: {exc}"))
                continue

            if dry_run:
                kw = len(payload["trigger_metadata"].get("keyword_filter", []))
                rx = len(payload["trigger_metadata"].get("regex_patterns", []))
                acts = "+".join(ACTION_NAMES.get(a["type"], "?") for a in payload["actions"])
                results.append((name, f"would-create ({kw} keywords, {rx} regex, {acts})"))
                continue

            resp = await client.post(
                f"{API_BASE}/guilds/{guild_id}/auto-moderation/rules", json=payload
            )
            if 200 <= resp.status_code < 300:
                results.append((name, "created"))
            else:
                results.append((name, f"error: HTTP {resp.status_code} {resp.text[:200]}"))
    return results
