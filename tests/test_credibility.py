"""
Credibility engine tests.

These encode the operator's editorial rule as executable policy:

    We may describe what a leak CLAIMS, as rumour only. Never linked, never
    reuploaded, always attributed to the journalism that reported it.

The most important test in this file is
`test_leak_derived_is_capped_at_rumour_even_from_tier_1` — if that ever passes
POST_AS_FACT, the bot has started asserting leaks as confirmed fact.
"""
from __future__ import annotations

from src import credibility as cred


def judge(cfg, **kw):
    base = dict(
        title="GTA 6 news", summary="", domain="ign.com",
        url="https://ign.com/a", feed_tier=2, cfg=cfg,
    )
    base.update(kw)
    return cred.judge(**base)


# ---------------------------------------------------------------------------
# Relevance
# ---------------------------------------------------------------------------

def test_irrelevant_items_are_dropped(cfg):
    v = judge(cfg, title="The Witcher 4 gets a release window")
    assert v.decision == cred.DROP
    assert "not GTA-related" in v.reasons


def test_gta6_item_is_relevant(cfg):
    assert cred.is_relevant("Grand Theft Auto VI delayed to November")
    assert cred.is_relevant("Rockstar Games announces something")
    assert not cred.is_relevant("Paradox announces grand strategy game")


def test_core_vs_adjacent(cfg):
    assert cred.is_core_gta6("GTA 6 trailer drops")
    assert not cred.is_core_gta6("FiveM for GTA V Enhanced released")


# ---------------------------------------------------------------------------
# Tiering
# ---------------------------------------------------------------------------

def test_tier1_official_posts_as_fact(cfg):
    v = judge(cfg, title="Grand Theft Auto VI launches November 19",
              domain="rockstargames.com", feed_tier=1)
    assert v.decision == cred.POST_AS_FACT
    assert v.label == cred.LABEL_OFFICIAL


def test_tier2_posts_as_report(cfg):
    v = judge(cfg, title="Take-Two reiterates GTA 6 November launch",
              domain="videogameschronicle.com", feed_tier=2)
    assert v.decision == cred.POST_AS_FACT
    assert v.label == cred.LABEL_REPORT


def test_worse_of_domain_and_feed_tier_wins(cfg):
    """A tier-3 story surfacing through a tier-2 feed is still tier 3."""
    v = judge(cfg, title="GTA 6 map detail spotted", domain="gtaboom.com", feed_tier=2)
    assert v.tier == 3


def test_unknown_domain_defaults_to_tier4(cfg):
    v = judge(cfg, title="GTA 6 something happens", domain="random-blog-xyz.example",
              feed_tier=2)
    assert v.tier == 4
    assert v.decision == cred.HOLD


def test_subdomain_does_not_inherit_parent_tier(cfg):
    """
    eduadmin.fortune.com must not inherit any tier from fortune.com. It is on
    the blocked list, so it should be dropped outright.
    """
    v = judge(cfg, title="GTA 6 leak reveals map",
              domain="eduadmin.fortune.com", url="https://eduadmin.fortune.com/gta6")
    assert v.decision == cred.DROP
    assert any("blocked domain" in r for r in v.reasons)


# ---------------------------------------------------------------------------
# The editorial rule
# ---------------------------------------------------------------------------

def test_leak_derived_is_capped_at_rumour_from_tier2(cfg):
    v = judge(cfg, title="GTA 6 leaked gameplay shows new mechanics",
              domain="videogameschronicle.com", feed_tier=2)
    assert v.decision == cred.POST_AS_RUMOUR
    assert v.label == cred.LABEL_RUMOUR
    assert v.is_leak_derived is True
    assert any("capped at rumour" in r for r in v.reasons)


def test_leak_derived_is_capped_at_rumour_even_from_tier_1(cfg):
    """
    THE critical invariant. A first-party post that discusses a leak must still
    be labelled rumour — Rockstar acknowledging a leak exists does not confirm
    what the leak claims.
    """
    v = judge(cfg, title="Rockstar responds to leaked GTA 6 footage",
              domain="rockstargames.com", feed_tier=1)
    assert v.decision == cred.POST_AS_RUMOUR
    assert v.label == cred.LABEL_RUMOUR
    assert v.decision != cred.POST_AS_FACT


def test_hedged_language_becomes_rumour(cfg):
    v = judge(cfg, title="GTA 6 reportedly features a karma system",
              domain="pcgamer.com", feed_tier=2)
    assert v.decision == cred.POST_AS_RUMOUR
    assert v.is_rumour is True
    assert v.is_leak_derived is False


def test_corroboration_promotes_tier4(cfg):
    held = judge(cfg, title="GTA 6 rumour about vehicles", domain="unknown-site.example",
                 feed_tier=4, tier2_corroborations=0)
    assert held.decision == cred.HOLD

    promoted = judge(cfg, title="GTA 6 rumour about vehicles", domain="unknown-site.example",
                     feed_tier=4, tier2_corroborations=2)
    assert promoted.decision == cred.POST_AS_RUMOUR
    assert any("never to the tier-4 origin" in r for r in promoted.reasons)


def test_one_corroboration_is_not_enough_for_tier4(cfg):
    v = judge(cfg, title="GTA 6 rumour about vehicles", domain="unknown-site.example",
              feed_tier=4, tier2_corroborations=1)
    assert v.decision == cred.HOLD


def test_tier3_needs_one_corroboration(cfg):
    held = judge(cfg, title="GTA 6 detail found", domain="rockstarintel.com", feed_tier=3)
    assert held.decision == cred.HOLD
    ok = judge(cfg, title="GTA 6 detail found", domain="rockstarintel.com",
               feed_tier=3, tier2_corroborations=1)
    assert ok.postable


# ---------------------------------------------------------------------------
# Fabrication defence
# ---------------------------------------------------------------------------

def test_blocked_handle_is_dropped(cfg):
    v = judge(cfg, title="GTA 6 gameplay from cyberleek_ar_io",
              url="https://x.com/cyberleek_ar_io/status/1", domain="x.com", feed_tier=4)
    assert v.decision == cred.DROP
    assert any("blocked account" in r for r in v.reasons)


def test_blocked_subreddit_is_dropped(cfg):
    v = judge(cfg, title="GTA 6 leak megathread",
              url="https://reddit.com/r/GTA6Unmoderated/comments/x", domain="reddit.com",
              feed_tier=4)
    assert v.decision == cred.DROP


def test_parasite_seo_domain_is_dropped(cfg):
    v = judge(cfg, title="GTA 6 map leak everything we know",
              url="https://widescope.stanford.edu/gta6", domain="widescope.stanford.edu",
              feed_tier=4)
    assert v.decision == cred.DROP


def test_contradicting_established_fact_is_dropped(cfg):
    """Perennial fake: a delay that did not happen."""
    v = judge(cfg, title="GTA 6 delayed to 2027, Rockstar confirms",
              domain="gamerant.com", feed_tier=3)
    assert v.decision == cred.DROP
    assert any("contradicts established fact" in r for r in v.reasons)


def test_fake_switch2_claim_is_dropped(cfg):
    v = judge(cfg, title="GTA 6 coming to Nintendo Switch 2",
              domain="thegamer.com", feed_tier=3)
    assert v.decision == cred.DROP


def test_official_release_date_is_not_treated_as_contradiction(cfg):
    """The true date must survive — the contradiction check must not be trigger-happy."""
    v = judge(cfg, title="Grand Theft Auto VI launches November 19, 2026",
              domain="rockstargames.com", feed_tier=1)
    assert v.decision == cred.POST_AS_FACT


def test_clickbait_reduces_score(cfg):
    plain = judge(cfg, title="GTA 6 pre-orders open", domain="pcgamer.com", feed_tier=2)
    bait = judge(cfg, title="GTA 6 everything we know so far", domain="pcgamer.com",
                 feed_tier=2)
    assert bait.score < plain.score


def test_all_caps_headline_reduces_score(cfg):
    normal = judge(cfg, title="Rockstar confirms GTA 6 launch date again",
                   domain="pcgamer.com", feed_tier=2)
    shouty = judge(cfg, title="ROCKSTAR CONFIRMS GTA 6 LAUNCH DATE AGAIN",
                   domain="pcgamer.com", feed_tier=2)
    assert shouty.score < normal.score


# ---------------------------------------------------------------------------
# Config integrity
# ---------------------------------------------------------------------------

def test_config_has_required_sections(cfg):
    for key in ("feeds", "domain_tiers", "blocked_domains", "blocked_handles",
                "leak_keywords", "factual_baseline", "corroboration"):
        assert key in cfg, f"config missing {key}"


def test_every_feed_has_required_fields(cfg):
    for f in cfg["feeds"]:
        for field in ("key", "name", "url", "tier", "instant", "poll_seconds", "verified"):
            assert field in f, f"feed {f.get('key')} missing {field}"
        assert f["verified"] in ("live", "blocked", "untested")


def test_feed_keys_are_unique(cfg):
    keys = [f["key"] for f in cfg["feeds"]]
    assert len(keys) == len(set(keys))


def test_blocked_feed_is_disabled(cfg):
    """A feed known to 403 must not be left enabled to fail every 15 minutes."""
    for f in cfg["feeds"]:
        if f["verified"] == "blocked":
            assert f.get("enabled", True) is False, f"{f['key']} is blocked but still enabled"


def test_instant_feeds_are_tier1(cfg):
    """Instant alerts are reserved for first-party sources."""
    for f in cfg["feeds"]:
        if f.get("instant"):
            assert int(f["tier"]) == 1, f"{f['key']} is instant but tier {f['tier']}"


# ---------------------------------------------------------------------------
# Contradiction check: assertion vs negation
# ---------------------------------------------------------------------------
# The first implementation matched "most words of a known-false claim co-occur",
# which made it a topic detector. Measured against real headlines it dropped 8
# of 8 probes including four TRUE stories. Dropping is destructive and
# irreversible, so these tests pin BOTH directions.

TRUE_OR_REPORTING = [
    "Rockstar confirms GTA 6 is NOT delayed, still launching November 19",
    "GTA 6 will not be delayed to 2027, Take-Two says",
    "Why GTA 6 was delayed to November 2026",
    "No, GTA 6 is still not coming to the Nintendo Switch 2",
    "GTA 6 PC version still not confirmed, Rockstar silent",
    "Rockstar issues statement on GTA 6 gameplay leaks",
    "Grand Theft Auto VI: An Extended Look premieres August 27",
]

GENUINE_FAKES = [
    "GTA 6 delayed to 2027, Rockstar confirms",
    "GTA 6 is coming to Switch 2",
    "GTA 6 PC version confirmed for launch day",
]


def test_true_and_reporting_headlines_are_never_dropped(cfg):
    """A true story deleted is gone forever; a fake that survives is merely labelled."""
    for title in TRUE_OR_REPORTING:
        assert cred.contradicts_baseline(title, "", cfg) is None, (
            f"dropped a true/reporting headline: {title!r}"
        )


def test_genuine_fakes_are_still_caught(cfg):
    for title in GENUINE_FAKES:
        assert cred.contradicts_baseline(title, "", cfg) is not None, (
            f"failed to catch a known fake: {title!r}"
        )


def test_negation_anywhere_vetoes_the_drop(cfg):
    """The error direction is deliberate: keep and label, rather than delete."""
    assert cred.contradicts_baseline("GTA 6 delayed to 2028", "", cfg) is not None
    assert cred.contradicts_baseline(
        "GTA 6 delayed to 2028? That rumour is false", "", cfg) is None


def test_mentioning_a_topic_is_not_a_contradiction(cfg):
    """Merely discussing PC or Switch 2 must not trip the check."""
    for title in (
        "Fans still hope for a GTA 6 PC version someday",
        "Switch 2 sales are strong ahead of the GTA 6 launch window",
        "Everything we know about the GTA 6 delay history",
    ):
        assert cred.contradicts_baseline(title, "", cfg) is None, title


# ---------------------------------------------------------------------------
# Relevance gate: "take two" is an ordinary English phrase
# ---------------------------------------------------------------------------

def test_bare_take_two_phrase_is_not_gta_relevant():
    """
    Four of the enabled feeds are all-games firehoses carrying 2000-char
    summaries, so a bare "take two" match put unrelated reviews into a GTA 6
    digest as blue Reports.
    """
    assert not cred.is_relevant("Hollow Knight Silksong review",
                                "It will take two weeks to finish this game")
    assert not cred.is_relevant("Best co-op games",
                                "You can take two players through the campaign")


def test_take_two_as_a_company_is_still_relevant():
    for title in (
        "Take-Two Interactive reports Q1 results",
        "Take-Two CEO Strauss Zelnick on the GTA 6 launch",
        "Take2 announces pre-orders",
    ):
        assert cred.is_relevant(title, ""), title


def test_new_first_party_feeds_pass_relevance():
    """The items these feeds actually carry, verified live 2026-08-26."""
    for title in (
        "Rockstar Games Announces Pre-Orders for Grand Theft Auto VI",
        "Support for GTA Online: The Kortz Center Heist Update is Available Now",
        "Public Stress Test Calendar: FiveM for GTAV Enhanced",
    ):
        assert cred.is_relevant(title, ""), title


def test_unrelated_take_two_release_is_filtered():
    """Why take2_ir can safely be instant: non-GTA releases self-filter."""
    assert not cred.is_relevant(
        "NBA 2K27 Cover Athletes Revealed: Victor Wembanyama, Caitlin Clark", "")


def test_cfxre_is_first_party_tier(cfg):
    """forum.cfx.re fell to the tier-4 default, so its items were held forever."""
    assert cred.tier_for_domain("forum.cfx.re", cfg) == 1
    assert cred.tier_for_domain("ir.take2games.com", cfg) == 1
