"""
URL canonicalisation and title normalisation tests.

These are the cheap end of the dedup funnel. If they regress, the same story
gets posted two or three times in one digest, which is the most visible possible
failure to a reader.
"""
from __future__ import annotations

from src.canonical import (
    canonicalise,
    is_wrapper,
    normalise_title,
    source_domain,
    strip_amp,
    title_hash,
)


# ---------------------------------------------------------------------------
# Canonicalisation
# ---------------------------------------------------------------------------

def test_strips_tracking_params():
    dirty = "https://www.ign.com/articles/gta-6-news?utm_source=twitter&utm_medium=social&fbclid=abc123"
    assert canonicalise(dirty) == "https://ign.com/articles/gta-6-news"


def test_keeps_unknown_params_because_they_may_identify_the_article():
    """Some CMSs put the article id in the query string; dropping it breaks the URL."""
    url = "https://example.com/index.php?p=12345&utm_source=rss"
    assert canonicalise(url) == "https://example.com/index.php?p=12345"


def test_normalises_scheme_host_and_trailing_slash():
    variants = [
        "http://www.eurogamer.net/gta-6-delayed/",
        "https://eurogamer.net/gta-6-delayed",
        "HTTPS://WWW.Eurogamer.net/gta-6-delayed//",
        "https://www.eurogamer.net/gta-6-delayed#comments",
    ]
    canon = {canonicalise(v) for v in variants}
    assert canon == {"https://eurogamer.net/gta-6-delayed"}


def test_query_params_are_order_independent():
    a = canonicalise("https://example.com/a?x=1&y=2")
    b = canonicalise("https://example.com/a?y=2&x=1")
    assert a == b


def test_de_amp_cdn_form():
    amp = "https://www-pcgamer-com.cdn.ampproject.org/c/s/www.pcgamer.com/gta-6-story"
    assert canonicalise(amp) == "https://pcgamer.com/gta-6-story"


def test_de_amp_subdomain_and_suffix_forms():
    assert canonicalise("https://amp.kotaku.com/gta-6-leak") == "https://kotaku.com/gta-6-leak"
    assert canonicalise("https://kotaku.com/gta-6-leak/amp") == "https://kotaku.com/gta-6-leak"
    assert canonicalise("https://kotaku.com/gta-6-leak?amp=1") == "https://kotaku.com/gta-6-leak"


def test_strip_amp_leaves_normal_urls_alone():
    url = "https://example.com/camp-story"  # must not match /amp$
    assert strip_amp(url) == url


def test_empty_and_garbage_input_does_not_raise():
    assert canonicalise("") == ""
    assert canonicalise("   ") == ""


def test_preserves_nonstandard_port():
    assert canonicalise("https://example.com:8443/a") == "https://example.com:8443/a"


# ---------------------------------------------------------------------------
# Wrapper detection
# ---------------------------------------------------------------------------

def test_detects_google_news_wrapper():
    assert is_wrapper("https://news.google.com/rss/articles/CBMiK2h0dHBz")
    assert is_wrapper("https://t.co/abc123")


def test_publisher_urls_are_not_wrappers():
    assert not is_wrapper("https://www.videogameschronicle.com/news/gta-6-thing/")
    assert not is_wrapper("https://ign.com/articles/x")


# ---------------------------------------------------------------------------
# Title normalisation
# ---------------------------------------------------------------------------

def test_same_headline_via_different_outlets_collapses():
    """The core cross-feed dedup case."""
    a = "BREAKING: GTA 6 Delayed Again - IGN"
    b = "GTA 6 delayed again | Eurogamer"
    c = "gta 6 delayed again"
    assert normalise_title(a) == normalise_title(b) == normalise_title(c)
    assert title_hash(a) == title_hash(b)


def test_strips_label_prefixes():
    for prefix in ("BREAKING:", "RUMOR:", "REPORT:", "LEAK:", "UPDATE:", "EXCLUSIVE:"):
        assert normalise_title(f"{prefix} Rockstar says hello") == "rockstar says hello"


def test_accents_and_punctuation_are_folded():
    assert normalise_title("GTA 6: Vice City — Leónida!") == normalise_title("gta 6 vice city leonida")


def test_distinct_stories_do_not_collide():
    a = "GTA 6 delayed to November 2026"
    b = "GTA 6 pre-orders open June 25"
    assert title_hash(a) != title_hash(b)


def test_empty_title_is_stable():
    assert normalise_title("") == ""
    assert title_hash("") == title_hash("")


# ---------------------------------------------------------------------------
# Domain extraction
# ---------------------------------------------------------------------------

def test_source_domain_drops_www():
    assert source_domain("https://www.pcgamer.com/a/b") == "pcgamer.com"
    assert source_domain("https://rockstarintel.com/feed/") == "rockstarintel.com"


def test_source_domain_keeps_subdomain():
    """Parasite-SEO blocking depends on the subdomain surviving."""
    assert source_domain("https://widescope.stanford.edu/gta6") == "widescope.stanford.edu"


# ---------------------------------------------------------------------------
# Google News consent-wall handling (regression: 166 items mis-tiered)
# ---------------------------------------------------------------------------

def test_detects_consent_wall():
    from src.canonical import is_consent_wall
    assert is_consent_wall("https://consent.google.com/m?continue=https%3A%2F%2Fx.com%2Fa")
    assert is_consent_wall("https://consent.youtube.com/m?continue=https%3A%2F%2Fy.com")
    assert not is_consent_wall("https://news.google.com/rss/articles/CBMi")
    assert not is_consent_wall("https://ign.com/articles/x")


def test_unwrap_consent_extracts_continue_target():
    from src.canonical import unwrap_consent
    url = "https://consent.google.com/m?continue=https%3A%2F%2Fwww.ign.com%2Fa&gl=HU"
    assert unwrap_consent(url) == "https://www.ign.com/a"


def test_unwrap_consent_leaves_other_urls_alone():
    from src.canonical import unwrap_consent
    assert unwrap_consent("https://ign.com/a") == "https://ign.com/a"


def test_strip_source_suffix_uses_the_feed_supplied_publisher():
    """
    The hardcoded suffix regex cannot know every publisher in a Google News
    query, so the exact name from <source> is used instead.
    """
    from src.canonical import strip_source_suffix
    assert strip_source_suffix("GTA 6 news thing - Mashable", "Mashable") == "GTA 6 news thing"
    assert strip_source_suffix("GTA 6 news thing | HotCars", "HotCars") == "GTA 6 news thing"
    assert strip_source_suffix("GTA 6 news thing", "IGN") == "GTA 6 news thing"
    assert strip_source_suffix("GTA 6 news thing - IGN", None) == "GTA 6 news thing - IGN"


def test_google_news_and_publisher_copies_share_a_title_hash():
    """The cross-feed dedup case this fix exists to enable."""
    from src.canonical import strip_source_suffix, title_hash
    via_google = strip_source_suffix(
        "Grand Theft Auto 6: Extended Look Global Release Times Confirmed - IGN", "IGN")
    via_publisher = "Grand Theft Auto 6: Extended Look Global Release Times Confirmed"
    assert title_hash(via_google) == title_hash(via_publisher)
