"""
gta6-news-bot — main entry point.

Commands:
    python -m src.main init-db              Create the database and register feeds
    python -m src.main poll                 Fetch all feeds and ingest new items
    python -m src.main run                  Full cycle (poll + alerts + digest if due)
    python -m src.main run --dry-run        Same, but print instead of posting
    python -m src.main digest --dry-run     Preview today's digest without posting
    python -m src.main digest --force       Build and post now, ignoring the hour
    python -m src.main status                Feed health, item counts, clock, digest runs
    python -m src.main check-ready            Verify configuration before going live
    python -m src.main list-sources           Show the configured source registry
    python -m src.main items --state new      List stored items
    python -m src.main clear-kill-switch      Re-enable posting after an auth failure

Windows Task Scheduler runs `run` every 15 minutes. All timing decisions live in
Python (see src/clock.py) so the schedule itself is dumb and hard to get wrong.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv

from src import paths

paths.ensure_dirs()

# This console is cp1250 and cannot encode the emoji used in Discord embeds, nor
# the '·' separator in the feed-health line. Without this, a log record carrying
# either one makes logging spew a UnicodeEncodeError traceback to stderr on every
# emit. errors="replace" degrades those characters instead of failing.
try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except (AttributeError, OSError):  # pragma: no cover - non-standard stdout
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(paths.LOGS_DIR, "bot.log"), encoding="utf-8"),
    ],
)

from src.logging_setup import configure_logging  # noqa: E402

configure_logging()

from src import automod, credibility, digest, discord_client, discord_setup, feeds, runner, storage  # noqa: E402
from src.clock import check_local_clock, describe_now, local_date_key  # noqa: E402

# Every command in this module writes to the console, and some of that text
# carries emoji or typographic punctuation from the Discord payload. Shadowing
# print() deliberately, so no individual call site can forget.
from src.console import safe_print as print  # noqa: A001, E402

logger = logging.getLogger("gta6")


def _load_env() -> None:
    load_dotenv(os.path.join(paths.PROJECT_ROOT, ".env"))


async def _open() -> tuple:
    conn = await storage.connect()
    await storage.init_schema(conn)
    cfg = credibility.load_config()
    return conn, cfg


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init_db(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, cfg = await _open()
        try:
            n = await runner.sync_feeds_from_config(conn, cfg)
            print(f"Database ready: {paths.db_path()}")
            print(f"Registered {n} feed(s) from {paths.SOURCES_JSON}")
            ok, msg = check_local_clock()
            print(f"Clock: {describe_now()}")
            print(f"{'OK  ' if ok else 'WARN'} {msg}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_poll(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, cfg = await _open()
        try:
            await runner.sync_feeds_from_config(conn, cfg)
            summary = await feeds.poll_all(conn, cfg, contact_url=os.environ.get("BOT_CONTACT_URL"))
            print(summary.health_line())
            for r in summary.results:
                print(f"  {r.short}")
            print(f"\nNew items ingested: {summary.new_items}")
            held = sum(r.items_held for r in summary.results)
            dropped = sum(r.items_dropped for r in summary.results)
            print(f"Held for corroboration: {held}   Dropped (irrelevant/blocked): {dropped}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_run(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, cfg = await _open()
        try:
            await runner.sync_feeds_from_config(conn, cfg)
            report = await runner.run_once(
                conn, cfg, dry_run=args.dry_run, force_digest=args.force
            )
            for line in report.summary_lines():
                print(line)
            # Task Scheduler History and the Windows Event Log are the only
            # monitoring surfaces a home PC has, and both key off the exit code.
            # Previously `run` exited 0 for every explained failure, so a bot
            # that had stopped posting looked identical to a healthy one.
            if report.errors:
                sys.exit(1)
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_digest(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, cfg = await _open()
        try:
            await runner.sync_feeds_from_config(conn, cfg)
            health = "poll skipped (use `run` to poll first)"
            if not args.no_poll:
                summary = await feeds.poll_all(
                    conn, cfg, contact_url=os.environ.get("BOT_CONTACT_URL")
                )
                health = summary.health_line()
                print(f"[poll] {health}\n")

            # Must go through the shared helper: passing args.dry_run straight
            # through ignored POSTING_ENABLED, so `digest --force` could post a
            # real unreviewed digest to a live server with posting "disabled".
            effective, note = runner.effective_dry_run(args.dry_run)
            if note:
                print(f"NOTE: {note}")
            posted, reason, count, mid = await runner.maybe_post_digest(
                conn, cfg, dry_run=effective, force=args.force, health_line=health
            )
            if posted:
                print(f"\nDigest POSTED with {count} item(s). Message id: {mid}")
            else:
                print(f"\nDigest not posted — {reason}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_status(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, cfg = await _open()
        try:
            from src import selfupdate
            rev = selfupdate.current_revision()
            if rev:
                auto = (os.environ.get("AUTO_UPDATE") or "true").strip().casefold()
                on = auto not in ("0", "false", "no", "off")
                print(f"Version:  {rev} "
                      f"({'tracking ' + (os.environ.get('AUTO_UPDATE_BRANCH') or 'main')
                         if on else 'auto-update OFF'})")
            print(f"Clock:    {describe_now()}")
            ok, msg = check_local_clock()
            print(f"          {'OK' if ok else 'WARN'} — {msg}")
            print(f"Database: {paths.db_path()}")
            print(f"Config:   {paths.SOURCES_JSON}")
            print(f"Posting:  {'ENABLED' if os.environ.get('POSTING_ENABLED','').casefold() in ('1','true','yes') else 'disabled (dry-run)'}")
            if await storage.kill_switch_engaged(conn):
                reason = await storage.get_flag(conn, "discord_kill_switch_reason", "?")
                print(f"KILL SWITCH ENGAGED — {reason}")
                print("  Clear it with: python -m src.main clear-kill-switch")

            print("\n--- Feeds ---")
            rows = await storage.get_feeds(conn, enabled_only=False)
            if not rows:
                print("  none registered; run `init-db`")
            for r in rows:
                state = "on " if r["enabled"] else "OFF"
                last = r["last_status"] if r["last_status"] is not None else "-"
                fails = r["consecutive_failures"]
                flag = ""
                threshold = int(os.environ.get("FEED_FAILURE_ALERT_THRESHOLD", "3") or 3)
                if fails >= threshold:
                    flag = f"  <-- {fails} consecutive failures"
                print(f"  [{state}] t{r['tier']} {r['key']:<28} last={last:<5} "
                      f"delay={r['politeness_delay_s']}s{flag}")
                if r["last_error"]:
                    print(f"          last error: {r['last_error'][:120]}")

            print("\n--- Items by state ---")
            counts = await storage.count_items_by_state(conn)
            if not counts:
                print("  none")
            for state, c in sorted(counts.items()):
                print(f"  {state:<14} {c}")

            print("\n--- Recent digests ---")
            runs = await storage.get_recent_digest_runs(conn, limit=10)
            if not runs:
                print("  none yet")
            for r in runs:
                tag = " (dry-run)" if r["dry_run"] else ""
                print(f"  {r['date_key']}  {r['item_count']} items  "
                      f"msg={r['discord_message_id'] or '-'}{tag}")

            today = local_date_key()
            print(f"\nToday ({today}): "
                  f"{'already posted' if await storage.digest_already_posted(conn, today) else 'not yet posted'}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_check_ready(args: argparse.Namespace) -> None:
    problems: list[str] = []
    warnings: list[str] = []

    print("--- Environment ---")
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Clock:    {describe_now()}")
    ok, msg = check_local_clock()
    print(f"{'OK  ' if ok else 'WARN'} {msg}")
    if not ok:
        warnings.append(msg)

    if feeds.FEEDPARSER_AVAILABLE:
        print(f"OK   feedparser {feeds.FEEDPARSER_VERSION}")
    else:
        problems.append('feedparser not installed — run: pip install "feedparser==6.0.14"')

    from src import selfupdate as _su
    print("\n--- Updates ---")
    up_problems, up_notes = _su.preflight()
    for n in up_notes:
        print(f"OK   {n}")
    for p in up_problems:
        print(f"FAIL {p}")
    problems.extend(up_problems)

    db = paths.db_path()
    print(f"\n--- Database ---\npath: {db}")
    if paths.is_cloud_synced(db):
        problems.append(
            f"database path is inside a cloud-synced folder: {db}. OneDrive syncs the .db, "
            f"-wal and -shm files independently, which corrupts the database."
        )
    else:
        print("OK   not inside a cloud-synced folder")

    print(f"\n--- Config ---\n{paths.SOURCES_JSON}")
    try:
        cfg = credibility.load_config()
        enabled = [f for f in cfg["feeds"] if f.get("enabled", True)]
        print(f"OK   {len(cfg['feeds'])} feeds ({len(enabled)} enabled), "
              f"{len(cfg.get('domain_tiers', {}))} domain tiers")
        unverified = [f["key"] for f in enabled if f.get("verified") == "untested"]
        if unverified:
            warnings.append("feeds never verified live (test these): " + ", ".join(unverified))
    except Exception as exc:
        problems.append(f"cannot load config: {exc}")

    print("\n--- Discord ---")
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    channel = (os.environ.get("DISCORD_NEWS_CHANNEL_ID") or "").strip()
    role = (os.environ.get("DISCORD_NEWS_ROLE_ID") or "").strip()
    posting = (os.environ.get("POSTING_ENABLED") or "").casefold() in ("1", "true", "yes")
    print(f"token set:    {'yes' if token else 'NO'}")
    print(f"channel set:  {'yes' if channel else 'NO'}")
    print(f"ping role:    {role or '(none — instant alerts will not ping)'}")
    print(f"POSTING_ENABLED: {posting}")
    if posting and not token:
        problems.append("POSTING_ENABLED is true but DISCORD_BOT_TOKEN is empty")
    if posting and not channel:
        problems.append("POSTING_ENABLED is true but DISCORD_NEWS_CHANNEL_ID is empty")
    if not posting:
        print("     (dry-run mode: nothing will be posted)")

    print("\n--- Digest ---")
    hour = int(os.environ.get("DIGEST_HOUR", "18") or 18)
    print(f"DIGEST_HOUR = {hour}")
    if 2 <= hour <= 3:
        problems.append(
            f"DIGEST_HOUR={hour} falls in the 02:00-03:00 DST transition window. "
            f"That hour does not exist on the spring-forward day and occurs twice in "
            f"autumn, which breaks the once-per-local-day guarantee. Use 18."
        )
    else:
        print(f"OK   {hour:02d}:00 exists exactly once on every local day")

    print("\n" + "=" * 60)
    for w in warnings:
        print(f"WARN  {w}")
    if problems:
        for p in problems:
            print(f"FAIL  {p}")
        print(f"\n{len(problems)} problem(s) must be fixed.")
        sys.exit(1)
    print("Ready." if not warnings else f"Ready, with {len(warnings)} warning(s).")


def cmd_list_sources(args: argparse.Namespace) -> None:
    cfg = credibility.load_config()
    print("--- Feeds ---")
    for f in cfg["feeds"]:
        state = "on " if f.get("enabled", True) else "OFF"
        inst = "INSTANT" if f.get("instant") else "digest "
        print(f"[{state}] t{f['tier']} {inst} {f.get('verified','?'):<9} {f['key']}")
        print(f"        {f['url']}")
        if f.get("note"):
            print(f"        note: {f['note'][:150]}")
    print(f"\n--- Domain tiers ({len(cfg.get('domain_tiers', {}))}) ---")
    by_tier: dict[int, list[str]] = {}
    for dom, t in cfg.get("domain_tiers", {}).items():
        by_tier.setdefault(int(t), []).append(dom)
    for t in sorted(by_tier):
        print(f"  tier {t}: {', '.join(sorted(by_tier[t]))}")
    print(f"\nBlocked domains:  {len(cfg.get('blocked_domains', []))}")
    print(f"Blocked handles:  {len(cfg.get('blocked_handles', []))}")


def cmd_items(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, _ = await _open()
        try:
            states = (args.state,) if args.state else (
                storage.STATE_NEW, storage.STATE_HELD,
                storage.STATE_SENT_DIGEST, storage.STATE_SENT_INSTANT,
            )
            rows = await storage.get_unsent_items(conn, states=states, limit=args.limit)
            if not rows:
                print("no items")
                return
            for r in rows:
                flag = "R" if r["is_rumour"] else " "
                print(f"#{r['id']:<5} t{r['tier']}{flag} {r['state']:<12} "
                      f"{(r['source_name'] or '?')[:22]:<22} {r['title'][:70]}")
                if args.verbose and r["state_reason"]:
                    print(f"        why: {r['state_reason'][:160]}")
                if args.verbose:
                    print(f"        {r['url_canonical']}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_clear_kill_switch(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, _ = await _open()
        try:
            if not await storage.kill_switch_engaged(conn):
                print("Kill switch is not engaged.")
                return
            reason = await storage.get_flag(conn, "discord_kill_switch_reason", "?")
            print(f"Clearing kill switch. It was engaged because: {reason}")
            await storage.set_flag(conn, storage.KILL_SWITCH_FLAG, "false")
            print("Cleared. Verify your token and permissions before running again.")
        finally:
            await conn.close()

    asyncio.run(_run())



def cmd_invite_url(args: argparse.Namespace) -> None:
    client_id = args.client_id or os.environ.get("DISCORD_CLIENT_ID", "")
    perms = discord_setup.minimal_permissions(
        ping_role=args.with_mention_everyone,
        manage_automod=not args.no_automod,
    )
    print("--- Minimal permissions for this bot ---")
    total = 0
    for name, why in discord_setup.REQUIRED_CHANNEL_PERMS.items():
        bit = discord_setup.PERMS[name]
        total += bit
        print(f"  {name:<26} {bit:>12}   {why}")
    if args.with_mention_everyone:
        bit = discord_setup.PERMS[discord_setup.ROLE_PING_PERM]
        total += bit
        print(f"  {discord_setup.ROLE_PING_PERM:<26} {bit:>12}   "
              f"ping a non-mentionable role, GUILD-WIDE (not recommended)")
    if not args.no_automod:
        bit = discord_setup.PERMS[discord_setup.AUTOMOD_PERM]
        total += bit
        print(f"  {discord_setup.AUTOMOD_PERM:<26} {bit:>12}   "
              f"read/manage AutoMod rules (optional)")
    print(f"  {'TOTAL':<26} {total:>12}")
    if total != perms:
        print(f"  WARNING: sum {total} != computed bitfield {perms} (overlapping bits?)")
    print()
    if not client_id:
        print("Set DISCORD_CLIENT_ID in .env, or pass --client-id, to get the invite URL.")
        print("The Client ID (also called Application ID) is on the application's")
        print("General Information page - it is NOT a secret.")
        return
    print("--- Invite URL (open in a browser, pick your server) ---")
    print(discord_setup.invite_url(client_id, perms))


def cmd_discord_doctor(args: argparse.Namespace) -> None:
    async def _run() -> None:
        d = await discord_setup.diagnose(
            token=(os.environ.get("DISCORD_BOT_TOKEN") or "").strip(),
            channel_id=(os.environ.get("DISCORD_NEWS_CHANNEL_ID") or "").strip(),
            role_id=(os.environ.get("DISCORD_NEWS_ROLE_ID") or "").strip() or None,
            check_automod=not args.no_automod,
        )
        for c in d.checks:
            mark = "OK  " if c.ok else "FAIL"
            print(f"{mark} {c.name:<22} {c.detail}")
            if c.fix:
                for line in _wrap(c.fix, 74):
                    print(f"       -> {line}")
        print()
        if d.ok:
            print("Discord configuration looks correct.")
            print("Next: python -m src.main post-test --yes")
        else:
            print(f"{len(d.failures)} problem(s) to fix (listed above).")
            sys.exit(1)

    asyncio.run(_run())


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def cmd_post_test(args: argparse.Namespace) -> None:
    async def _run() -> None:
        token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
        channel = (os.environ.get("DISCORD_NEWS_CHANNEL_ID") or "").strip()
        if not token or not channel:
            print("DISCORD_BOT_TOKEN and DISCORD_NEWS_CHANNEL_ID must both be set.")
            sys.exit(1)
        if not args.yes:
            # Spelled out because POSTING_ENABLED does NOT gate this command,
            # and both README and DEPLOY previously implied it gated everything.
            # An installer who believed that could ping a live community by
            # following the verification steps literally.
            print("This posts a REAL message to your news channel. POSTING_ENABLED")
            print("does not apply to post-test — that is the point of the command.")
            if args.ping:
                role = (os.environ.get("DISCORD_NEWS_ROLE_ID") or "").strip()
                print(f"\n--ping will genuinely NOTIFY everyone holding role {role or '(unset)'}.")
                print("Do not run this against a populated server without telling the owner.")
            print("\nRe-run with --yes to confirm.")
            return
        if not (args.ping or args.digest):
            ok, detail = await discord_setup.send_test_message(
                token=token, channel_id=channel)
            print(("OK   " if ok else "FAIL ") + detail)
            if not ok:
                sys.exit(1)
            return

        conn, cfg = await _open()
        try:
            role = (os.environ.get("DISCORD_NEWS_ROLE_ID") or "").strip() or None

            if args.ping:
                # A real ping, but honest content. Injecting a fake "Extended
                # Look" headline would look identical to a genuine alert to
                # every member reading the channel, so the sample says what it
                # is while still exercising the real renderer and mention path.
                if not role:
                    print("FAIL DISCORD_NEWS_ROLE_ID is not set, so nothing would be pinged.")
                    sys.exit(1)
                entry = digest.DigestEntry(
                    item_id=0,
                    title="Alert test — this is what breaking GTA 6 news will look like",
                    url="https://www.rockstargames.com/VI",
                    source_name="gta6-news-bot",
                    label=credibility.LABEL_OFFICIAL,
                    summary=("A real first-party story will appear in this shape and ping "
                             "this role. Only Rockstar and Take-Two announcements trigger "
                             "it, so it stays rare. Safe to delete this message."),
                )
                payload = digest.render_instant_alert(entry, role_id=role)
                result = await discord_client.post_message(
                    conn, token=token, channel_id=channel, payload=payload,
                    dry_run=False, kind="test_alert",
                )
                print(("OK   alert posted, pinging role " + role) if result.sent
                      else "FAIL alert: " + result.detail)

            if args.digest:
                # Rendered from today's REAL clustered stories, so the layout,
                # labels and 'also' lists are exactly what members will get.
                rows = await storage.get_unsent_items(
                    conn, states=(storage.STATE_NEW, storage.STATE_HELD), limit=300)
                entries, _ = runner.build_digest_entries(rows, cfg)
                payload = digest.render_digest(
                    entries,
                    health_line="sample rendered from today's real stories",
                    date_label="SAMPLE — not today's digest",
                    max_items=int(os.environ.get("DIGEST_MAX_ITEMS", "8") or 8),
                )
                result = await discord_client.post_message(
                    conn, token=token, channel_id=channel, payload=payload,
                    dry_run=False, kind="test_digest",
                )
                print(("OK   sample digest posted with " + str(len(entries))
                       + " candidate stories") if result.sent
                      else "FAIL digest: " + result.detail)

            print("\nBoth samples are labelled as tests — delete them when you are done.")
        finally:
            await conn.close()

    asyncio.run(_run())



def cmd_automod_apply(args: argparse.Namespace) -> None:
    async def _run() -> None:
        token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
        channel = (os.environ.get("DISCORD_NEWS_CHANNEL_ID") or "").strip()
        if not token or not channel:
            print("DISCORD_BOT_TOKEN and DISCORD_NEWS_CHANNEL_ID must be set.")
            sys.exit(1)

        rules = automod.load_rules()
        problems = automod.validate(rules)
        print(f"--- Validating {len(rules)} rule(s) against Discord's limits ---")
        if problems:
            for pb in problems:
                print(f"FAIL  {pb}")
            print("\nFix config/automod.json before applying.")
            sys.exit(1)
        for r in rules:
            kw = len(r.get("keywords") or [])
            rx = len(r.get("regex_patterns") or [])
            mode = "BLOCK" if r.get("block") else "alert-only"
            print(f"OK    {r['name']:<44} {kw:>4} kw {rx:>3} rx  {mode}")

        alert = args.alert_channel or (os.environ.get("DISCORD_MOD_ALERT_CHANNEL_ID") or "").strip()
        if not alert:
            print("\nWARNING: no alert channel. Alert-only rules cannot be created "
                  "without one.")
            print("Pass --alert-channel <ID> or set DISCORD_MOD_ALERT_CHANNEL_ID in .env.")

        guild = await automod.guild_id_for_channel(token, channel)
        print(f"\nGuild: {guild}")
        existing = await automod.list_rules(token, guild)
        print(f"Existing AutoMod rules: {len(existing)}")
        for e in existing:
            print(f"  - {e['name']!r} "
                  f"({automod.TRIGGER_NAMES.get(e['trigger_type'], e['trigger_type'])}, "
                  f"{'enabled' if e['enabled'] else 'disabled'})")

        if not args.yes:
            print("\n--- DRY RUN (nothing will be changed) ---")
        results = await automod.apply_rules(
            token=token, guild_id=guild, rules=rules,
            alert_channel_id=alert or None, dry_run=not args.yes,
        )
        print()
        failed = 0
        for name, outcome in results:
            mark = "FAIL" if outcome.startswith("error") else "OK  "
            if outcome.startswith("error"):
                failed += 1
            print(f"{mark} {name:<44} {outcome}")
        if not args.yes:
            print("\nRe-run with --yes to create these rules for real.")
        elif failed:
            print(f"\n{failed} rule(s) failed.")
            sys.exit(1)
        else:
            print("\nDone. Remember AutoMod cannot scan attachments, images or video —")
            print("deny Attach Files + Embed Links to @everyone server-wide as well.")

    asyncio.run(_run())



def cmd_mark_caught_up(args: argparse.Namespace) -> None:
    """
    Treat everything currently unsent as already covered.

    Needed when moving an install, or when standing one up beside a channel that
    already has history. The digest selects by STATE, not by a time window, and
    posts at most 8 stories a day -- so a carried-over backlog of a few hundred
    items does not flood the channel, it does something worse: it trickles
    week-old news into the top slots for weeks, because ranking is by how many
    outlets carried a story and an old story has had longer to accumulate them.

    This is deliberately a separate command rather than something a migration
    script does silently: it discards editorial content, and that should be an
    explicit act.
    """
    async def _run() -> None:
        conn, _ = await _open()
        try:
            cutoff = None
            if args.older_than_hours > 0:
                cutoff = time.time() - args.older_than_hours * 3600
                sql = ("SELECT id FROM items WHERE state IN (?, ?) "
                       "AND (published_epoch IS NULL OR published_epoch < ?)")
                params = (storage.STATE_NEW, storage.STATE_HELD, cutoff)
            else:
                sql = "SELECT id FROM items WHERE state IN (?, ?)"
                params = (storage.STATE_NEW, storage.STATE_HELD)

            async with conn.execute(sql, params) as cur:
                ids = [int(r["id"]) for r in await cur.fetchall()]

            if not ids:
                print("Nothing unsent — already caught up.")
                return

            scope = (f"published more than {args.older_than_hours}h ago"
                     if cutoff else "in the backlog")
            print(f"{len(ids)} unsent item(s) {scope} will be marked as already covered.")
            print("They will never appear in a digest. This cannot be undone.")
            if not args.yes:
                print("\nRe-run with --yes to proceed.")
                return

            await storage.mark_items_state(
                conn, ids, storage.STATE_SENT_DIGEST, "marked caught up")
            print(f"Marked {len(ids)} item(s).")
            print(f"States now: {await storage.count_items_by_state(conn)}")
        finally:
            await conn.close()

    asyncio.run(_run())


def cmd_prune(args: argparse.Namespace) -> None:
    async def _run() -> None:
        conn, _ = await _open()
        try:
            held_ttl = int(os.environ.get("HELD_TTL_DAYS", "4") or 4)
            new_ttl = int(os.environ.get("UNSENT_TTL_DAYS", "5") or 5)
            keep = args.keep_days

            before = await storage.count_items_by_state(conn)
            print(f"before: {before}")

            if args.dry_run:
                print("\n--- DRY RUN (nothing will be changed) ---")
                print(f"would expire held items older than {held_ttl}d")
                print(f"would expire unsent items older than {new_ttl}d")
                print(f"would delete dropped/sent rows older than {keep}d")
                print("\nRe-run without --dry-run to apply.")
                return

            eh = await storage.expire_held_items(conn, older_than_days=held_ttl)
            en = await storage.expire_stale_new_items(conn, older_than_days=new_ttl)
            deleted = await storage.prune_items(conn, keep_days=keep)
            res = await storage.prune_url_resolutions(conn, keep_days=keep)

            print(f"expired held  (>{held_ttl}d): {eh}")
            print(f"expired unsent(>{new_ttl}d): {en}")
            print(f"deleted rows  (>{keep}d): {deleted}")
            print(f"deleted url resolutions : {res}")
            print(f"\nafter: {await storage.count_items_by_state(conn)}")
            print("\nNote: retention must outlive the dedup window — a deleted row no")
            print("longer suppresses a repost of the same story.")
        finally:
            await conn.close()

    asyncio.run(_run())



def cmd_make_task(args: argparse.Namespace) -> None:
    """
    Generate the Windows Task Scheduler XML for THIS machine.

    Exists because both ways of getting this wrong actually happened here:

      * the committed file carries placeholders, since a real one contains the
        machine name, user account and full project path — none of which belong
        in a shared repository;
      * the XML declares encoding="UTF-16" and Task Scheduler believes that
        declaration. Saved as UTF-8, a path containing non-ASCII characters is
        misdecoded and the task stores a WorkingDirectory that does not exist,
        so every run dies instantly with 0x8007010B, "the directory name is
        invalid". This writes UTF-16 LE with a BOM so bytes match the header.
    """
    import getpass
    import socket

    tpl_path = os.path.join(paths.PROJECT_ROOT, "infra", "gta6-news-bot-task.template.xml")
    out_path = os.path.join(paths.PROJECT_ROOT, "infra", "gta6-news-bot-task.xml")
    if not os.path.exists(tpl_path):
        print(f"template not found: {tpl_path}")
        sys.exit(1)

    pythonw = args.pythonw or os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw):
        print(f"WARN pythonw.exe not found at {pythonw}; pass --pythonw to override")
    user = args.user or f"{socket.gethostname()}\\{getpass.getuser()}"

    xml = open(tpl_path, "rb").read().decode("utf-16")
    xml = (xml.replace("__USERID__", user)
              .replace("__PYTHONW__", pythonw)
              .replace("__PROJECT_DIR__", paths.PROJECT_ROOT))
    with open(out_path, "wb") as fh:
        fh.write(b"\xff\xfe" + xml.encode("utf-16-le"))

    print("Wrote " + out_path)
    print(f"  user             : {user}")
    print(f"  pythonw          : {pythonw}")
    print(f"  working directory: {paths.PROJECT_ROOT}")
    print("  encoding         : UTF-16 LE with BOM (matches the XML declaration)")
    print("\nRegister it from PowerShell (NOT Git Bash, which mangles /tn):")
    print('  schtasks /create /tn "gta6-news-bot" /xml infra\\gta6-news-bot-task.xml /f')
    print("\nThen check it ran: LastTaskResult 0 is success; 0x8007010B means the")
    print("working directory is wrong, and 0x41301 just means 'currently running'.")


def cmd_build_web(args: argparse.Namespace) -> None:
    """
    Regenerate the web edition (every story, not just the digest's top 8).

    With --deploy, also runs WEB_DEPLOY_CMD. The deploy step is a config line
    rather than hardcoded tooling because the page is a single self-contained
    static file: Cloudflare Pages today, nginx on your own server later, and
    switching is one line in .env with no code change.
    """
    import subprocess
    sys.path.insert(0, paths.PROJECT_ROOT)
    from tools import export_web

    payload = asyncio.run(export_web.build())
    print(f"exported {payload['total_stories']} stories from {payload['total_items']} items")
    r = subprocess.run(
        [sys.executable, os.path.join(paths.PROJECT_ROOT, "tools", "build_web.py")],
        capture_output=True, text=True, cwd=paths.PROJECT_ROOT)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        sys.exit(1)

    if not args.deploy:
        print("\nBuilt only. Add --deploy to publish it.")
        return

    cmd = (os.environ.get("WEB_DEPLOY_CMD") or "").strip()
    if not cmd:
        print("\nWEB_DEPLOY_CMD is not set in .env, so there is nowhere to deploy to.")
        print("See .env.example for a Cloudflare Pages and a self-hosted example.")
        sys.exit(1)

    # A leading bare `python`/`python3` means "run this with the same Python I
    # am", and taking that literally breaks in two ways that both look like the
    # deploy tool failing rather than the interpreter being wrong:
    #   * Ubuntu ships no `python` binary at all (only `python3`), so a .env
    #     written on Windows fails nightly with `sh: python: not found`;
    #   * even `python3` resolves to the SYSTEM interpreter, not the venv the
    #     bot runs from, so the script starts and dies on a missing dependency.
    # Substituting sys.executable removes the whole class. Anything else in
    # WEB_DEPLOY_CMD is left exactly as the operator wrote it.
    head, _, tail = cmd.partition(" ")
    if head in ("python", "python3", "python.exe", "python3.exe"):
        cmd = f'"{sys.executable}" {tail}'.strip()

    print(f"\ndeploying: {cmd}")
    # shell=True is deliberate: the value is operator-authored config on the
    # operator's own machine, at the same trust level as the code itself, and a
    # deploy line is naturally shell-shaped (flags, pipes, an scp target).
    d = subprocess.run(cmd, shell=True, cwd=paths.PROJECT_ROOT,
                       capture_output=True, text=True)
    out = (d.stdout or "") + (d.stderr or "")
    print(out.strip()[-1500:])
    if d.returncode != 0:
        print(f"\nDeploy FAILED (exit {d.returncode}).")
        sys.exit(1)

    # Surface the URL so the operator can paste it into DIGEST_WEB_URL.
    import re as _re
    urls = _re.findall(r"https://[^\s\"']+", out)
    if urls:
        print("\nDeployed. URL(s) reported by the deploy command:")
        for u in dict.fromkeys(urls):
            print(f"  {u}")
    print("\nSet DIGEST_WEB_URL in .env to the PUBLIC url so the digest links to it.")
    print("Only set it once you have opened that url in a logged-out browser.")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.main",
        description="GTA 6 news digest bot for Discord.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="Create the database and register feeds")
    p_init.set_defaults(func=cmd_init_db)

    p_poll = sub.add_parser("poll", help="Fetch all feeds and ingest new items")
    p_poll.set_defaults(func=cmd_poll)

    p_run = sub.add_parser("run", help="Full cycle: poll, instant alerts, digest if due")
    p_run.add_argument("--dry-run", action="store_true", help="Print instead of posting")
    p_run.add_argument("--force", action="store_true", help="Post the digest regardless of hour")
    p_run.set_defaults(func=cmd_run)

    p_dig = sub.add_parser("digest", help="Build today's digest")
    p_dig.add_argument("--dry-run", action="store_true", help="Preview without posting")
    p_dig.add_argument("--force", action="store_true", help="Ignore the hour and the once-a-day guard")
    p_dig.add_argument("--no-poll", action="store_true", help="Use already-stored items only")
    p_dig.set_defaults(func=cmd_digest)

    p_st = sub.add_parser("status", help="Feed health, item counts, digest history")
    p_st.set_defaults(func=cmd_status)

    p_cr = sub.add_parser("check-ready", help="Verify configuration before going live")
    p_cr.set_defaults(func=cmd_check_ready)

    p_ls = sub.add_parser("list-sources", help="Show the configured source registry")
    p_ls.set_defaults(func=cmd_list_sources)

    p_it = sub.add_parser("items", help="List stored items")
    p_it.add_argument("--state", choices=[
        storage.STATE_NEW, storage.STATE_HELD,
        storage.STATE_SENT_DIGEST, storage.STATE_SENT_INSTANT, storage.STATE_DROPPED,
    ])
    p_it.add_argument("--limit", type=int, default=40)
    p_it.add_argument("-v", "--verbose", action="store_true")
    p_it.set_defaults(func=cmd_items)

    p_pr = sub.add_parser("prune", help="Expire stale items and delete old rows")
    p_pr.add_argument("--keep-days", type=int, default=30,
                      help="Delete dropped/sent rows older than this (default 30)")
    p_pr.add_argument("--dry-run", action="store_true", help="Show what would change")
    p_pr.set_defaults(func=cmd_prune)

    p_cu = sub.add_parser(
        "mark-caught-up",
        help="Treat the current unsent backlog as already covered (use before a migration)")
    p_cu.add_argument("--older-than-hours", type=int, default=0,
                      help="Only items published more than N hours ago (default 0 = all)")
    p_cu.add_argument("--yes", action="store_true", help="Skip the confirmation")
    p_cu.set_defaults(func=cmd_mark_caught_up)

    p_mt = sub.add_parser("make-task",
                          help="Generate the Task Scheduler XML for this machine")
    p_mt.add_argument("--pythonw", help="Path to pythonw.exe (default: alongside this python)")
    p_mt.add_argument("--user", help=r"MACHINE\user to run as (default: this account)")
    p_mt.set_defaults(func=cmd_make_task)

    p_bw = sub.add_parser("build-web", help="Regenerate the web edition of the digest")
    p_bw.add_argument("--deploy", action="store_true",
                      help="Also run WEB_DEPLOY_CMD to publish it")
    p_bw.set_defaults(func=cmd_build_web)

    p_ks = sub.add_parser("clear-kill-switch", help="Re-enable posting after an auth failure")
    p_ks.set_defaults(func=cmd_clear_kill_switch)

    p_inv = sub.add_parser("invite-url", help="Show minimal permissions and the bot invite URL")
    p_inv.add_argument("--client-id", help="Application (Client) ID; defaults to DISCORD_CLIENT_ID")
    p_inv.add_argument("--with-mention-everyone", action="store_true",
                       help="Add MENTION_EVERYONE guild-wide. Not recommended: grant it as a "
                            "channel overwrite in #news instead, so the opt-in role can stay "
                            "non-mentionable by members everywhere.")
    p_inv.add_argument("--no-automod", action="store_true",
                       help="Omit MANAGE_GUILD (you configure AutoMod by hand)")
    p_inv.set_defaults(func=cmd_invite_url)

    p_doc = sub.add_parser("discord-doctor",
                           help="Check the live Discord config and name what is wrong")
    p_doc.add_argument("--no-automod", action="store_true", help="Skip the AutoMod check")
    p_doc.set_defaults(func=cmd_discord_doctor)

    p_am = sub.add_parser("automod-apply",
                          help="Create the leak-blocking AutoMod rules from config/automod.json")
    p_am.add_argument("--alert-channel", help="Channel ID for moderator alerts")
    p_am.add_argument("--yes", action="store_true", help="Actually create them (default: dry run)")
    p_am.set_defaults(func=cmd_automod_apply)

    p_pt = sub.add_parser("post-test", help="Post a harmless test message to the news channel")
    p_pt.add_argument("--yes", action="store_true", help="Confirm the real post")
    p_pt.add_argument("--ping", action="store_true",
                      help="Send a sample instant alert that pings the opt-in role")
    p_pt.add_argument("--digest", action="store_true",
                      help="Send a sample digest rendered from today's real stories")
    p_pt.set_defaults(func=cmd_post_test)

    return p


def main(argv: list[str] | None = None) -> None:
    _load_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except BaseException:
        # Under pythonw.exe a traceback goes to a console that does not exist.
        # Log it, then exit 2 so Task Scheduler's Last Run Result distinguishes
        # "crashed" (2) from "ran but reported problems" (1) from "fine" (0).
        logger.exception("unhandled error in command %r", getattr(args, "command", "?"))
        sys.exit(2)


if __name__ == "__main__":
    main()
