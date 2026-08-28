"""
Message rendering tests.

Two classes of bug these prevent:

  * a 400 from Discord, which rejects the ENTIRE message with no truncation, so
    a single over-long digest means no digest at all;
  * an accidental @everyone. Bot messages (unlike webhooks) default to parsing
    EVERYTHING including @everyone, so a missing allowed_mentions block is a
    latent mass-ping waiting for a headline that happens to contain "@everyone".
"""
from __future__ import annotations

import pytest

from src import credibility
from src.digest import (
    CONTENT_MAX,
    EMBED_DESC_MAX,
    EMBED_TITLE_MAX,
    EMBED_TOTAL_MAX,
    DigestEntry,
    assert_within_limits,
    embed_total_chars,
    render_digest,
    render_instant_alert,
)


def entry(i: int, *, label=credibility.LABEL_REPORT, title=None, summary=None) -> DigestEntry:
    return DigestEntry(
        item_id=i,
        title=title or f"GTA 6 story number {i} with a reasonably long headline",
        url=f"https://example.com/story-{i}",
        source_name="VGC",
        label=label,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# allowed_mentions — the @everyone guard
# ---------------------------------------------------------------------------

def test_digest_never_pings_anything():
    p = render_digest([entry(1)], health_line="10 feeds · 10 ok", date_label="2026-08-25")
    am = p["allowed_mentions"]
    assert am["parse"] == []
    assert am["roles"] == []
    assert am["users"] == []


def test_instant_alert_pings_exactly_one_role():
    p = render_instant_alert(entry(1, label=credibility.LABEL_OFFICIAL), role_id="99887766")
    am = p["allowed_mentions"]
    assert am["parse"] == []
    assert am["roles"] == ["99887766"]
    assert p["content"].startswith("<@&99887766> ")


def test_the_alert_content_carries_the_headline():
    """
    Discord builds the mobile push notification and the channel preview from
    `content` alone; embed titles are not included. content used to be nothing
    but the role mention, so the one message type meant to wake the community
    arrived on a phone as a ping with no words in it.
    """
    e = entry(1, label=credibility.LABEL_OFFICIAL)
    for p in (render_instant_alert(e, role_id="99887766"),
              render_instant_alert(e, role_id=None)):
        assert e.title in p["content"], p["content"]


def test_instant_alert_without_role_does_not_ping():
    p = render_instant_alert(entry(1, label=credibility.LABEL_OFFICIAL), role_id=None)
    assert p["allowed_mentions"]["roles"] == []
    # It still carries words, so the channel preview is readable -- but it must
    # mention nothing at all.
    assert "<@&" not in p["content"]


def test_missing_allowed_mentions_is_rejected():
    with pytest.raises(ValueError, match="allowed_mentions missing"):
        assert_within_limits({"embeds": [{"title": "x"}]})


def test_non_empty_parse_is_rejected():
    """parse: ['everyone'] must never ship, even if someone adds it deliberately."""
    with pytest.raises(ValueError, match=r"allowed_mentions.parse must be"):
        assert_within_limits({
            "embeds": [{"title": "x"}],
            "allowed_mentions": {"parse": ["everyone"], "roles": [], "users": []},
        })


def test_headline_containing_everyone_cannot_ping():
    """
    The real accident: a scraped headline containing @everyone. The explicit
    parse: [] block neutralises it even though the text is rendered verbatim.
    """
    p = render_digest(
        [entry(1, title="Rockstar thanks @everyone for their patience")],
        health_line="ok", date_label="2026-08-25",
    )
    assert "@everyone" in p["embeds"][0]["description"]
    assert p["allowed_mentions"]["parse"] == []


# ---------------------------------------------------------------------------
# Size limits
# ---------------------------------------------------------------------------

def test_many_long_entries_stay_within_total_budget():
    """
    The 6000-total ceiling is the one that actually bites: per-field limits are
    generous, so a naive renderer passes every individual check and still 400s.
    """
    long_summary = "x" * 400
    entries = [entry(i, summary=long_summary) for i in range(40)]
    p = render_digest(entries, health_line="10 feeds · 10 ok", date_label="2026-08-25",
                      max_items=40)
    assert_within_limits(p)
    assert embed_total_chars(p) <= EMBED_TOTAL_MAX
    assert len(p["embeds"][0]["description"]) <= EMBED_DESC_MAX


def test_omitted_count_is_not_rendered_by_default():
    """
    The "+N more not shown" line was removed: after clustering the overflow is
    dozens of lower-ranked stories, and "+82 more" tells a reader nothing.
    """
    entries = [entry(i, summary="y" * 400) for i in range(40)]
    p = render_digest(entries, health_line="ok", date_label="2026-08-25", max_items=40)
    assert "more item" not in p["embeds"][0]["description"]


def test_omitted_count_can_be_reenabled(monkeypatch):
    monkeypatch.setenv("DIGEST_SHOW_OMITTED_COUNT", "true")
    entries = [entry(i, summary="y" * 400) for i in range(40)]
    p = render_digest(entries, health_line="ok", date_label="2026-08-25", max_items=40)
    assert "more item" in p["embeds"][0]["description"]


def test_omitted_entries_are_reported_so_the_caller_can_roll_them_over():
    """
    Nothing is lost by hiding the count: select_entries still reports what was
    omitted, the caller marks only what was rendered, and the rest compete
    again tomorrow. That — not a cosmetic line — is the real safety property.
    """
    from src.digest import select_entries
    entries = [entry(i, summary="y" * 400) for i in range(40)]
    rendered, omitted = select_entries(entries, health_line="ok",
                                       date_label="2026-08-25", max_items=40)
    assert omitted > 0
    assert len(rendered) + omitted == len(entries)


def test_max_items_cap_is_honoured():
    entries = [entry(i) for i in range(30)]
    p = render_digest(entries, health_line="ok", date_label="2026-08-25", max_items=5)
    desc = p["embeds"][0]["description"]
    assert desc.count("https://example.com/story-") == 5


def test_absurdly_long_title_is_truncated():
    p = render_digest([entry(1, title="G" * 5000)], health_line="ok", date_label="2026-08-25")
    assert_within_limits(p)
    assert len(p["embeds"][0]["title"]) <= EMBED_TITLE_MAX


def test_single_embed_is_used_not_many():
    """One embed with many lines, deliberately — ten embeds breach 6000 fast."""
    p = render_digest([entry(i) for i in range(8)], health_line="ok", date_label="2026-08-25")
    assert len(p["embeds"]) == 1


def test_too_many_embeds_is_rejected():
    payload = {
        "embeds": [{"title": f"e{i}"} for i in range(11)],
        "allowed_mentions": {"parse": [], "roles": [], "users": []},
    }
    with pytest.raises(ValueError, match="too many embeds"):
        assert_within_limits(payload)


def test_over_budget_payload_is_rejected():
    payload = {
        "embeds": [{"description": "z" * 3500}, {"description": "z" * 3500}],
        "allowed_mentions": {"parse": [], "roles": [], "users": []},
    }
    with pytest.raises(ValueError, match="total embed characters"):
        assert_within_limits(payload)


# ---------------------------------------------------------------------------
# Content and labelling
# ---------------------------------------------------------------------------

def test_empty_digest_still_posts_with_health_line():
    """
    'No news today' and 'the bot is dead' must look different to a reader.
    The health line is what distinguishes them.
    """
    p = render_digest([], health_line="10 feeds · 9 ok · 1 failing: rockstar_newswire (403)",
                      date_label="2026-08-25")
    assert_within_limits(p)
    assert "No items cleared" in p["embeds"][0]["description"]
    assert "1 failing" in p["embeds"][0]["footer"]["text"]


def test_health_line_is_always_in_the_footer():
    p = render_digest([entry(1)], health_line="SENTINEL_HEALTH", date_label="2026-08-25")
    assert "SENTINEL_HEALTH" in p["embeds"][0]["footer"]["text"]


def test_rumour_label_is_visible_to_readers():
    p = render_digest([entry(1, label=credibility.LABEL_RUMOUR)],
                      health_line="ok", date_label="2026-08-25")
    assert "Rumour" in p["embeds"][0]["description"]


def test_official_and_rumour_render_differently():
    off = render_digest([entry(1, label=credibility.LABEL_OFFICIAL)],
                        health_line="ok", date_label="2026-08-25")
    rum = render_digest([entry(1, label=credibility.LABEL_RUMOUR)],
                        health_line="ok", date_label="2026-08-25")
    assert off["embeds"][0]["description"] != rum["embeds"][0]["description"]
    assert off["embeds"][0]["color"] != rum["embeds"][0]["color"]


def test_brackets_in_headline_cannot_break_the_masked_link():
    """An unbalanced ] would terminate the link early and leak a raw URL."""
    p = render_digest([entry(1, title="GTA 6 [UPDATE] thing")],
                      health_line="ok", date_label="2026-08-25")
    desc = p["embeds"][0]["description"]
    assert "[GTA 6 (UPDATE) thing](https://example.com/story-1)" in desc


def test_source_name_is_always_shown():
    """Attribution to the reporting outlet is an editorial requirement."""
    p = render_digest([entry(1)], health_line="ok", date_label="2026-08-25")
    assert "VGC" in p["embeds"][0]["description"]


def test_content_limit_enforced():
    with pytest.raises(ValueError, match="content exceeds"):
        assert_within_limits({
            "content": "c" * (CONTENT_MAX + 1),
            "embeds": [],
            "allowed_mentions": {"parse": [], "roles": [], "users": []},
        })


# ---------------------------------------------------------------------------
# Permission maths (verified against docs.discord.com 2026-08-26)
# ---------------------------------------------------------------------------

def test_invite_integer_is_least_privilege():
    from src import discord_setup as ds
    perms = ds.minimal_permissions()
    assert perms == 19488, "invite integer changed; re-verify against Discord docs"
    names = set(ds.decode_permissions(perms))
    assert names == {"VIEW_CHANNEL", "SEND_MESSAGES", "EMBED_LINKS", "MANAGE_GUILD"}
    # The dangerous ones must never be in the guild-level invite.
    assert "ADMINISTRATOR" not in names
    assert "MENTION_EVERYONE" not in names, (
        "MENTION_EVERYONE must be a per-channel overwrite, not a guild-wide grant"
    )


def test_automod_can_be_dropped_from_the_invite():
    from src import discord_setup as ds
    assert ds.minimal_permissions(manage_automod=False) == 19456
    assert "MANAGE_GUILD" not in ds.decode_permissions(
        ds.minimal_permissions(manage_automod=False))


def test_bot_channel_overwrite_includes_mention_but_invite_does_not():
    from src import discord_setup as ds
    allow = ds.bot_channel_allow()
    assert allow == 216064
    assert "MENTION_EVERYONE" in ds.decode_permissions(allow)


def test_everyone_news_deny_covers_threads():
    """
    SEND_MESSAGES is NOT inherited by threads, so denying it alone still lets a
    member drop a leaked clip into a thread on the bot's own digest post.
    """
    from src import discord_setup as ds
    deny = ds.everyone_news_deny()
    assert deny & ds.PERMS["SEND_MESSAGES"]
    assert deny & ds.PERMS["SEND_MESSAGES_IN_THREADS"]
    assert deny & (1 << 35)  # CREATE_PUBLIC_THREADS
    assert deny & (1 << 36)  # CREATE_PRIVATE_THREADS


def test_everyone_keeps_read_access():
    from src import discord_setup as ds
    allow = ds.everyone_news_allow()
    assert set(ds.decode_permissions(allow)) == {"VIEW_CHANNEL", "READ_MESSAGE_HISTORY"}
    assert allow & ds.everyone_news_deny() == 0, "a permission must not be both allowed and denied"


def test_server_media_deny_is_embed_plus_attach():
    from src import discord_setup as ds
    assert ds.SERVER_MEDIA_DENY == 49152


def test_permission_resolution_member_overwrite_beats_role_deny():
    """
    Discord applies the member overwrite LAST. Getting that order wrong would
    make discord-doctor report a working setup as broken.
    """
    from src import discord_setup as ds
    perms = ds.compute_channel_permissions(
        guild_id="100",
        everyone_perms=ds.PERMS["VIEW_CHANNEL"],
        member_role_perms=[0],
        member_role_ids={"200"},
        bot_user_id="999",
        overwrites=[
            {"id": "100", "type": 0, "allow": "0", "deny": str(ds.PERMS["SEND_MESSAGES"])},
            {"id": "200", "type": 0, "allow": "0", "deny": str(ds.PERMS["SEND_MESSAGES"])},
            {"id": "999", "type": 1, "allow": str(ds.PERMS["SEND_MESSAGES"]), "deny": "0"},
        ],
    )
    assert perms & ds.PERMS["SEND_MESSAGES"], "member allow must beat both role denies"


def test_permission_resolution_administrator_short_circuits():
    from src import discord_setup as ds
    perms = ds.compute_channel_permissions(
        guild_id="100",
        everyone_perms=ds.PERMS["ADMINISTRATOR"],
        member_role_perms=[],
        member_role_ids=set(),
        bot_user_id="999",
        overwrites=[{"id": "100", "type": 0, "allow": "0",
                     "deny": str(ds.PERMS["SEND_MESSAGES"])}],
    )
    assert perms & ds.PERMS["SEND_MESSAGES"], "ADMINISTRATOR ignores channel denies"


def test_permission_overwrites_accept_string_bitfields():
    """API v8+ serialises permissions as strings; ints must also not crash."""
    from src import discord_setup as ds
    for value in ("2048", 2048):
        perms = ds.compute_channel_permissions(
            guild_id="1", everyone_perms=0, member_role_perms=[],
            member_role_ids=set(), bot_user_id="9",
            overwrites=[{"id": "9", "type": 1, "allow": value, "deny": "0"}],
        )
        assert perms & ds.PERMS["SEND_MESSAGES"]


# ---------------------------------------------------------------------------
# Attribution injection + rendered/marked agreement
# ---------------------------------------------------------------------------

def test_attribution_cannot_inject_a_masked_link():
    """
    source_name comes from unvalidated feed metadata. Interpolated raw beside a
    masked link, `x](https://evil)` closes ours and opens theirs — turning a
    text field into a clickable destination on the line readers most trust.
    """
    from src.digest import sanitise_attribution
    evil = "IGN](https://evil.example) and more"
    out = sanitise_attribution(evil)
    assert "](" not in out
    assert "https://" not in out


def test_attribution_strips_urls_and_brackets():
    from src.digest import sanitise_attribution
    assert "[" not in sanitise_attribution("Weird [Outlet]")
    assert "evil" not in sanitise_attribution("Outlet https://evil.example/x")
    assert sanitise_attribution("VGC") == "VGC"
    assert sanitise_attribution("") == ""


def test_injected_source_name_does_not_reach_the_rendered_line():
    p = render_digest(
        [DigestEntry(1, "A real headline", "https://good.example/a",
                     "IGN](https://evil.example)", credibility.LABEL_REPORT)],
        health_line="ok", date_label="2026-08-26")
    desc = p["embeds"][0]["description"]
    assert "evil.example" not in desc


def test_injected_source_name_is_neutralised_in_instant_alerts():
    p = render_instant_alert(
        DigestEntry(1, "Official thing", "https://good.example/a",
                    "Rockstar](https://evil.example)", credibility.LABEL_OFFICIAL),
        role_id=None)
    blob = p["embeds"][0]["description"] + p["embeds"][0]["author"]["name"]
    assert "evil.example" not in blob


def test_select_entries_matches_what_render_includes():
    """
    The caller marks published items as sent_digest, which is terminal. If it
    marked more than was rendered, a real story would be deleted unseen.
    """
    from src.digest import select_entries
    entries = [entry(i, summary="z" * 400) for i in range(40)]
    rendered, omitted = select_entries(entries, health_line="ok",
                                       date_label="2026-08-26", max_items=40)
    p = render_digest(entries, health_line="ok", date_label="2026-08-26", max_items=40)
    desc = p["embeds"][0]["description"]
    for e in rendered:
        assert e.url in desc, "select_entries claimed an entry the payload omits"
    assert len(rendered) + omitted == len(entries)


def test_nothing_is_marked_when_everything_is_dropped():
    from src.digest import select_entries
    huge = [entry(1, summary="q" * 5000)]
    rendered, omitted = select_entries(huge, health_line="ok", date_label="2026-08-26")
    assert len(rendered) + omitted == 1


def test_legitimate_parentheses_survive_sanitising():
    """
    "Rockstar Games (YouTube)" must render intact. An earlier version replaced
    parens with lookalike glyphs, mangling the name on every instant alert. A
    bare paren cannot terminate link text — only `](` can, and `]` is handled.
    """
    from src.digest import sanitise_attribution
    assert sanitise_attribution("Rockstar Games (YouTube)") == "Rockstar Games (YouTube)"
    assert sanitise_attribution("GamesRadar+") == "GamesRadar+"


def test_bracket_url_injection_is_still_blocked_with_parens_allowed():
    """Relaxing parens must not reopen the escape hatch."""
    from src.digest import sanitise_attribution
    out = sanitise_attribution("IGN](https://evil.example)")
    assert "](" not in out
    assert "https://" not in out
    assert "evil" not in out


def test_managed_role_is_rejected_as_a_ping_target():
    """
    Inviting a bot auto-creates a MANAGED role named after it, sorted next to
    real roles — easy to copy by mistake. Discord will not let a human hold it,
    so a ping reaches nobody and reports no error.
    """
    from src import discord_setup as ds
    role = {"id": "1", "name": "GTA newsbot", "managed": True,
            "mentionable": False, "tags": {"bot_id": "9"}}
    assert role.get("managed") is True
    # The real opt-in role must not be flagged.
    ok_role = {"id": "2", "name": "GTA VI news", "managed": False,
               "mentionable": False, "tags": {}}
    assert not ok_role.get("managed")
    assert ds.PERMS["MENTION_EVERYONE"] == 131072


# ---------------------------------------------------------------------------
# Staleness must be visible
#
# Nothing in the digest carried a date, so a 30-hour-old story read exactly like
# one from this afternoon. On a day dominated by one event that mattered: several
# slots were "when to watch" pieces for a stream that had already aired.
# ---------------------------------------------------------------------------

def test_a_story_with_a_timestamp_renders_a_relative_stamp():
    e = entry(1)
    e.published = 1_787_000_000
    desc = render_digest([e], health_line="h", date_label="2026-08-27")["embeds"][0]["description"]
    assert "<t:1787000000:R>" in desc, (
        "Discord's <t:N:R> localises per reader; a fixed string cannot")


def test_a_story_without_a_timestamp_renders_no_stamp_and_no_stray_separator():
    e = entry(1)
    e.published = None
    desc = render_digest([e], health_line="h", date_label="2026-08-27")["embeds"][0]["description"]
    assert "<t:" not in desc
    assert "· ·" not in desc, "an empty timestamp left a dangling separator"


# ---------------------------------------------------------------------------
# The digest must never hand a member an aggregator redirect
#
# The web edition got this rule first and the digest was left behind — the
# surface where a bad link costs most, since it is a tap on a phone rather than
# a click on a page. Both now share canonical.link_target().
# ---------------------------------------------------------------------------

def test_an_unlinkable_story_renders_unlinked_rather_than_badly_linked():
    e = entry(1)
    e.url = ""
    desc = render_digest([e], health_line="h", date_label="d")["embeds"][0]["description"]
    assert e.title in desc, "the headline must survive even with no link"
    assert "](" not in desc, "rendered a markdown link with no destination"


def test_a_front_page_fallback_says_so():
    e = entry(1)
    e.url = "https://ign.com/"
    e.homepage_link = True
    desc = render_digest([e], health_line="h", date_label="d")["embeds"][0]["description"]
    assert "(front page)" in desc, (
        "a homepage link must not pose as a link to the article")


def test_the_shared_link_rule_is_the_one_the_web_edition_uses():
    from src import canonical
    assert canonical.link_target("https://news.google.com/rss/articles/X",
                                 tier=2, domain="ign.com") == ("https://ign.com/", True)
    assert canonical.link_target("https://news.google.com/rss/articles/X",
                                 tier=9, domain="unknown.example") == ("", False)
    assert canonical.link_target("https://ign.com/articles/x",
                                 tier=2, domain="ign.com") == ("https://ign.com/articles/x", False)
