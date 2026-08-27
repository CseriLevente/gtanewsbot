"""
SQLite persistence.

Design notes that matter:

  * The bot runs as a short-lived process every 15 minutes, so NOTHING may be
    held in memory between runs. Every decision (has today's digest posted? has
    this item been sent? what is this feed's ETag?) is a SELECT.
  * `items.url_canonical` carries a UNIQUE index. That index IS the exact-dup
    guard, and unlike an in-memory set it survives a restart.
  * `digest_runs.date_key` carries a UNIQUE index. That is the idempotency
    guarantee for "one digest per local day" — cheaper and more reliable than
    any time-window logic.
  * Journal mode is TRUNCATE, not WAL. See connect() — WAL was dropped after
    scheduled-task commits were observed reaching a side-car the shared file
    never received.
  * A local row is NOT sufficient evidence that the digest posted. The
    authoritative duplicate check reads the Discord channel; see
    discord_client.digest_already_in_channel().
"""
from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Sequence

import aiosqlite

from src import paths
from src.clock import epoch_now, local_date_key

logger = logging.getLogger(__name__)

# Item lifecycle states.
STATE_NEW = "new"            # ingested, not yet judged
STATE_HELD = "held"          # needs corroboration before it can be posted
STATE_SENT_INSTANT = "sent_instant"
STATE_SENT_DIGEST = "sent_digest"
STATE_DROPPED = "dropped"    # failed credibility or hard-blocked

SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
    key                  TEXT PRIMARY KEY,
    url                  TEXT NOT NULL,
    tier                 INTEGER NOT NULL,
    instant              INTEGER NOT NULL DEFAULT 0,
    poll_seconds         INTEGER NOT NULL DEFAULT 1800,
    enabled              INTEGER NOT NULL DEFAULT 1,
    -- HTTP conditional-request state
    etag                 TEXT,
    last_modified        TEXT,
    -- health
    last_fetch_epoch     INTEGER,
    last_status          INTEGER,
    last_error           TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_item_epoch      INTEGER,
    ever_had_entries     INTEGER NOT NULL DEFAULT 0,
    -- persisted politeness: a short-lived process would otherwise re-learn the
    -- same 429 every 15 minutes
    politeness_delay_s   INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_key         TEXT NOT NULL,
    url_canonical    TEXT NOT NULL UNIQUE,
    url_original     TEXT NOT NULL,
    title            TEXT NOT NULL,
    title_hash       TEXT NOT NULL,
    source_name      TEXT,
    source_domain    TEXT,
    published_epoch  INTEGER,
    first_seen_epoch INTEGER NOT NULL,
    summary_raw      TEXT,
    tier             INTEGER NOT NULL,
    is_rumour        INTEGER NOT NULL DEFAULT 0,
    state            TEXT NOT NULL DEFAULT 'new',
    state_reason     TEXT,
    cluster_id       INTEGER,
    retract_checked_epoch INTEGER
);

CREATE INDEX IF NOT EXISTS idx_items_state      ON items(state);
CREATE INDEX IF NOT EXISTS idx_items_title_hash ON items(title_hash);
CREATE INDEX IF NOT EXISTS idx_items_first_seen ON items(first_seen_epoch);
CREATE INDEX IF NOT EXISTS idx_items_cluster    ON items(cluster_id);

CREATE TABLE IF NOT EXISTS digest_runs (
    date_key           TEXT PRIMARY KEY,
    posted_epoch       INTEGER NOT NULL,
    item_count         INTEGER NOT NULL,
    discord_message_id TEXT,
    dry_run            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS url_resolutions (
    wrapper_url   TEXT PRIMARY KEY,
    resolved_url  TEXT NOT NULL,
    resolved_epoch INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS post_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    kind               TEXT NOT NULL,
    item_id            INTEGER,
    discord_message_id TEXT,
    posted_epoch       INTEGER NOT NULL,
    dry_run            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS app_flags (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def connect(db_path: str | None = None) -> aiosqlite.Connection:
    """
    Open the database, applying the pragmas and the cloud-sync guard.

    The guard is not paranoia: OneDrive syncs bot.db, -wal and -shm as three
    independent files, so a restore can pair a stale .db with a newer -wal,
    which is corrupt by definition.
    """
    path = db_path or paths.db_path()
    paths.assert_not_synced(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    # TRUNCATE, not WAL — deliberately.
    #
    # Under WAL, commits land in a side-car `-wal` file and only reach bot.db at
    # a checkpoint. Observed on this machine 2026-08-27: a scheduled run posted
    # the digest and wrote its bookkeeping, a later run in the same 15-minute
    # cycle could READ that row, and yet bot.db's mtime never advanced past the
    # previous hand-run — every write since then was ultimately discarded. The
    # digest went out while digest_runs stayed empty and no item was marked
    # sent, which is precisely the state that causes a repeat post.
    #
    # The root cause of the lost WAL was not identified. WAL's benefit here is
    # near-zero anyway (one writer, a few hundred tiny rows, a process that
    # exits every run), so the side-car is pure risk. TRUNCATE commits straight
    # into the main file, and `synchronous=FULL` makes the commit durable rather
    # than merely handed to the OS.
    await conn.execute("PRAGMA journal_mode=TRUNCATE")
    await conn.execute("PRAGMA busy_timeout=5000")
    await conn.execute("PRAGMA synchronous=FULL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def init_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript(SCHEMA)
    await conn.commit()


# ---------------------------------------------------------------------------
# Feeds
# ---------------------------------------------------------------------------

async def upsert_feed(
    conn: aiosqlite.Connection,
    *,
    key: str,
    url: str,
    tier: int,
    instant: bool,
    poll_seconds: int,
    enabled: bool = True,
) -> None:
    """
    Register a feed from config without clobbering its learned runtime state.

    ETag, failure counts and the politeness delay are deliberately NOT reset —
    they are learned at runtime and re-learning them on every config load would
    defeat the point of persisting them.
    """
    await conn.execute(
        """
        INSERT INTO feeds (key, url, tier, instant, poll_seconds, enabled)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            url          = excluded.url,
            tier         = excluded.tier,
            instant      = excluded.instant,
            poll_seconds = excluded.poll_seconds,
            enabled      = excluded.enabled
        """,
        (key, url, tier, 1 if instant else 0, poll_seconds, 1 if enabled else 0),
    )
    await conn.commit()


async def get_feeds(conn: aiosqlite.Connection, *, enabled_only: bool = True) -> list[aiosqlite.Row]:
    sql = "SELECT * FROM feeds"
    if enabled_only:
        sql += " WHERE enabled = 1"
    sql += " ORDER BY tier, key"
    async with conn.execute(sql) as cur:
        return list(await cur.fetchall())


async def record_fetch_success(
    conn: aiosqlite.Connection,
    key: str,
    *,
    status: int,
    etag: str | None,
    last_modified: str | None,
    entry_count: int,
    newest_item_epoch: int | None,
) -> None:
    await conn.execute(
        """
        UPDATE feeds SET
            last_fetch_epoch     = ?,
            last_status          = ?,
            last_error           = NULL,
            consecutive_failures = 0,
            etag                 = COALESCE(?, etag),
            last_modified        = COALESCE(?, last_modified),
            ever_had_entries     = CASE WHEN ? > 0 THEN 1 ELSE ever_had_entries END,
            last_item_epoch      = COALESCE(MAX(COALESCE(last_item_epoch, 0), ?), last_item_epoch)
        WHERE key = ?
        """,
        (epoch_now(), status, etag, last_modified, entry_count,
         newest_item_epoch, key),
    )
    await conn.commit()


async def record_fetch_failure(
    conn: aiosqlite.Connection, key: str, *, status: int | None, error: str
) -> None:
    await conn.execute(
        """
        UPDATE feeds SET
            last_fetch_epoch     = ?,
            last_status          = ?,
            last_error           = ?,
            consecutive_failures = consecutive_failures + 1
        WHERE key = ?
        """,
        (epoch_now(), status, error[:500], key),
    )
    await conn.commit()


async def set_politeness_delay(conn: aiosqlite.Connection, key: str, seconds: int) -> None:
    """Persist a backed-off delay so the next short-lived run inherits it."""
    await conn.execute("UPDATE feeds SET politeness_delay_s = ? WHERE key = ?", (seconds, key))
    await conn.commit()


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

async def insert_item(
    conn: aiosqlite.Connection,
    *,
    feed_key: str,
    url_canonical: str,
    url_original: str,
    title: str,
    title_hash: str,
    source_name: str | None,
    source_domain: str | None,
    published_epoch: int | None,
    summary_raw: str | None,
    tier: int,
    is_rumour: bool,
    state: str = STATE_NEW,
    state_reason: str | None = None,
) -> int | None:
    """
    Insert an item. Returns the new rowid, or None if it was a duplicate.

    Duplicate detection is delegated to the UNIQUE index on url_canonical —
    INSERT OR IGNORE plus a changes() check is cheaper and more reliable than a
    SELECT-then-INSERT race.
    """
    cur = await conn.execute(
        """
        INSERT OR IGNORE INTO items (
            feed_key, url_canonical, url_original, title, title_hash,
            source_name, source_domain, published_epoch, first_seen_epoch,
            summary_raw, tier, is_rumour, state, state_reason
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (feed_key, url_canonical, url_original, title, title_hash,
         source_name, source_domain, published_epoch, epoch_now(),
         summary_raw, tier, 1 if is_rumour else 0, state, state_reason),
    )
    await conn.commit()
    if cur.rowcount == 0:
        return None
    return cur.lastrowid


async def title_hash_exists(conn: aiosqlite.Connection, title_hash: str, *, within_seconds: int = 7 * 86400) -> bool:
    """
    True if a near-identical headline was already ingested recently.

    Time-bounded so an annually recurring headline ("everything we know about
    GTA 6") is not suppressed forever.
    """
    async with conn.execute(
        "SELECT 1 FROM items WHERE title_hash = ? AND first_seen_epoch >= ? LIMIT 1",
        (title_hash, epoch_now() - within_seconds),
    ) as cur:
        return await cur.fetchone() is not None


async def get_unsent_items(
    conn: aiosqlite.Connection, *, states: Sequence[str] = (STATE_NEW,), limit: int = 200
) -> list[aiosqlite.Row]:
    """
    Candidates for the digest, selected by STATE — never by a time window.

    This is the DST-safe formulation: an ambiguous or missing local hour cannot
    silently drop or duplicate items, because membership does not depend on the
    clock at all.
    """
    marks = ",".join("?" for _ in states)
    async with conn.execute(
        f"""
        SELECT * FROM items
        WHERE state IN ({marks})
        ORDER BY tier ASC, COALESCE(published_epoch, first_seen_epoch) DESC
        LIMIT ?
        """,
        (*states, limit),
    ) as cur:
        return list(await cur.fetchall())


async def mark_items_state(
    conn: aiosqlite.Connection, item_ids: Iterable[int], state: str, reason: str | None = None
) -> int:
    ids = list(item_ids)
    if not ids:
        return 0
    marks = ",".join("?" for _ in ids)
    cur = await conn.execute(
        f"UPDATE items SET state = ?, state_reason = ? WHERE id IN ({marks})",
        (state, reason, *ids),
    )
    await conn.commit()
    return cur.rowcount


async def expire_held_items(conn: aiosqlite.Connection, *, older_than_days: int) -> int:
    """
    Retire held items that were never corroborated.

    A held item is one waiting for independent confirmation that may never
    arrive. Without an expiry the queue only grows (110 rows after two days at
    current volume) and, worse, a three-week-old unconfirmed rumour stays
    eligible for tonight's digest — so a channel whose whole promise is "today"
    can publish a story from last month as news.

    Expiry is by PUBLICATION time where known, falling back to first-seen, and
    uses epoch seconds so it is unaffected by DST.
    """
    if older_than_days <= 0:
        return 0
    cutoff = epoch_now() - older_than_days * 86400
    cur = await conn.execute(
        """
        UPDATE items SET state = ?, state_reason = ?
        WHERE state = ? AND COALESCE(published_epoch, first_seen_epoch) < ?
        """,
        (STATE_DROPPED, f"expired unconfirmed after {older_than_days}d", STATE_HELD, cutoff),
    )
    await conn.commit()
    return cur.rowcount


async def expire_stale_new_items(conn: aiosqlite.Connection, *, older_than_days: int) -> int:
    """
    Retire unsent items that are simply too old to present as news.

    The 3-day gate in feeds.py only filters at INGEST. Anything already stored
    stays a digest candidate forever, so on a quiet day the digest would surface
    week-old headlines as today's news — exactly what the ingest gate exists to
    prevent.
    """
    if older_than_days <= 0:
        return 0
    cutoff = epoch_now() - older_than_days * 86400
    cur = await conn.execute(
        """
        UPDATE items SET state = ?, state_reason = ?
        WHERE state = ? AND COALESCE(published_epoch, first_seen_epoch) < ?
        """,
        (STATE_DROPPED, f"too old to publish ({older_than_days}d)", STATE_NEW, cutoff),
    )
    await conn.commit()
    return cur.rowcount


async def prune_items(conn: aiosqlite.Connection, *, keep_days: int) -> int:
    """
    Delete rows the bot will never look at again.

    Retention has to outlive the dedup window: a deleted row is a row whose URL
    and title hash no longer suppress a repost, so pruning too aggressively
    makes old stories eligible to be published a second time.
    """
    if keep_days <= 0:
        return 0
    cutoff = epoch_now() - keep_days * 86400
    cur = await conn.execute(
        "DELETE FROM items WHERE first_seen_epoch < ? AND state IN (?, ?)",
        (cutoff, STATE_DROPPED, STATE_SENT_DIGEST),
    )
    await conn.commit()
    return cur.rowcount


async def prune_url_resolutions(conn: aiosqlite.Connection, *, keep_days: int) -> int:
    if keep_days <= 0:
        return 0
    cutoff = epoch_now() - keep_days * 86400
    cur = await conn.execute(
        "DELETE FROM url_resolutions WHERE resolved_epoch < ?", (cutoff,)
    )
    await conn.commit()
    return cur.rowcount


async def count_items_by_state(conn: aiosqlite.Connection) -> dict[str, int]:
    async with conn.execute("SELECT state, COUNT(*) c FROM items GROUP BY state") as cur:
        return {r["state"]: r["c"] for r in await cur.fetchall()}


# ---------------------------------------------------------------------------
# Digest runs — the once-per-local-day idempotency guard
# ---------------------------------------------------------------------------

async def digest_already_posted(conn: aiosqlite.Connection, date_key: str | None = None) -> bool:
    key = date_key or local_date_key()
    async with conn.execute("SELECT 1 FROM digest_runs WHERE date_key = ?", (key,)) as cur:
        return await cur.fetchone() is not None


async def record_digest_run(
    conn: aiosqlite.Connection,
    *,
    date_key: str | None = None,
    item_count: int,
    discord_message_id: str | None,
    dry_run: bool,
) -> bool:
    """
    Claim today's digest slot. Returns False if it was already claimed.

    INSERT OR IGNORE against the UNIQUE date_key makes this a compare-and-set,
    so two overlapping runs cannot both post.
    """
    key = date_key or local_date_key()
    cur = await conn.execute(
        """
        INSERT OR IGNORE INTO digest_runs
            (date_key, posted_epoch, item_count, discord_message_id, dry_run)
        VALUES (?,?,?,?,?)
        """,
        (key, epoch_now(), item_count, discord_message_id, 1 if dry_run else 0),
    )
    await conn.commit()
    return cur.rowcount > 0


async def attach_digest_message(
    conn: aiosqlite.Connection, *, date_key: str, discord_message_id: str | None,
    item_count: int,
) -> None:
    """
    Fill in the message id after a successful post.

    The row is inserted BEFORE posting (to claim the day), so the message id is
    not known yet at insert time.
    """
    await conn.execute(
        "UPDATE digest_runs SET discord_message_id = ?, item_count = ? WHERE date_key = ?",
        (discord_message_id, item_count, date_key),
    )
    await conn.commit()


async def release_digest_claim(conn: aiosqlite.Connection, date_key: str) -> None:
    """
    Give back an unused claim after a failed post.

    Without this, a transient Discord failure would permanently consume the
    day's only slot and no digest could be posted until tomorrow.
    """
    await conn.execute(
        "DELETE FROM digest_runs WHERE date_key = ? AND discord_message_id IS NULL",
        (date_key,),
    )
    await conn.commit()


async def get_recent_digest_runs(conn: aiosqlite.Connection, limit: int = 14) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT * FROM digest_runs ORDER BY date_key DESC LIMIT ?", (limit,)
    ) as cur:
        return list(await cur.fetchall())


# ---------------------------------------------------------------------------
# URL resolution cache
# ---------------------------------------------------------------------------

async def get_cached_resolution(conn: aiosqlite.Connection, wrapper_url: str) -> str | None:
    async with conn.execute(
        "SELECT resolved_url FROM url_resolutions WHERE wrapper_url = ?", (wrapper_url,)
    ) as cur:
        row = await cur.fetchone()
        return row["resolved_url"] if row else None


async def cache_resolution(conn: aiosqlite.Connection, wrapper_url: str, resolved_url: str) -> None:
    await conn.execute(
        """
        INSERT INTO url_resolutions (wrapper_url, resolved_url, resolved_epoch)
        VALUES (?,?,?)
        ON CONFLICT(wrapper_url) DO UPDATE SET
            resolved_url = excluded.resolved_url,
            resolved_epoch = excluded.resolved_epoch
        """,
        (wrapper_url, resolved_url, epoch_now()),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# Post log + flags
# ---------------------------------------------------------------------------

async def log_post(
    conn: aiosqlite.Connection,
    *,
    kind: str,
    item_id: int | None,
    discord_message_id: str | None,
    dry_run: bool,
) -> None:
    await conn.execute(
        """
        INSERT INTO post_log (kind, item_id, discord_message_id, posted_epoch, dry_run)
        VALUES (?,?,?,?,?)
        """,
        (kind, item_id, discord_message_id, epoch_now(), 1 if dry_run else 0),
    )
    await conn.commit()


async def get_flag(conn: aiosqlite.Connection, key: str, default: str = "") -> str:
    async with conn.execute("SELECT value FROM app_flags WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
        return row["value"] if row else default


async def set_flag(conn: aiosqlite.Connection, key: str, value: str) -> None:
    await conn.execute(
        """
        INSERT INTO app_flags (key, value) VALUES (?,?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    await conn.commit()


KILL_SWITCH_FLAG = "discord_kill_switch"


async def kill_switch_engaged(conn: aiosqlite.Connection) -> bool:
    return (await get_flag(conn, KILL_SWITCH_FLAG, "false")).casefold() in ("1", "true", "yes")


async def engage_kill_switch(conn: aiosqlite.Connection, reason: str) -> None:
    """
    Latch posting off after a fatal Discord auth error.

    Persisted rather than in-memory precisely because the process is
    short-lived: an in-memory flag would reset in 15 minutes and resume hammering
    Discord with invalid credentials. 10,000 invalid requests in 10 minutes earns
    a Cloudflare IP ban that takes the entire household off Discord.
    """
    await set_flag(conn, KILL_SWITCH_FLAG, "true")
    await set_flag(conn, "discord_kill_switch_reason", reason[:500])
    logger.error("Discord kill switch ENGAGED: %s", reason)


async def verify_write_persistence(db_path: str | None = None) -> tuple[bool, str]:
    """
    Prove that a committed write survives closing and reopening the database.

    This exists because of a real, unexplained failure on the operator's machine
    (2026-08-27): a scheduled run posted the digest and committed its
    bookkeeping, a later run in the same cycle could READ that row, and yet the
    row was absent from bot.db afterwards and the file's mtime never advanced.
    The digest went out while `digest_runs` stayed empty and no item was marked
    sent — exactly the state that causes a repeat post.

    Rather than trust that storage works, check it: write a canary, close the
    connection, reopen, and read it back. A False result means the bot's
    once-per-day guarantee cannot be honoured on this machine, and posting
    should stay off until it is fixed.
    """
    path = db_path or paths.db_path()
    canary = f"persistence-canary-{epoch_now()}"
    try:
        conn = await connect(path)
        await init_schema(conn)
        await set_flag(conn, "persistence_canary", canary)
        async with conn.execute("PRAGMA journal_mode") as cur:
            mode = (await cur.fetchone())[0]
        await conn.close()

        conn2 = await connect(path)
        readback = await get_flag(conn2, "persistence_canary", "")
        await conn2.close()
    except Exception as exc:
        return False, f"persistence check errored: {type(exc).__name__}: {exc}"

    if readback == canary:
        return True, f"committed write survived a reopen (journal_mode={mode})"
    return False, (
        f"WRITE LOST: wrote {canary!r}, read back {readback!r} after reopening "
        f"(journal_mode={mode}). Committed data is not reaching {path}. Do not "
        f"enable posting: the once-per-day guard cannot work, so the digest can "
        f"be posted repeatedly."
    )
