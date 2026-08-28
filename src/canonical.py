"""
URL canonicalisation, redirect resolution and title normalisation.

This is the cheap end of the dedup funnel and it does the heavy lifting:
deterministic, free, and more reliable than asking a model. An LLM should only
ever see items that survived every free filter here.

Two feed-specific problems this module exists to solve:

  1. Google News RSS does not give you publisher URLs. Every link is a
     `news.google.com/rss/articles/<opaque>` wrapper. Without resolution, the
     same IGN story arriving via Google News and via IGN's own feed looks like
     two different stories, and the digest posts it twice.
  2. Outlets append tracking parameters that differ per feed, so byte-identical
     articles produce different URLs.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from hashlib import blake2b
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

# Query parameters that are pure tracking. Removed unconditionally.
# NOTE: this is a denylist, not an allowlist, and that is deliberate — some
# sites carry the article id in the query string (?id=, ?p=, ?story=), so
# dropping unknown params would break those URLs entirely.
_TRACKING_PARAMS = frozenset(
    {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "utm_name", "utm_cid", "utm_reader", "utm_id", "utm_social",
        "utm_social-type", "utm_brand",
        "fbclid", "gclid", "dclid", "gclsrc", "msclkid", "yclid", "twclid",
        "igshid", "mc_cid", "mc_eid", "_hsenc", "_hsmi", "hsCtaTracking",
        "ref", "ref_src", "ref_url", "referrer", "source", "cmpid", "CMP",
        "at_medium", "at_campaign", "at_custom1", "ito", "ncid", "sr_share",
        "share_type", "smid", "partner", "spm", "vero_id", "wtrid",
        "__twitter_impression", "guccounter", "guce_referrer",
        "guce_referrer_sig", "amp", "outputType", "sh", "s_kwcid",
    }
)

# Hosts whose links are wrappers around a real publisher URL.
_REDIRECT_HOSTS = frozenset(
    {
        "news.google.com", "feedproxy.google.com", "feeds.feedburner.com",
        "t.co", "bit.ly", "buff.ly", "dlvr.it", "ift.tt", "trib.al",
        "out.reddit.com", "l.discord.com", "lnkd.in", "flip.it",
    }
)

# Publisher-name suffixes that feeds append to titles.
_TITLE_SUFFIX_RE = re.compile(
    r"\s*[|–—\-·:]\s*"
    r"(IGN|GameSpot|Eurogamer(?:\.net)?|VGC|Video\s*Games\s*Chronicle|PC\s*Gamer|"
    r"Polygon|Kotaku|GamesRadar\+?|Push\s*Square|Insider\s*Gaming|RockstarINTEL|"
    r"Rockstar\s*Newswire|GTA\s*Base|GTABase|TheGamer|Game\s*Rant|Dexerto|"
    r"Bloomberg|Variety|CNBC|Engadget|Tom's\s*Hardware|Game\s*File|TorrentFreak)"
    r"\s*$",
    re.IGNORECASE,
)

# Clickbait/label prefixes. Stripped for hashing so "BREAKING: X" == "X".
_TITLE_PREFIX_RE = re.compile(
    r"^\s*(BREAKING|RUMOR|RUMOUR|REPORT|LEAK|LEAKED|UPDATE|EXCLUSIVE|NEW|CONFIRMED|"
    r"OFFICIAL|WATCH|NEWS|OPINION|REVIEW|GUIDE)\s*[:\-–—!]\s*",
    re.IGNORECASE,
)

_NON_ALNUM_RE = re.compile(r"[^\w]+", re.UNICODE)


def strip_amp(url: str) -> str:
    """Rewrite AMP URLs back to their canonical origin."""
    parts = urlsplit(url)
    host, path = parts.netloc, parts.path

    # cdn.ampproject.org/c/s/<real-host>/<path>
    if host.endswith("cdn.ampproject.org"):
        m = re.match(r"^/[cv]/(?:s/)?([^/]+)(/.*)?$", path)
        if m:
            return urlunsplit(("https", m.group(1), m.group(2) or "/", parts.query, ""))

    # amp.example.com → example.com
    if host.startswith("amp."):
        host = host[4:]

    # trailing /amp, /amp/, .amp
    path = re.sub(r"(?:/amp/?|\.amp)$", "", path) or "/"
    return urlunsplit((parts.scheme, host, path, parts.query, parts.fragment))


def canonicalise(url: str) -> str:
    """
    Normalise a URL for use as a dedup key.

    Pure string work — no network. Call resolve_redirects() first if the URL may
    be a wrapper.
    """
    if not url:
        return ""
    url = url.strip()
    if not url:
        return ""

    url = strip_amp(url)
    parts = urlsplit(url)

    # No host, no URL. A feed that emits RELATIVE entry links -- Shacknews does:
    # "/article/150519/gta-6-gameplay-reveal" -- otherwise produced
    # "https:///article/150519/...", which is malformed but TRUTHY, so the
    # caller's `if not url: skip` never fired. The item was stored with an
    # unusable link and an empty source_domain, which then defaults to tier 4.
    # Returning "" makes the item skippable by the check that already exists.
    if not parts.hostname:
        return ""

    scheme = "https"
    host = (parts.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    # Preserve a non-default port if one was specified.
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"

    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if len(path) > 1:
        path = path.rstrip("/")
    if not path:
        path = "/"

    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
            if k.casefold() not in _TRACKING_PARAMS]
    query = urlencode(sorted(kept))

    # Fragment always dropped — it never identifies a distinct article.
    return urlunsplit((scheme, host, path, query, ""))


def is_wrapper(url: str) -> bool:
    """True if this URL is a known redirect/aggregator wrapper."""
    host = (urlsplit(url).hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    return host in _REDIRECT_HOSTS


def is_consent_wall(url: str) -> bool:
    """
    True if the URL is a Google/YouTube cookie-consent interstitial.

    Redirect chains from news.google.com land here, and the interstitial's
    `continue` parameter points BACK at the original URL — so following the
    chain loops forever. Detecting it lets the caller stop instead of burning
    hops, and is why Google News publisher attribution comes from the feed's
    <source> element rather than from URL resolution.
    """
    host = (urlsplit(url).hostname or "").casefold()
    return host.startswith("consent.") and (
        host.endswith("google.com") or host.endswith("youtube.com")
    )


def unwrap_consent(url: str) -> str:
    """
    Pull the target out of a consent interstitial's `continue` parameter.

    Returns the input unchanged if it is not a consent URL or has no usable
    target. Note the result is frequently the ORIGINAL wrapper URL, so callers
    must not treat this as progress through a redirect chain.
    """
    if not is_consent_wall(url):
        return url
    for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=False):
        if key == "continue" and value.startswith(("http://", "https://")):
            return value
    return url


def strip_source_suffix(title: str, source_title: str | None) -> str:
    """
    Remove a trailing " - Publisher" that Google News appends to every headline.

    The hardcoded suffix regex cannot know every publisher (Mashable, HotCars,
    and hundreds of others appear in a Google News query), but the feed hands us
    the exact publisher name per item — so use it. This materially improves
    cross-feed dedup: the Google News copy and the publisher's own feed copy of
    one story only collapse to the same title hash once this suffix is gone.
    """
    if not title or not source_title:
        return title
    needle = source_title.strip()
    if not needle:
        return title
    for sep in (" - ", " | ", " — ", " – ", " · "):
        tail = f"{sep}{needle}"
        if title.endswith(tail):
            return title[: -len(tail)].rstrip()
    return title


async def resolve_redirects(client, url: str, *, max_hops: int = 5) -> tuple[str, bool]:
    """
    Follow a redirect chain to the real publisher URL.

    Returns (final_url, resolved) where `resolved` is False if the chain could
    not be followed (in which case the caller should keep the original URL and
    may retry later).

    HEAD is tried first because it is cheap; a fair number of CDNs reject or
    mishandle HEAD, so GET is the fallback. Callers should cache the result —
    each wrapper only ever needs resolving once.
    """
    current = url
    for _ in range(max_hops):
        # A consent interstitial's `continue` points back at the URL we came
        # from, so following it loops. Stop and let the caller fall back to
        # feed-supplied publisher metadata.
        if is_consent_wall(current):
            return url, False

        try:
            resp = await client.head(current, follow_redirects=False)
        except Exception:
            try:
                resp = await client.get(current, follow_redirects=False)
            except Exception as exc:
                logger.debug("redirect resolution failed for %s: %s", current, exc)
                return current, current != url

        if resp.status_code in (301, 302, 303, 307, 308):
            nxt = resp.headers.get("location")
            if not nxt:
                return current, current != url
            # Relative Location header.
            if nxt.startswith("/"):
                p = urlsplit(current)
                nxt = urlunsplit((p.scheme, p.netloc, nxt, "", ""))
            current = nxt
            continue

        if resp.status_code == 200 and is_wrapper(current):
            # Google News serves a 200 HTML shim containing the real link
            # instead of a redirect. Pull the first external href out of it.
            found = _extract_from_shim(resp.text if hasattr(resp, "text") else "")
            if found:
                return found, True
            return current, current != url

        return current, current != url

    return current, current != url


_SHIM_HREF_RE = re.compile(r'(?:href|data-n-au)=["\'](https?://[^"\']+)["\']', re.IGNORECASE)


def _extract_from_shim(html: str) -> str | None:
    """Pull the target URL out of a Google News interstitial page."""
    if not html:
        return None
    for candidate in _SHIM_HREF_RE.findall(html[:20000]):
        host = (urlsplit(candidate).hostname or "").casefold()
        if host and not host.endswith("google.com") and not host.endswith("gstatic.com"):
            return candidate
    return None


def normalise_title(title: str) -> str:
    """
    Aggressively normalise a headline for near-duplicate detection.

    NFKD-fold, strip publisher suffix and clickbait prefix, collapse all
    non-alphanumerics. "BREAKING: GTA 6 Delayed Again — IGN" and
    "GTA 6 delayed again | Eurogamer" collapse to the same string.
    """
    if not title:
        return ""
    t = unicodedata.normalize("NFKD", title)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = _TITLE_SUFFIX_RE.sub("", t)
    t = _TITLE_PREFIX_RE.sub("", t)
    t = _NON_ALNUM_RE.sub(" ", t)
    return " ".join(t.split()).casefold()


def title_hash(title: str) -> str:
    """Stable short hash of the normalised title, for a UNIQUE index."""
    return blake2b(normalise_title(title).encode("utf-8"), digest_size=16).hexdigest()


def url_hash(canonical_url: str) -> str:
    """Stable short hash of a canonical URL."""
    return blake2b(canonical_url.encode("utf-8"), digest_size=16).hexdigest()


def source_domain(url: str) -> str:
    """Registrable-ish host for tier lookup: lowercased, no www."""
    host = (urlsplit(url).hostname or "").casefold()
    return host[4:] if host.startswith("www.") else host


# Highest tier number we will still send a reader to the outlet's homepage for.
# Above this the domain is not in the credibility list at all, and an unlabelled
# homepage link to an outlet we cannot vouch for is worth less than a plain name.
HOMEPAGE_TIER_MAX = 3


def link_target(url: str, *, tier: int, domain: str) -> tuple[str, bool]:
    """
    Decide where a story may point. Shared by the digest and the web edition.

    Returns (href, is_homepage_fallback). An empty href means "do not link".

    Most items reach the bot through Google News, whose RSS links are opaque
    redirects: the post-2024 blobs contain no recoverable address, and following
    one lands on consent.google.com from the EU. Emitting such a URL is worse
    than emitting none, because it looks like a link to the outlet named beside
    it and is not one.

    This lived only in the web builder at first, so the fix reached the website
    and left the Discord digest still handing members 300-character Google
    redirects -- the surface where a bad link is most expensive, since it is a
    tap on a phone rather than a click on a page.

    In order: a real publisher URL is used as-is; a wrapper from an outlet we
    recognise falls back to that outlet's front page; anything else is not a
    link at all.
    """
    if url and not is_wrapper(url):
        return url, False
    if domain and tier <= HOMEPAGE_TIER_MAX:
        return "https://" + domain + "/", True
    return "", False
