"""
Orchestration tests.

THE INVARIANT THIS FILE EXISTS FOR: a dry run must not mutate state.

An earlier version marked instant-alert candidates as `sent_instant` on a dry
run. Because POSTING_ENABLED=false forces dry-run mode, that silently consumed
every tier-1 story before the operator had even switched posting on — the item
was recorded as "already alerted" while nobody was notified, and the alert could
then never fire. It would have eaten the GTA 6 Extended Look announcement.
"""
from __future__ import annotations

from src import credibility, runner, storage
from tests.conftest import run


def _insert(conn, **kw):
    base = dict(
        feed_key="rockstar_youtube",
        url_canonical="https://youtube.com/watch?v=extended-look",
        url_original="https://youtube.com/watch?v=extended-look",
        title="Grand Theft Auto VI: An Extended Look",
        title_hash="hash-extended-look",
        source_name="Rockstar Games",
        source_domain="youtube.com",
        published_epoch=1_787_000_000,
        summary_raw=None,
        tier=1,
        is_rumour=False,
        state=storage.STATE_NEW,
    )
    base.update(kw)
    return storage.insert_item(conn, **base)


def _state_of(conn, item_id):
    async def _q():
        async with conn.execute("SELECT state FROM items WHERE id = ?", (item_id,)) as cur:
            row = await cur.fetchone()
            return row["state"] if row else None
    return _q()


# ---------------------------------------------------------------------------
# The dry-run invariant
# ---------------------------------------------------------------------------

def test_dry_run_does_not_consume_instant_alert_candidates(conn, cfg):
    """The regression that would have swallowed the Extended Look alert."""
    async def _t():
        item_id = await _insert(conn)
        sent, details = await runner.send_instant_alerts(
            conn, cfg, dry_run=True, health_line="test"
        )
        return item_id, sent, details, await _state_of(conn, item_id)

    item_id, sent, details, state = run(_t())
    assert sent == 0, "a dry run must not report anything as sent"
    assert state == storage.STATE_NEW, (
        "a dry run left the item marked as alerted; the real alert can now never fire"
    )
    assert any("still queued" in d for d in details), (
        "the operator should be told the item is still pending"
    )


def test_dry_run_leaves_item_available_for_a_later_real_run(conn, cfg):
    """Two dry runs in a row must not exhaust the queue."""
    async def _t():
        item_id = await _insert(conn)
        for _ in range(3):
            await runner.send_instant_alerts(conn, cfg, dry_run=True, health_line="t")
        return await _state_of(conn, item_id)

    assert run(_t()) == storage.STATE_NEW


def test_failed_send_does_not_consume_the_item(conn, cfg):
    """
    A real (non-dry) attempt with no credentials fails. The item must stay
    queued, or a transient outage would permanently lose the alert.
    """
    async def _t():
        item_id = await _insert(conn)
        sent, _ = await runner.send_instant_alerts(
            conn, cfg, dry_run=False, health_line="t"
        )
        return sent, await _state_of(conn, item_id)

    sent, state = run(_t())
    assert sent == 0
    assert state == storage.STATE_NEW


# ---------------------------------------------------------------------------
# Instant-alert eligibility
# ---------------------------------------------------------------------------

def test_rumours_are_never_instant_alerted(conn, cfg):
    """A push notification is only justified for confirmed first-party news."""
    async def _t():
        item_id = await _insert(conn, is_rumour=True, title="Rockstar responds to leaks",
                                title_hash="h-rumour")
        _, details = await runner.send_instant_alerts(
            conn, cfg, dry_run=True, health_line="t"
        )
        return item_id, details

    _, details = run(_t())
    assert details == [], "a rumour must not be a candidate for an instant alert"


def test_tier2_is_never_instant_alerted(conn, cfg):
    async def _t():
        await _insert(conn, tier=2, feed_key="vgc", title_hash="h-t2",
                      url_canonical="https://vgc.com/a")
        _, details = await runner.send_instant_alerts(
            conn, cfg, dry_run=True, health_line="t"
        )
        return details

    assert run(_t()) == []


def test_non_instant_feed_is_not_alerted(conn, cfg):
    """Tier 1 alone is not enough — the feed must be flagged instant."""
    async def _t():
        await _insert(conn, feed_key="google_news_rockstar_site",
                      title_hash="h-notinstant",
                      url_canonical="https://news.google.com/x")
        _, details = await runner.send_instant_alerts(
            conn, cfg, dry_run=True, health_line="t"
        )
        return details

    assert run(_t()) == []


# ---------------------------------------------------------------------------
# Digest entry building
# ---------------------------------------------------------------------------

def test_build_digest_entries_marks_every_cluster_member(cfg):
    """
    All members carry into member_ids, so a posted story does not resurface
    tomorrow via the outlets we did not link.
    """
    rows = [
        dict(id=1, title="NBA 2K27 Teases GTA 6 Crossover Of Some Kind",
             url_canonical="https://gamespot.com/a", source_name="GameSpot",
             source_domain="gamespot.com", tier=2, is_rumour=0,
             state=storage.STATE_NEW, published_epoch=100, summary_raw=""),
        dict(id=2, title="NBA 2K27 Teases A GTA 6 -Themed Season Coming Later This Year",
             url_canonical="https://kotaku.com/b", source_name="Kotaku",
             source_domain="kotaku.com", tier=2, is_rumour=0,
             state=storage.STATE_NEW, published_epoch=200, summary_raw=""),
    ]
    entries, promoted = runner.build_digest_entries(rows, cfg)
    assert len(entries) == 1, "one story, one entry"
    assert sorted(entries[0].member_ids) == [1, 2]
    assert promoted == []


def test_held_item_is_promoted_by_corroboration(cfg):
    """
    Clustering supplies the corroboration count that judge() previously always
    received as 0, which left tier-3 items held forever.
    """
    rows = [
        dict(id=1, title="GTA 6 nightclub interiors shown in new footage",
             url_canonical="https://rockstarintel.com/a", source_name="RockstarINTEL",
             source_domain="rockstarintel.com", tier=3, is_rumour=0,
             state=storage.STATE_HELD, published_epoch=100, summary_raw=""),
        dict(id=2, title="GTA 6 nightclub interiors shown in new footage",
             url_canonical="https://videogameschronicle.com/b", source_name="VGC",
             source_domain="videogameschronicle.com", tier=2, is_rumour=0,
             state=storage.STATE_NEW, published_epoch=200, summary_raw=""),
    ]
    entries, _ = runner.build_digest_entries(rows, cfg)
    assert len(entries) == 1
    # The tier-2 member is preferred as representative, so attribution goes to
    # the outlet we actually link.
    assert entries[0].source_name == "VGC"


def test_cluster_with_no_postable_member_is_skipped(cfg):
    """A held tier-4 story with no corroboration must not reach the digest."""
    rows = [
        dict(id=1, title="Some unverified GTA 6 claim about vehicles",
             url_canonical="https://unknown.example/a", source_name="Unknown",
             source_domain="unknown.example", tier=4, is_rumour=1,
             state=storage.STATE_HELD, published_epoch=100, summary_raw=""),
    ]
    entries, promoted = runner.build_digest_entries(rows, cfg)
    assert entries == []
    assert promoted == []


# ---------------------------------------------------------------------------
# The duplicate-digest guard must not depend on local storage
# ---------------------------------------------------------------------------
# Real failure, 2026-08-27: commits from the Task Scheduler process were visible
# to that process but never reached the shared database. `digest_runs` stayed
# empty while the digest posted correctly two days running, so the local guard
# was inert and only luck prevented a repeat post every 15 minutes.

def test_channel_guard_detects_our_own_digest():
    from src.discord_client import digest_already_in_channel
    import asyncio, httpx

    payload = [{
        "id": "999", "author": {"bot": True},
        "embeds": [{"title": "GTA 6 — Daily News Digest · 2026-08-27"}],
    }]

    async def _t(monkeypatched_json):
        class Resp:
            status_code = 200
            def json(self): return monkeypatched_json
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return Resp()
        orig = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **k: Client()
        try:
            return await digest_already_in_channel(
                token="t", channel_id="c", date_label="2026-08-27")
        finally:
            httpx.AsyncClient = orig

    found, detail = asyncio.run(_t(payload))
    assert found is True, detail


def test_channel_guard_ignores_a_different_date():
    """Yesterday's digest must not block today's."""
    from src.discord_client import digest_already_in_channel
    import asyncio, httpx

    async def _t():
        class Resp:
            status_code = 200
            def json(self):
                return [{"id": "1", "author": {"bot": True},
                         "embeds": [{"title": "GTA 6 — Daily News Digest · 2026-08-26"}]}]
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return Resp()
        orig = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **k: Client()
        try:
            return await digest_already_in_channel(
                token="t", channel_id="c", date_label="2026-08-27")
        finally:
            httpx.AsyncClient = orig

    found, _ = asyncio.run(_t())
    assert found is False


def test_channel_guard_ignores_messages_from_humans():
    """A member pasting the title must not suppress the real digest."""
    from src.discord_client import digest_already_in_channel
    import asyncio, httpx

    async def _t():
        class Resp:
            status_code = 200
            def json(self):
                return [{"id": "1", "author": {},  # not a bot
                         "embeds": [{"title": "GTA 6 — Daily News Digest · 2026-08-27"}]}]
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return Resp()
        orig = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **k: Client()
        try:
            return await digest_already_in_channel(
                token="t", channel_id="c", date_label="2026-08-27")
        finally:
            httpx.AsyncClient = orig

    found, _ = asyncio.run(_t())
    assert found is False


def test_channel_guard_is_inconclusive_without_credentials():
    """None means 'could not tell', which must be distinguishable from 'no'."""
    from src.discord_client import digest_already_in_channel
    import asyncio
    found, detail = asyncio.run(digest_already_in_channel(
        token=None, channel_id=None, date_label="2026-08-27"))
    assert found is None
    assert "credentials" in detail


def test_channel_guard_is_inconclusive_on_403():
    """Missing READ_MESSAGE_HISTORY must not be read as 'no digest posted'."""
    from src.discord_client import digest_already_in_channel
    import asyncio, httpx

    async def _t():
        class Resp:
            status_code = 403
            text = "Missing Access"
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return Resp()
        orig = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **k: Client()
        try:
            return await digest_already_in_channel(
                token="t", channel_id="c", date_label="2026-08-27")
        finally:
            httpx.AsyncClient = orig

    found, detail = asyncio.run(_t())
    assert found is None
    assert "READ_MESSAGE_HISTORY" in detail


def test_instant_alert_guard_matches_an_existing_title():
    """
    Prevents the 03:00 nightmare: the same first-party story announced and the
    role re-pinged on every run because `sent_instant` never persisted.
    """
    from src.discord_client import title_already_in_channel
    import asyncio, httpx

    async def _t(title):
        class Resp:
            status_code = 200
            def json(self):
                return [{"id": "7", "author": {"bot": True},
                         "embeds": [{"title": "Grand Theft Auto VI: An Extended Look"}]}]
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url): return Resp()
        orig = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **k: Client()
        try:
            return await title_already_in_channel(token="t", channel_id="c", title=title)
        finally:
            httpx.AsyncClient = orig

    found, detail = asyncio.run(_t("Grand Theft Auto VI: An Extended Look"))
    assert found is True, detail
    # Whitespace differences must not defeat it.
    found2, _ = asyncio.run(_t("Grand Theft Auto VI:   An Extended Look"))
    assert found2 is True
    # A genuinely different story must still be announced.
    found3, _ = asyncio.run(_t("Rockstar delays GTA 6 to December"))
    assert found3 is False


def test_instant_alert_guard_is_inconclusive_without_credentials():
    from src.discord_client import title_already_in_channel
    import asyncio
    found, detail = asyncio.run(title_already_in_channel(
        token=None, channel_id=None, title="Grand Theft Auto VI: An Extended Look"))
    assert found is None


def test_instant_alert_guard_refuses_short_titles():
    """A 3-character title would match far too much."""
    from src.discord_client import title_already_in_channel
    import asyncio
    found, detail = asyncio.run(title_already_in_channel(
        token="t", channel_id="c", title="GTA"))
    assert found is None
    assert "too short" in detail
