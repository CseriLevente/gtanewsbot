"""
Live Discord configuration diagnostics.

A setup guide can tell you which switches to flip; it cannot tell you whether
you actually flipped them. This module asks Discord directly and names the exact
missing permission, so the failure mode is a clear sentence instead of a 403 at
18:00 with nobody watching.

Everything here is READ-ONLY (GET requests). It never posts, never edits a
setting, and never mutates the guild. `post-test` is a separate, explicit
command.

Permission resolution follows Discord's documented algorithm:
    ADMINISTRATOR short-circuits everything
    -> base = @everyone role perms OR'd with each of the bot's role perms
    -> channel @everyone overwrite (deny then allow)
    -> union of role denies, then union of role allows
    -> member-specific overwrite (deny then allow)
Getting the ORDER wrong silently reports the wrong answer, which is worse than
not checking, so it is written out explicitly rather than approximated.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://discord.com/api/v10"
BOT_VERSION = "1.0"
BOT_URL = "https://github.com/your-name/gta6-news-bot"

# Permission bits. Values are (1 << position) per Discord's permissions table.
PERMS: dict[str, int] = {
    "CREATE_INSTANT_INVITE": 1 << 0,
    "KICK_MEMBERS": 1 << 1,
    "BAN_MEMBERS": 1 << 2,
    "ADMINISTRATOR": 1 << 3,
    "MANAGE_CHANNELS": 1 << 4,
    "MANAGE_GUILD": 1 << 5,
    "ADD_REACTIONS": 1 << 6,
    "VIEW_AUDIT_LOG": 1 << 7,
    "VIEW_CHANNEL": 1 << 10,
    "SEND_MESSAGES": 1 << 11,
    "MANAGE_MESSAGES": 1 << 13,
    "EMBED_LINKS": 1 << 14,
    "ATTACH_FILES": 1 << 15,
    "READ_MESSAGE_HISTORY": 1 << 16,
    "MENTION_EVERYONE": 1 << 17,
    "MANAGE_ROLES": 1 << 28,
    "MANAGE_WEBHOOKS": 1 << 29,
    "SEND_MESSAGES_IN_THREADS": 1 << 38,
    "MODERATE_MEMBERS": 1 << 40,
}

# What the bot genuinely needs, and why. Least privilege: it never reads message
# content, never deletes, never manages members.
REQUIRED_CHANNEL_PERMS = {
    "VIEW_CHANNEL": "see the news channel at all",
    "SEND_MESSAGES": "post the daily digest",
    "EMBED_LINKS": "render the digest as an embed (without this the embed is silently dropped)",
}
# Only needed when instant alerts should ping a NON-MENTIONABLE opt-in role.
ROLE_PING_PERM = "MENTION_EVERYONE"
# Only needed if the bot should manage AutoMod rules rather than you hand-editing them.
AUTOMOD_PERM = "MANAGE_GUILD"

CHANNEL_TYPES = {
    0: "text",
    5: "announcement",
    15: "forum",
    11: "public thread",
    12: "private thread",
}


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bot {token}",
        "User-Agent": f"DiscordBot ({BOT_URL}, {BOT_VERSION})",
    }


def decode_permissions(bits: int) -> list[str]:
    """Names of the permissions present in a bitfield."""
    return sorted(name for name, bit in PERMS.items() if bits & bit)


def invite_url(client_id: str, permissions: int) -> str:
    """The OAuth2 URL that adds this bot to a guild with exactly `permissions`."""
    return (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={client_id}"
        f"&scope=bot"
        f"&permissions={permissions}"
    )


def minimal_permissions(*, ping_role: bool = False, manage_automod: bool = True) -> int:
    """
    Sum the permission bits this bot needs AT GUILD LEVEL (the invite integer).

    Kept as a function rather than a magic constant so the number can be
    re-derived and audited instead of trusted.

    `ping_role` defaults to FALSE deliberately. MENTION_EVERYONE is a dangerous
    guild-wide bit, and it does not need to be granted guild-wide: a channel
    permission overwrite can grant a permission the bot's role does not have,
    so it is allowed for the bot in #news ONLY (see BOT_CHANNEL_ALLOW below).
    That gives the best of both — the opt-in role stays NON-mentionable so no
    member can ping it anywhere, while the bot can ping it in the news channel.
    """
    total = 0
    for name in REQUIRED_CHANNEL_PERMS:
        total |= PERMS[name]
    if ping_role:
        total |= PERMS[ROLE_PING_PERM]
    if manage_automod:
        total |= PERMS[AUTOMOD_PERM]
    return total


# --- channel overwrite masks ------------------------------------------------
# Permission overwrites are serialised as STRINGS in API v8+, so send "84992"
# not 84992. The @everyone role's id is identical to the guild id.

def bot_channel_allow(*, mention_role: bool = True, pin: bool = False) -> int:
    """What to ALLOW the bot in #news, as a member overwrite (type 1).

    A member overwrite is the highest-precedence allow layer in Discord's
    resolution order, so it survives any role deny and any position in the role
    hierarchy — which is what makes a locked-down channel still work for the bot.
    """
    total = PERMS["VIEW_CHANNEL"] | PERMS["SEND_MESSAGES"] | PERMS["EMBED_LINKS"]
    total |= PERMS["READ_MESSAGE_HISTORY"]
    if mention_role:
        total |= PERMS["MENTION_EVERYONE"]
    if pin:
        # PIN_MESSAGES was split out of MANAGE_MESSAGES effective 2026-02-23;
        # MANAGE_MESSAGES alone no longer permits pinning.
        total |= 1 << 51
    return total


def everyone_news_deny() -> int:
    """
    What to DENY @everyone in #news so it is read-only.

    Denying SEND_MESSAGES implicitly neutralises EMBED_LINKS, ATTACH_FILES and
    MENTION_EVERYONE in that channel. But SEND_MESSAGES is NOT inherited by
    threads — without the three thread bits, a member can still drop a leaked
    clip into a thread hanging off the bot's own digest post.
    """
    return (
        PERMS["SEND_MESSAGES"]
        | (1 << 35)   # CREATE_PUBLIC_THREADS
        | (1 << 36)   # CREATE_PRIVATE_THREADS
        | PERMS["SEND_MESSAGES_IN_THREADS"]
    )


def everyone_news_allow() -> int:
    """What @everyone keeps in #news: read the channel and its history."""
    return PERMS["VIEW_CHANNEL"] | PERMS["READ_MESSAGE_HISTORY"]


# Server-wide media hardening: remove these from the @everyone ROLE. AutoMod
# cannot scan attachments, images or video at all, so this permission is the
# only real control against a member uploading leaked media.
SERVER_MEDIA_DENY = PERMS["EMBED_LINKS"] | PERMS["ATTACH_FILES"]  # 49152


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""


@dataclass
class Diagnosis:
    checks: list[Check] = field(default_factory=list)
    bot_name: str | None = None
    guild_id: str | None = None
    channel_name: str | None = None

    def add(self, name: str, ok: bool, detail: str, fix: str = "") -> None:
        self.checks.append(Check(name, ok, detail, fix))

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    @property
    def ok(self) -> bool:
        return not self.failures


async def _get(client: httpx.AsyncClient, path: str) -> tuple[int, object]:
    resp = await client.get(f"{API_BASE}{path}")
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, resp.text


def compute_channel_permissions(
    *,
    guild_id: str,
    everyone_perms: int,
    member_role_perms: list[int],
    member_role_ids: set[str],
    bot_user_id: str,
    overwrites: list[dict],
) -> int:
    """
    Effective permissions for the bot in one channel.

    Implements Discord's documented resolution order exactly.
    """
    base = everyone_perms
    for p in member_role_perms:
        base |= p

    if base & PERMS["ADMINISTRATOR"]:
        return sum(PERMS.values()) | PERMS["ADMINISTRATOR"]

    perms = base

    # 1. @everyone channel overwrite (its id equals the guild id)
    for ow in overwrites:
        if str(ow.get("id")) == str(guild_id) and int(ow.get("type", 0)) == 0:
            perms &= ~int(ow.get("deny", 0) or 0)
            perms |= int(ow.get("allow", 0) or 0)
            break

    # 2. all role overwrites: denies first, then allows
    role_deny = 0
    role_allow = 0
    for ow in overwrites:
        if int(ow.get("type", 0)) != 0:
            continue
        oid = str(ow.get("id"))
        if oid == str(guild_id) or oid not in member_role_ids:
            continue
        role_deny |= int(ow.get("deny", 0) or 0)
        role_allow |= int(ow.get("allow", 0) or 0)
    perms &= ~role_deny
    perms |= role_allow

    # 3. member-specific overwrite wins outright
    for ow in overwrites:
        if int(ow.get("type", 0)) == 1 and str(ow.get("id")) == str(bot_user_id):
            perms &= ~int(ow.get("deny", 0) or 0)
            perms |= int(ow.get("allow", 0) or 0)
            break

    return perms


async def diagnose(
    *,
    token: str,
    channel_id: str,
    role_id: str | None,
    check_automod: bool = True,
    timeout: float = 20.0,
) -> Diagnosis:
    """Interrogate Discord and report exactly what is wrong, if anything."""
    d = Diagnosis()

    if not token:
        d.add("token", False, "DISCORD_BOT_TOKEN is empty",
              "Create a bot at discord.com/developers/applications and paste its token into .env")
        return d
    if not channel_id:
        d.add("channel", False, "DISCORD_NEWS_CHANNEL_ID is empty",
              "Right-click your #news channel -> Copy Channel ID (needs Developer Mode on)")
        return d

    async with httpx.AsyncClient(timeout=timeout, headers=_headers(token)) as client:
        # --- token -------------------------------------------------------
        status, me = await _get(client, "/users/@me")
        if status == 401:
            d.add("token", False, "Discord rejected the token (401)",
                  "The token is wrong or was regenerated. Copy it again from the Bot tab. "
                  "Note it is the BOT token, not the application Client Secret.")
            return d
        if status != 200 or not isinstance(me, dict):
            d.add("token", False, f"unexpected response {status}: {str(me)[:200]}")
            return d
        bot_user_id = str(me.get("id"))
        d.bot_name = f"{me.get('username')} ({bot_user_id})"
        d.add("token", True, f"authenticated as {d.bot_name}")

        # --- channel -----------------------------------------------------
        status, ch = await _get(client, f"/channels/{channel_id}")
        if status in (403, 404) or not isinstance(ch, dict):
            d.add("channel", False,
                  f"cannot see channel {channel_id} (HTTP {status})",
                  "Either the ID is wrong, or the bot has not been invited to that server. "
                  "Re-run the invite URL from `python -m src.main invite-url`.")
            return d
        guild_id = str(ch.get("guild_id") or "")
        d.guild_id = guild_id
        d.channel_name = ch.get("name")
        ctype = int(ch.get("type", -1))
        d.add("channel", True,
              f"#{ch.get('name')} (type {ctype} = {CHANNEL_TYPES.get(ctype, 'unknown')}), "
              f"guild {guild_id}")
        if ctype not in (0, 5):
            d.add("channel type", False,
                  f"channel type {ctype} ({CHANNEL_TYPES.get(ctype, 'unknown')}) is not a "
                  f"text or announcement channel",
                  "Use a normal Text channel, or an Announcement channel if you want "
                  "followers to be able to subscribe.")

        # --- roles + effective permissions --------------------------------
        status, roles = await _get(client, f"/guilds/{guild_id}/roles")
        status2, member = await _get(client, f"/guilds/{guild_id}/members/{bot_user_id}")
        if status != 200 or status2 != 200 or not isinstance(roles, list) or not isinstance(member, dict):
            d.add("permissions", False,
                  f"could not read guild roles/membership (HTTP {status}/{status2})",
                  "This usually means the bot is not actually in the guild.")
            return d

        role_by_id = {str(r["id"]): r for r in roles}
        everyone = role_by_id.get(str(guild_id), {})
        everyone_perms = int(everyone.get("permissions", 0) or 0)
        member_role_ids = {str(r) for r in (member.get("roles") or [])}
        member_role_perms = [
            int(role_by_id[rid].get("permissions", 0) or 0)
            for rid in member_role_ids if rid in role_by_id
        ]

        effective = compute_channel_permissions(
            guild_id=guild_id,
            everyone_perms=everyone_perms,
            member_role_perms=member_role_perms,
            member_role_ids=member_role_ids,
            bot_user_id=bot_user_id,
            overwrites=list(ch.get("permission_overwrites") or []),
        )

        for name, why in REQUIRED_CHANNEL_PERMS.items():
            has = bool(effective & PERMS[name])
            d.add(
                f"perm {name}", has,
                f"{'granted' if has else 'MISSING'} — needed to {why}",
                "" if has else (
                    f"Channel settings -> Permissions -> add the bot's role and allow "
                    f"{name}. Nothing will post without it."
                ),
            )

        # --- opt-in ping role ---------------------------------------------
        if role_id:
            role = role_by_id.get(str(role_id))
            if role is None:
                d.add("ping role", False, f"role {role_id} does not exist in this guild",
                      "Copy the role ID again, or clear DISCORD_NEWS_ROLE_ID to disable pings.")
            elif role.get("managed"):
                # Inviting a bot auto-creates a MANAGED role named after it, and
                # it sorts right next to the real roles in the UI — so it is easy
                # to copy by mistake. Discord will not let a human hold a managed
                # role, so pinging it notifies nobody and reports no error.
                owner = (role.get("tags") or {}).get("bot_id")
                d.add("ping role", False,
                      f"@{role.get('name')} is a MANAGED integration role"
                      + (f" belonging to bot {owner}" if owner else "")
                      + " — members cannot be given it, so a ping reaches nobody",
                      "Create your own role (Server Settings -> Roles -> new role, zero "
                      "permissions) and use ITS id. A bot's own role is auto-created on "
                      "invite and is not assignable to people.")
            else:
                mentionable = bool(role.get("mentionable"))
                has_mention_everyone = bool(effective & PERMS[ROLE_PING_PERM])
                if mentionable:
                    d.add("ping role", True,
                          f"@{role.get('name')} is mentionable by anyone",
                          "Recommended: set the role to NOT mentionable and grant the bot "
                          "MENTION_EVERYONE in the news channel only. Then the bot can ping "
                          "it and no member can, anywhere.")
                elif has_mention_everyone:
                    d.add("ping role", True,
                          f"@{role.get('name')} is non-mentionable and the bot holds "
                          f"MENTION_EVERYONE here — this is the recommended setup")
                else:
                    d.add("ping role", False,
                          f"@{role.get('name')} is non-mentionable and the bot lacks "
                          f"MENTION_EVERYONE, so instant-alert pings will silently not notify",
                          "Either allow MENTION_EVERYONE for the bot in this channel, or "
                          "make the role mentionable (worse: then members can ping it too).")
        else:
            d.add("ping role", True,
                  "DISCORD_NEWS_ROLE_ID not set — instant alerts will post without pinging")

        # --- AutoMod -------------------------------------------------------
        if check_automod:
            status, rules = await _get(client, f"/guilds/{guild_id}/auto-moderation/rules")
            if status == 403:
                d.add("automod", False,
                      "cannot read AutoMod rules (403 — bot lacks MANAGE_GUILD)",
                      "Optional. Grant MANAGE_GUILD only if you want the bot to manage "
                      "AutoMod rules; otherwise configure them by hand in Server Settings "
                      "-> AutoMod and ignore this check.")
            elif status == 200 and isinstance(rules, list):
                enabled = [r for r in rules if r.get("enabled")]
                keyword_rules = [r for r in enabled if int(r.get("trigger_type", 0)) == 1]
                d.add("automod", len(enabled) > 0,
                      f"{len(enabled)} enabled rule(s), {len(keyword_rules)} keyword rule(s)",
                      "" if enabled else (
                          "No AutoMod rules are active. For a GTA 6 server this is the main "
                          "protection against members pasting leak links — see "
                          "research/discord-delivery.md section 11."
                      ))
            else:
                d.add("automod", False, f"unexpected response {status}")

    return d


async def send_test_message(*, token: str, channel_id: str, timeout: float = 20.0) -> tuple[bool, str]:
    """
    Post one harmless message to prove the whole path works.

    Deliberately carries the same allowed_mentions block as every real payload,
    so this also proves the @everyone guard is in place.
    """
    payload = {
        "embeds": [{
            "title": "gta6-news-bot connection test",
            "description": (
                "If you can read this, the bot can post here.\n"
                "-# This is a one-off test. Delete it freely."
            ),
            "color": 0x2ECC71,
        }],
        "allowed_mentions": {"parse": [], "roles": [], "users": [], "replied_user": False},
    }
    async with httpx.AsyncClient(timeout=timeout, headers=_headers(token)) as client:
        resp = await client.post(f"{API_BASE}/channels/{channel_id}/messages", json=payload)
        if 200 <= resp.status_code < 300:
            try:
                return True, f"posted, message id {resp.json().get('id')}"
            except Exception:
                return True, "posted"
        if resp.status_code == 403:
            return False, ("403 Forbidden — the bot is in the server but lacks "
                           "SEND_MESSAGES or EMBED_LINKS in this channel. Run "
                           "`discord-doctor` to see which.")
        if resp.status_code == 401:
            return False, "401 Unauthorized — the token is invalid."
        return False, f"HTTP {resp.status_code}: {resp.text[:300]}"
