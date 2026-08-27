"""
Breakout-alert tests.

A breakout alert is the only message the bot can send that pings a whole
community on the strength of coverage volume rather than a first-party source.
Everything here protects that: the guards must hold, and a dry run must not
consume a story that nobody was actually notified about.

The failure to avoid is over-pinging, not under-pinging. Where a guard cannot
prove it is safe to send, the expected behaviour is to decline.
"""
from __future__ import annotations

from src import credibility, digest, runner, storage
from tests.conftest import run

WRAPPER = "https://news.google.com/rss/articles/CBMiOPAQUE"


def _insert(conn, n, **kw):
    """One item in a cluster about the same story, from a distinct outlet."""
    base = dict(
        feed_key="google_news_gta6",
        url_canonical=f"https://outlet{n}.example/rockstar-statement-gta6-leaks",
        url_original=f"https://outlet{n}.example/rockstar-statement-gta6-leaks",
        title="Rockstar issues statement on GTA 6 gameplay leaks calling them heartbreaking",
        title_hash=f"hash-breakout-{n}",
        source_name=f"Outlet {n}",
        source_domain=f"outlet{n}.example",
        published_epoch=None,   # filled in by the caller as "now"
        summary_raw=None,
        tier=2,
        is_rumour=True,
        state=storage.STATE_NEW,
    )
    base.update(kw)
    return storage.insert_item(conn, **base)


def _seed(conn, count, *, now, wrapped=False, title=None):
    async def _s():
        ids = []
        for i in range(count):
            kw = dict(published_epoch=now - 600)
            if wrapped:
                kw["url_canonical"] = WRAPPER + str(i)
                kw["url_original"] = WRAPPER + str(i)
            if title:
                kw["title"] = title
            ids.append(await _insert(conn, i, **kw))
        return ids
    return _s()


def _states(conn, ids):
    async def _q():
        out = []
        for i in ids:
            async with conn.execute("SELECT state FROM items WHERE id = ?", (i,)) as c:
                r = await c.fetchone()
                out.append(r["state"] if r else None)
        return out
    return _q()


# ---------------------------------------------------------------------------
# The threshold
# ---------------------------------------------------------------------------

def test_below_the_outlet_threshold_nothing_fires(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    ids = run(_seed(conn, 3, now=time.time()))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0
    assert details == []
    assert run(_states(conn, ids)) == [storage.STATE_NEW] * 3


def test_at_the_threshold_it_becomes_a_candidate(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    run(_seed(conn, 7, now=time.time()))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0, "dry run must not send"
    assert any("dry-run" in d for d in details), details
    assert any("outlets" in d for d in details), details


def test_setting_zero_disables_the_feature(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "0")
    run(_seed(conn, 20, now=time.time()))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0
    assert "disabled" in details[0]


def test_a_stale_story_does_not_fire(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    monkeypatch.setenv("BREAKOUT_WINDOW_HOURS", "24")
    run(_seed(conn, 8, now=time.time() - 40 * 3600))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0
    assert details == [], "a 40-hour-old story is not breaking news"


# ---------------------------------------------------------------------------
# The guards
# ---------------------------------------------------------------------------

def test_a_fully_wrapped_cluster_is_skipped(conn, cfg, monkeypatch):
    """
    Every link is a Google News redirect, which lands on a consent wall. That
    is tolerable on a web page and not tolerable in a push notification.
    """
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    ids = run(_seed(conn, 8, now=time.time(), wrapped=True))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0
    assert any("no publisher URL" in d for d in details), details
    assert run(_states(conn, ids)) == [storage.STATE_NEW] * 8


def test_a_crude_headline_is_never_pinged(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    run(_seed(conn, 8, now=time.time(),
              title="Latest GTA 6 leak confirms full dong and other details"))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=True, health_line="t"))
    assert sent == 0
    assert any("not pinged" in d for d in details), details


def test_an_ordinary_headline_is_not_caught_by_the_crude_filter():
    # The filter must stay narrow; eating real stories is the worse failure.
    for ok in [
        "Rockstar reveals a swathe of new GTA 6 details ahead of the trailer",
        "GTA 6 delayed again, Take-Two confirms November 2026 window",
        "Every activity we've spotted in GTA 6's extended look trailer",
    ]:
        assert not runner._CRUDE_RE.search(ok), ok


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_the_alert_is_countable_and_pings_only_the_role():
    entry = digest.DigestEntry(
        item_id=1, title="Rockstar issues statement on GTA 6 gameplay leaks",
        url="https://videogameschronicle.com/news/x", source_name="VGC",
        label=credibility.LABEL_RUMOUR, other_outlets=["IGN", "Kotaku"],
    )
    p = digest.render_breakout_alert(entry, role_id="99", outlet_count=26,
                                     health_line=None)
    author = p["embeds"][0]["author"]["name"]
    assert author.startswith(digest.BREAKOUT_MARKER), (
        "the channel-side rate limit counts messages by this prefix")
    assert "26 outlets" in author
    assert p["allowed_mentions"] == {
        "parse": [], "roles": ["99"], "users": [], "replied_user": False,
    }, "a breakout must never be able to mention @everyone"


def test_a_rumour_breakout_says_rumour_before_the_headline_detail():
    entry = digest.DigestEntry(
        item_id=1, title="Leaker posts extended GTA 6 gameplay",
        url="https://pcgamer.com/x", source_name="PC Gamer",
        label=credibility.LABEL_RUMOUR,
    )
    desc = digest.render_breakout_alert(
        entry, role_id=None, outlet_count=9)["embeds"][0]["description"]
    assert desc.lstrip().startswith(digest._LABEL_PREFIX[credibility.LABEL_RUMOUR]), (
        "a leak-sourced alert must be labelled where it cannot be missed")


def test_no_role_means_no_content_and_no_role_mention():
    entry = digest.DigestEntry(
        item_id=1, title="GTA 6 news", url="https://vgc.com/x",
        source_name="VGC", label=credibility.LABEL_REPORT,
    )
    p = digest.render_breakout_alert(entry, role_id=None, outlet_count=7)
    assert "content" not in p
    assert p["allowed_mentions"]["roles"] == []


# ---------------------------------------------------------------------------
# The rate limit
#
# It lives in the channel, not in SQLite, because scheduled writes do not
# reliably persist on the deployment machine and a per-run cap would still
# permit four pings an hour on a 15-minute schedule.
# ---------------------------------------------------------------------------

def test_the_counter_cannot_answer_without_credentials():
    from src import discord_client
    count, detail = run(discord_client.count_recent_marked_alerts(
        token="", channel_id="", marker=digest.BREAKOUT_MARKER,
        within_seconds=3600))
    assert count is None
    assert "credentials" in detail


def _fake_counter(monkeypatch, *values):
    """Script successive count_recent_marked_alerts() answers."""
    from src import discord_client
    seq = list(values)

    async def fake(**kw):
        return seq.pop(0) if seq else (0, "exhausted")
    monkeypatch.setattr(discord_client, "count_recent_marked_alerts", fake)


def test_it_declines_to_send_when_the_rate_limit_is_unverifiable(
        conn, cfg, monkeypatch):
    """An unbounded ping is worse than a late one."""
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    ids = run(_seed(conn, 8, now=time.time()))
    _fake_counter(monkeypatch, (None, "cannot read channel history (403)"))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=False, health_line="t"))
    assert sent == 0
    assert any("unverifiable" in d for d in details), details
    assert run(_states(conn, ids)) == [storage.STATE_NEW] * 8, (
        "declining must not consume the story")


def test_the_daily_cap_stops_further_alerts(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    monkeypatch.setenv("BREAKOUT_MAX_PER_DAY", "3")
    run(_seed(conn, 8, now=time.time()))
    _fake_counter(monkeypatch, (3, "3 in the last 1440 min"))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=False, health_line="t"))
    assert sent == 0
    assert any("daily cap" in d for d in details), details


def test_the_cooldown_stops_a_second_alert_too_soon(conn, cfg, monkeypatch):
    import time
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    monkeypatch.setenv("BREAKOUT_MAX_PER_DAY", "3")
    monkeypatch.setenv("BREAKOUT_COOLDOWN_MINUTES", "60")
    run(_seed(conn, 8, now=time.time()))
    # under the daily cap, but one went out inside the cooldown window
    _fake_counter(monkeypatch, (1, "1 in the last 1440 min"),
                  (1, "1 in the last 60 min"))
    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=False, health_line="t"))
    assert sent == 0
    assert any("cooldown" in d for d in details), details


# ---------------------------------------------------------------------------
# The digest interlock exception
# ---------------------------------------------------------------------------

def test_a_breakout_alert_leaves_the_story_in_the_digest_pool(
        conn, cfg, monkeypatch):
    """
    Unlike an instant alert, a breakout must NOT consume its cluster.

    The state machine excludes sent items from the evening digest. For a
    one-off first-party announcement that is right. For a breakout it would
    delete the day's biggest story from the day's record.
    """
    import time
    from src import discord_client
    monkeypatch.setenv("BREAKOUT_MIN_OUTLETS", "6")
    monkeypatch.setenv("POSTING_ENABLED", "true")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("DISCORD_NEWS_CHANNEL_ID", "123")

    ids = run(_seed(conn, 8, now=time.time()))
    _fake_counter(monkeypatch, (0, "0 in the last 1440 min"),
                  (0, "0 in the last 60 min"))

    async def not_seen(**kw):
        return False, "not found"
    monkeypatch.setattr(discord_client, "title_already_in_channel", not_seen)

    class _Result:
        sent, dry_run, detail = True, False, "ok"

    async def fake_post(*a, **kw):
        return _Result()
    monkeypatch.setattr(discord_client, "post_message", fake_post)

    sent, details = run(runner.send_breakout_alerts(
        conn, cfg, dry_run=False, health_line="t"))

    assert sent == 1, details
    assert run(_states(conn, ids)) == [storage.STATE_NEW] * 8, (
        "the breakout consumed the story; it would be missing from the digest")
