"""
Persistence tests.

The bot is a short-lived process, so every guarantee it makes lives in SQLite.
These tests cover the three that matter:

  * one digest per local day (UNIQUE date_key as compare-and-set)
  * an item is never ingested twice (UNIQUE url_canonical)
  * the instant-alert / digest interlock (state machine, not a separate check)
"""
from __future__ import annotations

import asyncio

import pytest

from src import paths, storage
from tests.conftest import run


def _item(conn, **kw):
    base = dict(
        feed_key="vgc",
        url_canonical="https://example.com/a",
        url_original="https://example.com/a?utm_source=x",
        title="GTA 6 thing happens",
        title_hash="hash-a",
        source_name="VGC",
        source_domain="example.com",
        published_epoch=1_780_000_000,
        summary_raw="summary",
        tier=2,
        is_rumour=False,
    )
    base.update(kw)
    return storage.insert_item(conn, **base)


# ---------------------------------------------------------------------------
# Digest idempotency
# ---------------------------------------------------------------------------

def test_digest_can_only_be_claimed_once_per_day(conn):
    async def _t():
        first = await storage.record_digest_run(
            conn, date_key="2026-08-25", item_count=5,
            discord_message_id="111", dry_run=False,
        )
        second = await storage.record_digest_run(
            conn, date_key="2026-08-25", item_count=7,
            discord_message_id="222", dry_run=False,
        )
        return first, second

    first, second = run(_t())
    assert first is True, "first claim must succeed"
    assert second is False, "second claim on the same local date must be refused"


def test_digest_already_posted_reflects_the_claim(conn):
    async def _t():
        before = await storage.digest_already_posted(conn, "2026-08-25")
        await storage.record_digest_run(conn, date_key="2026-08-25", item_count=1,
                                       discord_message_id=None, dry_run=False)
        after = await storage.digest_already_posted(conn, "2026-08-25")
        other_day = await storage.digest_already_posted(conn, "2026-08-26")
        return before, after, other_day

    before, after, other_day = run(_t())
    assert before is False
    assert after is True
    assert other_day is False, "claiming one day must not block the next"


# ---------------------------------------------------------------------------
# Item dedup
# ---------------------------------------------------------------------------

def test_same_canonical_url_is_only_stored_once(conn):
    async def _t():
        a = await _item(conn)
        b = await _item(conn, title="Different headline, same link", title_hash="hash-b")
        return a, b

    a, b = run(_t())
    assert a is not None
    assert b is None, "duplicate canonical URL must be rejected by the UNIQUE index"


def test_different_urls_are_both_stored(conn):
    async def _t():
        a = await _item(conn, url_canonical="https://example.com/a", title_hash="h1")
        b = await _item(conn, url_canonical="https://example.com/b", title_hash="h2")
        return a, b

    a, b = run(_t())
    assert a is not None and b is not None and a != b


def test_title_hash_lookup_detects_reposts(conn):
    async def _t():
        await _item(conn, title_hash="shared-hash")
        return (
            await storage.title_hash_exists(conn, "shared-hash"),
            await storage.title_hash_exists(conn, "never-seen"),
        )

    seen, unseen = run(_t())
    assert seen is True
    assert unseen is False


# ---------------------------------------------------------------------------
# The interlock
# ---------------------------------------------------------------------------

def test_instant_alerted_item_is_excluded_from_the_digest(conn):
    """
    The interlock. An item moved to sent_instant must not appear in the digest
    candidate set, so a story cannot be announced twice in one evening.
    """
    async def _t():
        item_id = await _item(conn, url_canonical="https://example.com/official",
                              title_hash="h-official", tier=1)
        before = await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))
        await storage.mark_items_state(conn, [item_id], storage.STATE_SENT_INSTANT, "instant")
        after = await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))
        return before, after

    before, after = run(_t())
    assert len(before) == 1
    assert len(after) == 0


def test_held_items_are_not_digest_candidates(conn):
    async def _t():
        await _item(conn, url_canonical="https://example.com/held", title_hash="h-held",
                    state=storage.STATE_HELD)
        return await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))

    assert run(_t()) == []


def test_digest_sent_items_are_not_reused(conn):
    async def _t():
        item_id = await _item(conn)
        await storage.mark_items_state(conn, [item_id], storage.STATE_SENT_DIGEST, "digest")
        return await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))

    assert run(_t()) == []


def test_unsent_items_are_ordered_by_tier_first(conn):
    """Official news should lead the digest."""
    async def _t():
        await _item(conn, url_canonical="https://example.com/t3", title_hash="h3", tier=3)
        await _item(conn, url_canonical="https://example.com/t1", title_hash="h1", tier=1)
        await _item(conn, url_canonical="https://example.com/t2", title_hash="h2", tier=2)
        rows = await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))
        return [int(r["tier"]) for r in rows]

    assert run(_t()) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------

def test_kill_switch_persists(conn):
    """
    Persisted, not in-memory: the process restarts every 15 minutes, and an
    in-memory flag would resume hammering Discord with invalid credentials.
    """
    async def _t():
        before = await storage.kill_switch_engaged(conn)
        await storage.engage_kill_switch(conn, "HTTP 401 from Discord")
        after = await storage.kill_switch_engaged(conn)
        reason = await storage.get_flag(conn, "discord_kill_switch_reason")
        await storage.set_flag(conn, storage.KILL_SWITCH_FLAG, "false")
        cleared = await storage.kill_switch_engaged(conn)
        return before, after, reason, cleared

    before, after, reason, cleared = run(_t())
    assert before is False
    assert after is True
    assert "401" in reason
    assert cleared is False


# ---------------------------------------------------------------------------
# Feed state
# ---------------------------------------------------------------------------

def test_upsert_feed_preserves_learned_runtime_state(conn):
    """
    Re-reading config must not reset a backed-off politeness delay or an ETag —
    otherwise the short-lived process re-learns the same 429 forever.
    """
    async def _t():
        await storage.upsert_feed(conn, key="x", url="https://x.example/feed",
                                  tier=2, instant=False, poll_seconds=1800)
        await storage.set_politeness_delay(conn, "x", 40)
        await storage.record_fetch_success(conn, "x", status=200, etag='W/"abc"',
                                           last_modified="Mon, 25 Aug 2026 10:00:00 GMT",
                                           entry_count=5, newest_item_epoch=1_780_000_000)
        # Simulate a config reload.
        await storage.upsert_feed(conn, key="x", url="https://x.example/feed",
                                  tier=2, instant=False, poll_seconds=900)
        rows = await storage.get_feeds(conn)
        return next(r for r in rows if r["key"] == "x")

    row = run(_t())
    assert row["politeness_delay_s"] == 40, "backed-off delay was reset by config reload"
    assert row["etag"] == 'W/"abc"', "ETag was reset by config reload"
    assert row["poll_seconds"] == 900, "config value should still update"
    assert row["ever_had_entries"] == 1


def test_failure_increments_and_success_resets(conn):
    async def _t():
        await storage.upsert_feed(conn, key="y", url="https://y.example/feed",
                                  tier=2, instant=False, poll_seconds=1800)
        for _ in range(3):
            await storage.record_fetch_failure(conn, "y", status=503, error="boom")
        rows = await storage.get_feeds(conn)
        failed = next(r for r in rows if r["key"] == "y")["consecutive_failures"]
        await storage.record_fetch_success(conn, "y", status=200, etag=None,
                                           last_modified=None, entry_count=1,
                                           newest_item_epoch=None)
        rows = await storage.get_feeds(conn)
        reset = next(r for r in rows if r["key"] == "y")["consecutive_failures"]
        return failed, reset

    failed, reset = run(_t())
    assert failed == 3
    assert reset == 0


# ---------------------------------------------------------------------------
# The OneDrive guard
# ---------------------------------------------------------------------------

def test_refuses_to_open_a_database_under_onedrive(tmp_path, monkeypatch):
    monkeypatch.delenv("GTA6_ALLOW_SYNCED_DB", raising=False)
    fake = str(tmp_path / "OneDrive" / "project" / "bot.db")
    with pytest.raises(RuntimeError, match="cloud-synced"):
        paths.assert_not_synced(fake)


def test_sync_guard_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("GTA6_ALLOW_SYNCED_DB", "true")
    paths.assert_not_synced(str(tmp_path / "OneDrive" / "bot.db"))  # must not raise


def test_default_db_path_is_not_synced():
    """The shipped default must pass its own guard."""
    assert not paths.is_cloud_synced(paths.db_path())


# ---------------------------------------------------------------------------
# Retention: held items must be able to leave the held state
# ---------------------------------------------------------------------------

def test_held_items_expire(conn):
    """
    Without a TTL the held queue only grows and a weeks-old unconfirmed rumour
    stays eligible for tonight's digest.
    """
    from src.clock import epoch_now

    async def _t():
        old = await _item(conn, url_canonical="https://x.test/old", title_hash="h-old",
                          state=storage.STATE_HELD,
                          published_epoch=epoch_now() - 10 * 86400)
        fresh = await _item(conn, url_canonical="https://x.test/new", title_hash="h-new",
                            state=storage.STATE_HELD,
                            published_epoch=epoch_now() - 3600)
        n = await storage.expire_held_items(conn, older_than_days=4)
        held = await storage.get_unsent_items(conn, states=(storage.STATE_HELD,))
        return old, fresh, n, [r["id"] for r in held]

    old, fresh, n, still_held = run(_t())
    assert n == 1
    assert still_held == [fresh], "only the stale held item should expire"


def test_stale_unsent_items_expire(conn):
    """The ingest age gate only filters new arrivals; stored rows need a bound too."""
    from src.clock import epoch_now

    async def _t():
        await _item(conn, url_canonical="https://x.test/stale", title_hash="h-stale",
                    published_epoch=epoch_now() - 30 * 86400)
        n = await storage.expire_stale_new_items(conn, older_than_days=5)
        return n, await storage.get_unsent_items(conn, states=(storage.STATE_NEW,))

    n, remaining = run(_t())
    assert n == 1
    assert remaining == []


def test_expiry_is_a_noop_when_disabled(conn):
    async def _t():
        await _item(conn, state=storage.STATE_HELD)
        return await storage.expire_held_items(conn, older_than_days=0)

    assert run(_t()) == 0


def test_prune_deletes_only_terminal_rows(conn):
    """A pruned row no longer suppresses a repost, so live states must survive."""
    from src.clock import epoch_now
    ancient = epoch_now() - 365 * 86400

    async def _t():
        keep_new = await _item(conn, url_canonical="https://x.test/keep",
                               title_hash="h-keep", state=storage.STATE_NEW)
        keep_held = await _item(conn, url_canonical="https://x.test/held",
                                title_hash="h-held2", state=storage.STATE_HELD)
        await _item(conn, url_canonical="https://x.test/gone", title_hash="h-gone",
                    state=storage.STATE_DROPPED)
        # Backdate everything so age is not what distinguishes them.
        await conn.execute("UPDATE items SET first_seen_epoch = ?", (ancient,))
        await conn.commit()
        deleted = await storage.prune_items(conn, keep_days=30)
        async with conn.execute("SELECT id FROM items ORDER BY id") as cur:
            left = [r["id"] for r in await cur.fetchall()]
        return keep_new, keep_held, deleted, left

    keep_new, keep_held, deleted, left = run(_t())
    assert deleted == 1
    assert sorted(left) == sorted([keep_new, keep_held]), (
        "pruning must never delete a row still waiting to be published"
    )


def test_prune_respects_keep_days(conn):
    async def _t():
        await _item(conn, state=storage.STATE_DROPPED)
        return await storage.prune_items(conn, keep_days=30)

    assert run(_t()) == 0, "a freshly-dropped row is inside the retention window"


# ---------------------------------------------------------------------------
# Digest claim lifecycle
# ---------------------------------------------------------------------------

def test_claim_then_attach_message_id(conn):
    """The slot is claimed BEFORE posting, so the id arrives afterwards."""
    async def _t():
        claimed = await storage.record_digest_run(
            conn, date_key="2026-08-26", item_count=0,
            discord_message_id=None, dry_run=False)
        await storage.attach_digest_message(
            conn, date_key="2026-08-26", discord_message_id="555", item_count=6)
        rows = await storage.get_recent_digest_runs(conn, 5)
        return claimed, rows[0]["discord_message_id"], rows[0]["item_count"]

    claimed, mid, count = run(_t())
    assert claimed is True
    assert mid == "555"
    assert count == 6


def test_failed_post_releases_the_claim(conn):
    """
    A transient Discord failure must not consume the day's only slot, or no
    digest could be posted until tomorrow.
    """
    async def _t():
        await storage.record_digest_run(
            conn, date_key="2026-08-26", item_count=0,
            discord_message_id=None, dry_run=False)
        await storage.release_digest_claim(conn, "2026-08-26")
        return await storage.digest_already_posted(conn, "2026-08-26")

    assert run(_t()) is False


def test_release_does_not_delete_a_successful_post(conn):
    """Releasing must only reclaim an UNUSED claim."""
    async def _t():
        await storage.record_digest_run(
            conn, date_key="2026-08-26", item_count=0,
            discord_message_id=None, dry_run=False)
        await storage.attach_digest_message(
            conn, date_key="2026-08-26", discord_message_id="777", item_count=3)
        await storage.release_digest_claim(conn, "2026-08-26")
        return await storage.digest_already_posted(conn, "2026-08-26")

    assert run(_t()) is True
