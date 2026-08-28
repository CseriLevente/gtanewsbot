"""
Orchestration: one invocation of the bot.

Called every ~15 minutes by Windows Task Scheduler. Each run:

  1. polls every enabled feed and ingests new items
  2. sends INSTANT alerts for first-party items (tier 1, instant feeds only)
  3. sends BREAKOUT alerts when many outlets converge on one story
  4. posts the daily digest if it is due and has not been posted today
  5. republishes the public web edition, once the digest has gone out

THE INTERLOCK
-------------
An item sent as an instant alert is moved to state `sent_instant`. The digest
selects only items in state `new`, so an instantly-alerted story can never be
repeated in that evening's digest. The interlock is a consequence of the state
machine rather than a separate check, which is why it cannot drift out of sync.

A BREAKOUT ALERT IS THE EXCEPTION, ON PURPOSE
---------------------------------------------
It does not mark its cluster, so the story still appears in the evening digest.
The interlock's logic does not transfer: a first-party announcement is a single
event, already pinged, and repeating it that evening adds nothing -- whereas a
breakout is by construction the day's biggest story, and a digest missing it
looks broken to anyone who muted alerts or joined after it fired. The digest is
the day's record; the alert is a notification about it. Re-alerting is prevented
by the channel (title guard, cooldown, daily cap) rather than by local state,
which also survives the write-persistence problem on the Windows host.

CATCH-UP SEMANTICS
------------------
If the PC was off for three days, ONE digest is posted, not three. Items are
selected by unsent flag rather than by a time window, so the backlog flows
naturally into today's digest instead of being replayed as three stale ones.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field

from src import (canonical, cluster, credibility, digest, discord_client, feeds,
                 llm, selfupdate, storage)
from src.clock import local_date_key, local_now, should_post_digest

logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name) or default)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    v = _env(name).casefold()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def effective_dry_run(requested: bool) -> tuple[bool, str | None]:
    """
    The single source of truth for "will this actually post?".

    Every command that can send a message MUST route through this. It exists
    because `cmd_digest` previously passed its --dry-run flag straight through
    and never consulted POSTING_ENABLED — so `digest --force` posted a real,
    unreviewed digest to a live community server while the operator believed
    posting was disabled. Two callers, two different answers, is the bug; one
    helper is the fix.

    Returns (dry_run, note) where note explains an override.
    """
    if requested:
        return True, None
    if not _env_bool("POSTING_ENABLED", False):
        return True, (
            "POSTING_ENABLED is false — forcing dry-run mode. Set it to true in "
            ".env when you are ready to post for real."
        )
    return False, None


@dataclass
class RunReport:
    revision: str = ""
    updated: bool = False
    update_detail: str = ""
    poll: feeds.PollSummary | None = None
    instant_sent: int = 0
    instant_details: list[str] = field(default_factory=list)
    breakout_sent: int = 0
    breakout_details: list[str] = field(default_factory=list)
    digest_posted: bool = False
    digest_reason: str = ""
    digest_items: int = 0
    digest_message_id: str | None = None
    web_published: bool = False
    web_reason: str = ""
    errors: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        out: list[str] = []
        if self.revision:
            out.append(f"Version: {self.revision}")
        if self.update_detail:
            out.append(f"Self-update: {self.update_detail}")
        if self.poll:
            out.append(f"Feeds: {self.poll.health_line()}")
            out.append(f"New items ingested: {self.poll.new_items}")
            for r in self.poll.results:
                out.append(f"  - {r.short}")
        out.append(f"Instant alerts sent: {self.instant_sent}")
        for d in self.instant_details:
            out.append(f"  - {d}")
        out.append(f"Breakout alerts sent: {self.breakout_sent}")
        for d in self.breakout_details:
            out.append(f"  - {d}")
        if self.digest_posted:
            out.append(f"Digest: POSTED with {self.digest_items} item(s) "
                       f"(message {self.digest_message_id or 'n/a'})")
        else:
            out.append(f"Digest: not posted — {self.digest_reason}")
        if self.web_reason:
            state = "PUBLISHED" if self.web_published else "not published"
            out.append(f"Web edition: {state} — {self.web_reason}")
        for e in self.errors:
            out.append(f"ERROR: {e}")
        return out


async def sync_feeds_from_config(conn, cfg: dict) -> int:
    """Register configured feeds, preserving learned runtime state."""
    count = 0
    for f in cfg.get("feeds", []):
        await storage.upsert_feed(
            conn,
            key=f["key"],
            url=f["url"],
            tier=int(f.get("tier", 4)),
            instant=bool(f.get("instant", False)),
            poll_seconds=int(f.get("poll_seconds", 1800)),
            enabled=bool(f.get("enabled", True)),
        )
        count += 1
    return count


async def send_instant_alerts(
    conn, cfg: dict, *, dry_run: bool, health_line: str, limit: int = 5
) -> tuple[int, list[str]]:
    """
    Send instant alerts for first-party news only.

    Restricted to tier 1 from feeds flagged `instant`, because that is the only
    tier where a push notification is justified and the volume is naturally low.
    Rumours are never instant-alerted regardless of tier.
    """
    token = _env("DISCORD_BOT_TOKEN")
    channel = _env("DISCORD_NEWS_CHANNEL_ID")
    role = _env("DISCORD_NEWS_ROLE_ID") or None

    instant_keys = {f["key"] for f in cfg.get("feeds", [])
                    if f.get("instant") and f.get("enabled", True)}
    if not instant_keys:
        return 0, []

    candidates = await storage.get_unsent_items(conn, states=(storage.STATE_NEW,), limit=50)
    picked = [
        r for r in candidates
        if r["feed_key"] in instant_keys and int(r["tier"]) == 1 and not r["is_rumour"]
    ][:limit]

    sent = 0
    details: list[str] = []
    for row in picked:
        entry = digest.entry_from_row(row, label_override=credibility.LABEL_OFFICIAL)

        # Ask the channel before announcing. `items.state` is the local record
        # that an alert was sent, and on this machine commits from the scheduled
        # process do not reach the shared database — so without this the same
        # story would be announced, and the role re-pinged, on every 15-minute
        # run. Repeated 03:00 pings is the worst thing this bot could do.
        if not dry_run:
            seen, seen_detail = await discord_client.title_already_in_channel(
                token=token, channel_id=channel, title=entry.title,
            )
            if seen is True:
                logger.warning("skipping instant alert, %s: %s", seen_detail, entry.title[:60])
                await storage.mark_items_state(
                    conn, [entry.item_id], storage.STATE_SENT_INSTANT,
                    "already in channel",
                )
                details.append(f"already announced: {entry.title[:60]}")
                continue
            if seen is None:
                logger.warning("duplicate-alert guard inconclusive: %s", seen_detail)

        payload = digest.render_instant_alert(entry, role_id=role, health_line=None)
        try:
            result = await discord_client.post_message(
                conn, token=token, channel_id=channel, payload=payload,
                dry_run=dry_run, kind="instant", item_id=entry.item_id,
            )
        except discord_client.DiscordFatalError as exc:
            details.append(f"FATAL: {exc}")
            break

        if result.sent:
            # ONLY a real send consumes the item. A dry run must never mutate
            # state: it would mark a tier-1 story as already-alerted while
            # notifying nobody, and the alert could then never fire. Because
            # POSTING_ENABLED=false forces dry-run mode, the earlier version of
            # this branch silently ate every instant candidate before the
            # operator had even switched posting on.
            await storage.mark_items_state(
                conn, [entry.item_id], storage.STATE_SENT_INSTANT, "instant alert",
            )
            sent += 1
            details.append(entry.title[:80])
        elif result.dry_run:
            details.append(f"[dry-run, still queued] {entry.title[:70]}")
        else:
            details.append(f"not sent: {result.detail} — {entry.title[:60]}")
    return sent, details


# Headlines we will not put behind a role ping. The digest and the website still
# carry them -- this is not editorial censorship, it is that a push notification
# to a whole community is the one place a crude headline cannot be scrolled
# past. Kept deliberately tiny and literal; a broad filter would silently eat
# real stories, which is a worse failure than an occasional blunt headline.
_CRUDE_RE = re.compile(
    r"\b(dong|penis|genital\w*|nude|nudity|nudist|boobs?|titt(?:y|ies)|"
    r"sex\s?scene|porn\w*)\b",
    re.IGNORECASE,
)


# Reasons a digest legitimately did not post. Anything else is a failure and
# must make the run exit non-zero, so Task Scheduler's Last Run Result and
# systemd's unit state both show it. Matched as prefixes against the strings
# maybe_post_digest and clock.should_post_digest return; keep them in sync.
_BENIGN_DIGEST = (
    "local hour ",                 # before DIGEST_HOUR
    "digest for ",                 # already posted today
    "only ",                       # below DIGEST_MIN_ITEMS
    "another run already claimed ",
    "dry-run preview only",
)


async def send_breakout_alerts(
    conn, cfg: dict, *, dry_run: bool, health_line: str
) -> tuple[int, list[str]]:
    """
    Alert on a story that many outlets ran at once, within the hour.

    The instant-alert path covers first-party news, but that is only two live
    feeds -- so the biggest story of 27 Aug 2026, Rockstar's own statement on
    the leaks carried by 26 outlets, was not announced until the 18:00 digest,
    up to a day late. This closes that gap: corroboration is the warrant, on the
    reasoning that when this many independent outlets carry the same GTA 6 story
    within hours, something actually happened.

    Four guards, because this path can ping a whole community:

      * a real publisher URL is REQUIRED. Most items arrive via Google News,
        whose links land on a consent wall -- fine to omit on a web page, not
        fine to push to someone's phone. Measured on the live corpus: every
        cluster at 8+ outlets contains a direct URL, so this costs almost
        nothing at the sizes that matter;
      * the channel is the rate limiter (daily cap and cooldown), not a local
        counter, because scheduled writes do not reliably persist on this
        machine and a per-run cap would still allow four pings an hour;
      * if the rate limit cannot be verified, we DECLINE. An unbounded ping is
        worse than a late one;
      * crude headlines are never pinged.

    Returns (sent, details).
    """
    min_outlets = _env_int("BREAKOUT_MIN_OUTLETS", 6)
    if min_outlets <= 0:
        return 0, ["disabled (BREAKOUT_MIN_OUTLETS=0)"]

    window_h = _env_int("BREAKOUT_WINDOW_HOURS", 24)
    max_per_day = _env_int("BREAKOUT_MAX_PER_DAY", 3)
    cooldown_min = _env_int("BREAKOUT_COOLDOWN_MINUTES", 60)

    token = _env("DISCORD_BOT_TOKEN")
    channel = _env("DISCORD_NEWS_CHANNEL_ID")
    role = _env("DISCORD_NEWS_ROLE_ID") or None

    rows = await storage.get_unsent_items(
        conn, states=(storage.STATE_NEW, storage.STATE_HELD), limit=300)
    if not rows:
        return 0, []

    items = [cluster.row_to_dict(r) for r in rows]
    cutoff = time.time() - window_h * 3600

    candidates = []
    for c in cluster.cluster_items(items):
        n = len(c.outlets)
        if n < min_outlets:
            continue
        # Freshness is judged on the NEWEST member: a story still attracting
        # coverage is live, even if the first report predates the window.
        newest = max((m.get("published_epoch") or 0) for m in c.members)
        if newest < cutoff:
            continue
        candidates.append((n, newest, c))

    if not candidates:
        return 0, []
    candidates.sort(key=lambda t: (-t[0], -t[1]))

    details: list[str] = []

    # --- rate limit, asked of the channel ---------------------------------
    if not dry_run:
        today, d1 = await discord_client.count_recent_marked_alerts(
            token=token, channel_id=channel, marker=digest.BREAKOUT_MARKER,
            within_seconds=24 * 3600,
        )
        if today is None:
            logger.warning("declining breakout alerts, rate limit unverifiable: %s", d1)
            return 0, [f"declined: rate limit unverifiable ({d1})"]
        if today >= max_per_day:
            return 0, [f"daily cap reached ({today}/{max_per_day})"]

        recent, d2 = await discord_client.count_recent_marked_alerts(
            token=token, channel_id=channel, marker=digest.BREAKOUT_MARKER,
            within_seconds=max(0, cooldown_min) * 60,
        )
        if recent is None:
            logger.warning("declining breakout alerts, cooldown unverifiable: %s", d2)
            return 0, [f"declined: cooldown unverifiable ({d2})"]
        if recent > 0:
            return 0, [f"in cooldown ({d2})"]

    sent = 0
    for n, _newest, c in candidates:
        # A direct publisher URL, or nothing. Cluster.representative already
        # prefers non-wrappers, but a cluster can be entirely wrapped.
        direct = [m for m in c.members
                  if not canonical.is_wrapper(m.get("url_canonical") or "")]
        if not direct:
            details.append(f"skipped, no publisher URL ({n} outlets): "
                           f"{(c.representative.get('title') or '')[:50]}")
            continue

        # NEWEST wins here, unlike cluster.representative, which prefers the
        # outlet that published first in order to credit whoever broke the
        # story. That is right for attribution and wrong for an alert: the
        # freshness gate above is computed on the cluster's newest member, so
        # pairing it with an oldest-first link let a cluster qualify on a
        # one-hour-old report and then ping the role about a day-and-a-half-old
        # article headed "Breaking".
        best = min(direct, key=lambda m: (
            int(m.get("tier") or 9),
            -(m.get("published_epoch") or 0),
            -len(m.get("title") or ""),
        ))
        # And the LINKED item must itself be inside the window. Testing only
        # the cluster leaves the same mismatch one step removed.
        if (best.get("published_epoch") or 0) < cutoff:
            details.append(f"skipped, freshest direct link is stale ({n} outlets): "
                           f"{(best.get('title') or '')[:45]}")
            continue
        title = best.get("title") or ""
        if _CRUDE_RE.search(title):
            logger.info("not pinging a crude headline: %s", title[:70])
            details.append(f"not pinged (headline): {title[:50]}")
            continue

        entry = digest.entry_from_row(best)
        entry.other_outlets = [o for o in c.outlets
                               if o != (best.get("source_name") or "")]
        entry.member_ids = [int(m["id"]) for m in c.members]

        if not dry_run:
            seen, seen_detail = await discord_client.title_already_in_channel(
                token=token, channel_id=channel, title=entry.title,
            )
            if seen is True:
                details.append(f"already announced: {entry.title[:50]}")
                continue
            if seen is None:
                logger.warning("breakout duplicate guard inconclusive: %s", seen_detail)
                details.append(f"declined: duplicate guard inconclusive ({seen_detail})")
                continue

        payload = digest.render_breakout_alert(
            entry, role_id=role, outlet_count=n, health_line=health_line)
        try:
            result = await discord_client.post_message(
                conn, token=token, channel_id=channel, payload=payload,
                dry_run=dry_run, kind="breakout", item_id=entry.item_id,
            )
        except discord_client.DiscordFatalError as exc:
            details.append(f"FATAL: {exc}")
            break

        if result.sent:
            # Deliberately does NOT mark the cluster sent, unlike an instant
            # alert. The state machine's interlock excludes sent items from the
            # evening digest, which is right for a one-off first-party
            # announcement and wrong here: a breakout is by definition the
            # biggest story of the day, and a digest missing it reads as broken
            # to anyone who muted alerts or joined later. The digest is the
            # day's record, so the story stays in the pool and appears there.
            #
            # Re-alerting is prevented by the channel instead: the title guard
            # above (which must answer conclusively or we decline), the
            # cooldown, the daily cap, and the freshness window. The exposure
            # is only from this alert until the next digest consumes the item.
            sent += 1
            details.append(f"{n} outlets: {entry.title[:70]}")
        elif result.dry_run:
            details.append(f"[dry-run, still queued] {n} outlets: {entry.title[:60]}")
        else:
            details.append(f"not sent: {result.detail} — {entry.title[:50]}")

        # One per run, always. The cooldown makes this the real cap, but even
        # without it a single alert per cycle bounds the blast radius.
        break

    return sent, details


def build_digest_entries(rows, cfg: dict) -> tuple[list[digest.DigestEntry], list[int]]:
    """
    Turn raw item rows into one entry per STORY.

    Returns (entries, promoted_item_ids).

    For each cluster the best usable member is chosen as the representative. A
    HELD member can become usable here: clustering supplies the
    `tier2_corroborations` count that `credibility.judge()` always received as 0
    before, so a tier-3 story carried by a tier-2 outlet is now promoted instead
    of being held indefinitely.

    Corroboration deliberately EXCLUDES the candidate's own domain, so an outlet
    cannot corroborate itself.
    """
    dicts = [cluster.row_to_dict(r) for r in rows]
    clusters = cluster.cluster_items(dicts)

    entries: list[digest.DigestEntry] = []
    promoted: list[int] = []

    for c in clusters:
        # Try members in the representative's preference order.
        ordered = sorted(
            c.members,
            key=lambda m: (
                int(m.get("tier") or 9),
                1 if canonical.is_wrapper(m.get("url_canonical") or "") else 0,
                m.get("published_epoch") or float("inf"),
                -len(m.get("title") or ""),
            ),
        )
        chosen = None
        label = None
        for m in ordered:
            if m.get("state") == storage.STATE_NEW:
                chosen = m
                break
            if m.get("state") == storage.STATE_HELD:
                corr = c.tier2_corroborations(exclude_domain=m.get("source_domain"))
                verdict = credibility.judge(
                    title=m.get("title") or "",
                    summary=m.get("summary_raw") or "",
                    domain=m.get("source_domain") or "",
                    url=m.get("url_canonical") or "",
                    feed_tier=int(m.get("tier") or 4),
                    cfg=cfg,
                    tier2_corroborations=corr,
                )
                if verdict.postable:
                    chosen = m
                    label = verdict.label
                    promoted.append(int(m["id"]))
                    break
        if chosen is None:
            continue

        rep_domain = (chosen.get("source_domain") or "").casefold()
        others = [
            o for o in c.outlets
            if o != (chosen.get("source_name") or chosen.get("source_domain"))
        ]
        entry = digest.DigestEntry(
            item_id=int(chosen["id"]),
            title=chosen.get("title") or "",
            url=chosen.get("url_canonical") or "",
            source_name=chosen.get("source_name") or chosen.get("source_domain") or "unknown",
            label=label or _label_for(chosen),
            other_outlets=others,
            # Every member is marked sent, not just the linked one — otherwise
            # the unused copies resurface tomorrow as separate "new" stories.
            member_ids=[int(m["id"]) for m in c.members],
        )
        entries.append(entry)

    return entries, promoted


def _llm_digest_entries(rows, cfg: dict, *, max_items: int) -> list[digest.DigestEntry] | None:
    """
    Build digest entries from LLM curation. Returns None to fall back.

    The URL is looked up HERE, from the DB row, keyed on the item_id the model
    echoed. The model is never asked for a link, so it cannot invent one.
    """
    dicts = [cluster.row_to_dict(r) for r in rows]
    by_id = {int(d["id"]): d for d in dicts}
    outcome = llm.curate(dicts, max_stories=max_items)
    if outcome is None or not outcome.stories:
        return None

    entries: list[digest.DigestEntry] = []
    for story in outcome.stories:
        lead = by_id.get(int(story.lead_item_id))
        if lead is None:
            continue
        members = [by_id[i] for i in (int(x) for x in story.item_ids) if i in by_id]
        # Attribution and destination must agree, so both come from the lead row.
        others: list[str] = []
        lead_name = lead.get("source_name") or lead.get("source_domain") or "unknown"
        for m in members:
            name = m.get("source_name") or m.get("source_domain")
            if name and name != lead_name and name not in others:
                others.append(name)
        entries.append(digest.DigestEntry(
            item_id=int(lead["id"]),
            title=story.headline.strip() or (lead.get("title") or ""),
            url=lead.get("url_canonical") or "",
            source_name=lead_name,
            label=llm.label_to_display(story.label, story.is_leak_derived),
            summary=(story.summary or "").strip()[:llm.MAX_SUMMARY_CHARS] or None,
            other_outlets=others,
            member_ids=[int(m["id"]) for m in members],
        ))
    if not entries:
        return None
    logger.info("digest built by LLM curation: %d stories (~$%.4f)",
                len(entries), outcome.cost_usd)
    return entries


def _label_for(item: dict) -> str:
    if item.get("is_rumour"):
        return credibility.LABEL_RUMOUR
    if int(item.get("tier") or 9) == 1:
        return credibility.LABEL_OFFICIAL
    return credibility.LABEL_REPORT


async def maybe_post_digest(
    conn, cfg: dict, *, dry_run: bool, force: bool, health_line: str
) -> tuple[bool, str, int, str | None]:
    """Post the daily digest if due. Returns (posted, reason, item_count, message_id)."""
    digest_hour = _env_int("DIGEST_HOUR", 18)
    max_items = _env_int("DIGEST_MAX_ITEMS", 8)
    # Default 0, deliberately: the EMPTY digest is the heartbeat. With a minimum
    # of 1, the one case that matters most — every feed broken, so zero items —
    # is exactly the case where nothing posts, and channel silence becomes
    # ambiguous between a quiet news day and total collapse. render_digest has a
    # whole empty-state branch that a minimum of 1 makes unreachable.
    min_items = _env_int("DIGEST_MIN_ITEMS", 0)

    # Age out stale candidates BEFORE selecting, so a three-week-old
    # unconfirmed rumour can never appear under today's date.
    held_ttl = _env_int("HELD_TTL_DAYS", 4)
    new_ttl = _env_int("UNSENT_TTL_DAYS", 5)
    expired_held = await storage.expire_held_items(conn, older_than_days=held_ttl)
    expired_new = await storage.expire_stale_new_items(conn, older_than_days=new_ttl)
    if expired_held or expired_new:
        logger.info(
            "expired %d held (>%dd) and %d unsent (>%dd) item(s) before building the digest",
            expired_held, held_ttl, expired_new, new_ttl,
        )

    date_key = local_date_key()
    already = await storage.digest_already_posted(conn, date_key)

    # AUTHORITATIVE DUPLICATE CHECK.
    #
    # The local row is necessary but not sufficient. On this operator's machine
    # commits from the Task Scheduler process were visible to that process yet
    # never reached the shared database, so `digest_runs` stayed empty while the
    # digest posted correctly two days running — the guard was inert and only
    # luck prevented a repeat every 15 minutes. A guard whose evidence lives in
    # the same place as the failure is not a guard.
    #
    # Discord is the authority on what is in the channel. If it says today's
    # digest is already there, believe it over the local DB.
    if not dry_run and not already:
        in_channel, detail = await discord_client.digest_already_in_channel(
            token=_env("DISCORD_BOT_TOKEN"),
            channel_id=_env("DISCORD_NEWS_CHANNEL_ID"),
            date_label=date_key,
        )
        if in_channel is True:
            logger.warning("channel check overrode the local state: %s", detail)
            # Repair the local record so `status` stops lying to the operator.
            await storage.record_digest_run(
                conn, date_key=date_key, item_count=0,
                discord_message_id="recovered-from-channel", dry_run=False,
            )
            already = True
        elif in_channel is None:
            logger.warning("duplicate-digest guard inconclusive: %s", detail)

    if force:
        due, reason = True, "forced"
        if already:
            reason = "forced (a digest for today already exists; this will not be recorded twice)"
    else:
        due, reason = should_post_digest(
            digest_hour=digest_hour, already_posted=already, now=local_now()
        )
    if not due:
        return False, reason, 0, None

    # HELD items are included as candidates: a held tier-3/4 item may be
    # promoted by corroboration once clustering reveals how many independent
    # tier-2 outlets carried the same story.
    rows = await storage.get_unsent_items(
        conn, states=(storage.STATE_NEW, storage.STATE_HELD), limit=300
    )
    # LLM curation when available, heuristic clustering otherwise. The LLM path
    # exists mainly to merge same-story groups that lexical overlap provably
    # cannot (see src/llm.py), and it returns None on any failure so the digest
    # still posts.
    entries, promoted_ids = None, []
    if _env_bool("LLM_CURATION_ENABLED", False):
        entries = _llm_digest_entries(rows, cfg, max_items=max_items)
    if entries is None:
        entries, promoted_ids = build_digest_entries(rows, cfg)
    if promoted_ids:
        await storage.mark_items_state(
            conn, promoted_ids, storage.STATE_NEW, "promoted by cluster corroboration"
        )

    if len(entries) < min_items and not force:
        return False, f"only {len(entries)} item(s), below DIGEST_MIN_ITEMS={min_items}", 0, None

    payload = digest.render_digest(
        entries,
        health_line=health_line,
        date_label=date_key,
        max_items=max_items,
    )
    # Exactly the entries the payload contains — derived from the same function
    # the renderer uses, so the marking list cannot drift from what was shown.
    rendered, _omitted = digest.select_entries(
        entries, health_line=health_line, date_label=date_key, max_items=max_items
    )

    # CLAIM THE DAY BEFORE POSTING. Claiming afterwards leaves a window in which
    # two overlapping runs (the task fires every 15 minutes) both pass the
    # already-posted check, both post, and only then race on the INSERT — the
    # community sees the digest twice. record_digest_run is a compare-and-set on
    # the UNIQUE date key, so claiming first makes the second run bail out.
    if not dry_run:
        claimed = await storage.record_digest_run(
            conn, date_key=date_key, item_count=len(rendered),
            discord_message_id=None, dry_run=False,
        )
        if not claimed and not force:
            return False, f"another run already claimed {date_key}", 0, None

    try:
        result = await discord_client.post_message(
            conn,
            token=_env("DISCORD_BOT_TOKEN"),
            channel_id=_env("DISCORD_NEWS_CHANNEL_ID"),
            payload=payload,
            dry_run=dry_run,
            kind="digest",
        )
    except discord_client.DiscordFatalError as exc:
        # Release even here. A fatal error latches the kill switch, so nothing
        # will retry until an operator clears it -- but if they clear it the
        # same evening, the digest must still be postable. Holding the claim
        # would silently make today unrecoverable.
        if not dry_run:
            await storage.release_digest_claim(conn, date_key)
        return False, f"fatal: {exc}", 0, None

    if not (result.sent or result.dry_run):
        # The claim was taken before posting, so a failed post MUST release it
        # or today's digest can never be retried -- one rate-limit or one HTTP
        # 400 would silently cost the whole day.
        #
        # This release used to live in an `elif not dry_run:` arm below, which
        # was unreachable: reaching it required result.dry_run to be True, and
        # that only happens when the dry_run parameter was True, so `not
        # dry_run` was always False. The claim leaked on every real failure.
        if not dry_run:
            await storage.release_digest_claim(conn, date_key)
        return False, result.detail, 0, None

    if result.sent:
        await storage.attach_digest_message(
            conn, date_key=date_key, discord_message_id=result.message_id,
            item_count=len(rendered),
        )
        # Mark every clustered member of a RENDERED entry — not entries[:max],
        # which would bury stories the budget pushed out. Members beyond the
        # representative are marked too, otherwise the other outlets' copies of
        # a story we just published return tomorrow looking like fresh news.
        sent_ids: list[int] = []
        for e in rendered:
            sent_ids.extend(e.member_ids or [e.item_id])
        await storage.mark_items_state(
            conn, sorted(set(sent_ids)), storage.STATE_SENT_DIGEST, f"digest {date_key}",
        )
    return (result.sent, "posted" if result.sent else "dry-run preview only",
            len(rendered), result.message_id)


async def run_once(conn, cfg: dict, *, dry_run: bool = False, force_digest: bool = False,
                   skip_poll: bool = False) -> RunReport:
    """One full cycle. This is the Task Scheduler entry point."""
    report = RunReport()

    # Log the resolved database path and identity on every run. An operator
    # comparing a scheduled run against a hand-run needs to know they touched
    # the same state; two processes silently using two different DB files looks
    # exactly like writes vanishing.
    from src import paths as _paths
    logger.info("run | db=%s | user=%s | localappdata=%s | cwd=%s",
                _paths.db_path(),
                os.environ.get("USERNAME", "?"),
                os.environ.get("LOCALAPPDATA", "?"),
                os.getcwd())

    # Track the repo before anything else, so a deployment picks up fixes
    # without anyone logging into it. The pulled code runs on the NEXT cycle,
    # never this one -- re-execing into freshly pulled code unattended is how
    # you get a crash loop nobody is watching.
    #
    # Failures here are recorded and then ignored: being unable to update must
    # never stop the bot doing the job it can already do with the code it has.
    try:
        report.updated, report.update_detail = selfupdate.check_and_update()
        report.revision = selfupdate.current_revision()
    except Exception as exc:               # noqa: BLE001 - never fatal
        logger.exception("self-update stage failed")
        report.update_detail = f"error: {exc}"

    # NOTE: an in-process write-persistence canary was tried here and is
    # useless for this failure — the scheduled process reads back its own
    # writes perfectly, so the canary always passes even when nothing reaches
    # the shared file. `storage.verify_write_persistence()` is kept for
    # `check-ready`, where an operator runs it interactively, but the real
    # duplicate protection is the channel-side check in maybe_post_digest.

    if not skip_poll:
        report.poll = await feeds.poll_all(conn, cfg, contact_url=_env("BOT_CONTACT_URL") or None)
        health = report.poll.health_line()
    else:
        health = "poll skipped"

    effective, note = effective_dry_run(dry_run)
    if note:
        report.errors.append(note)

    try:
        report.instant_sent, report.instant_details = await send_instant_alerts(
            conn, cfg, dry_run=effective, health_line=health
        )
    except Exception as exc:
        logger.exception("instant alert stage failed")
        report.errors.append(f"instant alerts: {exc}")

    # Breakout alerts run after first-party and before the digest. After,
    # because a first-party source outranks corroboration and should not be
    # pre-empted by coverage of itself; before, because a story announced now is
    # marked sent and must not also appear in tonight's digest.
    try:
        report.breakout_sent, report.breakout_details = await send_breakout_alerts(
            conn, cfg, dry_run=effective, health_line=health
        )
    except Exception as exc:
        logger.exception("breakout alert stage failed")
        report.errors.append(f"breakout alerts: {exc}")

    try:
        posted, reason, count, mid = await maybe_post_digest(
            conn, cfg, dry_run=effective, force=force_digest, health_line=health
        )
        report.digest_posted = posted
        report.digest_reason = reason
        report.digest_items = count
        report.digest_message_id = mid
        # A returned failure used to land only in digest_reason, and main.py
        # exits non-zero only when report.errors is non-empty -- so "rate
        # limited", "HTTP 400 rejected the message" and "kill switch engaged"
        # all exited 0, the same code as the benign "not 18:00 yet". Task
        # Scheduler's Last Run Result therefore read 0 on a day nothing was
        # posted, which is precisely the signal an operator relies on.
        if not posted and not effective and not reason.startswith(_BENIGN_DIGEST):
            report.errors.append(f"digest not posted: {reason}")
    except Exception as exc:
        logger.exception("digest stage failed")
        report.errors.append(f"digest: {exc}")
        report.digest_reason = f"error: {exc}"


    # Refresh the public web edition, but only once the digest has actually gone
    # out. Deliberately tied to the digest rather than to every 15-minute cycle:
    # the page's own "compiled <time>" line is a once-a-day statement, and a
    # deploy that force-pushes a branch 96 times a day is pure noise in the repo
    # and in any CDN cache in front of it.
    #
    # Wrapped so publishing can never fail the run. The digest is the product;
    # the website is a convenience. A deploy that dies because the network
    # dropped must not turn a successful post into a failed run -- and must not
    # be silent either, hence web_reason in the report.
    if report.digest_posted and not effective:
        try:
            report.web_published, report.web_reason = await _publish_web_edition()
            if not report.web_published:
                report.errors.append(f"web publish: {report.web_reason}")
            else:
                broken = _linked_host_failed(report.web_reason)
                if broken:
                    # Something is live, so the run is not a write-off -- but
                    # the digest links the host that failed, so every message
                    # from here on points at a page that stopped updating.
                    report.errors.append(
                        f"web publish: {broken} is the host DIGEST_WEB_URL "
                        f"points at, and it failed ({report.web_reason})")
        except Exception as exc:
            logger.exception("web publish stage failed")
            report.web_reason = f"error: {exc}"
            report.errors.append(f"web publish: {exc}")

    await _escalate_operator_alerts(conn, report)

    # Write the whole report to the LOG, not just the console.
    #
    # Task Scheduler runs this under pythonw.exe, which has no console at all —
    # so everything cmd_run prints goes nowhere. Without this, the bot can stop
    # posting for a week and logs/bot.log is byte-identical to a week of healthy
    # runs. This is the root of every other visibility gap.
    for line in report.summary_lines():
        logger.info("run | %s", line)

    return report



def _linked_host_failed(reason: str) -> str | None:
    """
    Did the host the digest actually LINKS to fail to publish?

    A broken standby is a warning; a broken linked host means every digest from
    now on points members at a page that has stopped updating, which is the one
    web-publish failure worth failing the run over.
    """
    url = (os.environ.get("DIGEST_WEB_URL") or "").lower()
    if not url:
        return None
    linked = ("cloudflare" if "pages.dev" in url
              else "github" if "github.io" in url else None)
    if not linked:
        return None
    return linked if f"{linked}=FAIL" in reason else None


# Generous, because the inner steps are sequential and each has its own limit
# (GitHub 180s + Cloudflare 300s in tools/publish_web.py). An outer timeout
# below their sum would kill a healthy-but-slow deploy and report a timeout
# that never really happened.
async def _publish_web_edition(timeout_s: int = 600) -> tuple[bool, str]:
    """
    Rebuild and publish the public web edition.

    Runs `build-web --deploy` as a subprocess rather than importing it. That
    reuses the exact code path an operator runs by hand -- so the scheduled
    publish cannot drift from the manual one -- and it contains a hanging or
    crashing deploy tool inside its own process with its own timeout.

    Returns (published, reason). Never raises for an ordinary failure; the
    caller records the reason and the run continues.
    """
    if not (os.environ.get("WEB_DEPLOY_CMD") or "").strip():
        return False, "WEB_DEPLOY_CMD is not set"

    import subprocess
    from src import paths as _paths

    def _run() -> tuple[bool, str]:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "src.main", "build-web", "--deploy"],
                cwd=_paths.PROJECT_ROOT, capture_output=True, text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return False, f"deploy timed out after {timeout_s}s"
        out = ((r.stdout or "") + (r.stderr or "")).strip()

        # Parse the per-host RESULT line rather than the tail.
        #
        # This used to keep out.splitlines()[-1], but cmd_build_web prints two
        # fixed reminder lines AFTER the deploy output -- so the "status" was
        # always the literal sentence "Only set it once you have opened that url
        # in a logged-out browser.", recorded as web_reason and logged as
        # "web publish ok" every single day no matter what happened. A publish
        # that had been failing for months would have read as healthy.
        #
        # The line is searched for, not tailed, and is authoritative when
        # present. WEB_DEPLOY_CMD is operator-configurable, so an arbitrary
        # command that emits no RESULT line still falls back to the exit code.
        targets: dict[str, str] = {}
        for line in out.splitlines():
            if line.strip().startswith("RESULT "):
                for tok in line.split()[1:]:
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        targets[k.strip()] = v.strip()

        if targets:
            failed = sorted(k for k, v in targets.items() if v != "ok")
            summary = " ".join(f"{k}={v}" for k, v in sorted(targets.items()))
            if not failed:
                logger.info("web publish ok: %s", summary)
                return True, summary
            if len(failed) == len(targets):
                logger.error("web publish failed on every host: %s", out[-800:])
                return False, summary
            # Partial: the page is live somewhere, so the run stands -- but say
            # which host is broken, because a standby that quietly stopped
            # working is worth nothing on the day it is needed.
            logger.warning("web publish partial (%s failed): %s",
                           ", ".join(failed), out[-800:])
            return True, f"{summary} (partial)"

        tail = out.splitlines()[-1] if out else "no output"
        if r.returncode != 0:
            logger.warning("web publish failed (exit %s): %s", r.returncode, out[-800:])
            return False, f"exit {r.returncode}: {tail[:200]}"
        logger.info("web publish ok: %s", tail[:200])
        return True, tail[:200]

    # Keep the event loop responsive; the deploy is a blocking subprocess.
    return await asyncio.to_thread(_run)


async def _escalate_operator_alerts(conn, report: RunReport) -> None:
    """
    Turn silent degradation into something the operator can actually notice.

    Three conditions, all previously invisible under pythonw.exe:
      * the kill switch is engaged — the most consequential state the bot can be
        in, and it announced itself exactly once, when it latched;
      * a feed has failed FEED_FAILURE_ALERT_THRESHOLD times running — the
        config option existed but nothing ever read it;
      * a feed returns 200 with zero entries though it has had entries before,
        which means the endpoint changed shape rather than the news stopping.

    A dying feed is the likeliest real failure and the quietest: the digest
    keeps looking normal while coverage silently halves.
    """
    if await storage.kill_switch_engaged(conn):
        reason = await storage.get_flag(conn, "discord_kill_switch_reason", "unknown")
        msg = (f"KILL SWITCH ENGAGED — nothing is being posted. Reason: {reason}. "
               f"Clear with: python -m src.main clear-kill-switch")
        logger.error(msg)
        report.errors.append(msg)

    if not report.poll:
        return

    threshold = _env_int("FEED_FAILURE_ALERT_THRESHOLD", 3)
    for row in await storage.get_feeds(conn, enabled_only=True):
        fails = int(row["consecutive_failures"] or 0)
        if fails >= threshold:
            msg = (f"feed '{row['key']}' has failed {fails} times in a row "
                   f"(last status {row['last_status']}): {row['last_error'] or 'no detail'}")
            logger.error(msg)
            report.errors.append(msg)

    for r in report.poll.results:
        if r.suspected_dead:
            msg = (f"feed '{r.key}' returned HTTP 200 with 0 entries but has had entries "
                   f"before — the endpoint has probably changed shape (redirect to HTML, "
                   f"login wall, or CMS migration)")
            logger.error(msg)
            report.errors.append(msg)
