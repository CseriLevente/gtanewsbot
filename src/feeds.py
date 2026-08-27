"""
Feed polling and ingestion.

Politeness and resilience decisions worth knowing:

  * Conditional GETs (ETag / If-Modified-Since) are always sent. A 304 costs
    almost nothing and is the difference between a well-behaved poller and one
    that re-downloads 100 items every 15 minutes.
  * The politeness delay is PERSISTED per feed. A short-lived process that kept
    it in memory would re-learn the same 429 on every run. rockstarintel.com
    returned 429 when its main feed and a tag feed were fetched back to back, so
    this is not hypothetical.
  * feedparser is NOT allowed to do its own HTTP. Its fetcher is blocking
    urllib and it hides the 301/403/429/ETag details we need. We fetch with
    httpx and hand it bytes.
  * DEAD FEED DETECTION: a working feed almost never returns zero entries — it
    returns its back catalogue whether or not news happened. So
    `200 + parsed OK + 0 entries` on a feed that has previously had entries is
    near-certain breakage (301-to-HTML, login wall, CMS migration), and it is
    detectable *independently of the news cycle*. That distinction matters
    because a silently broken feed otherwise looks exactly like a quiet day.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass, field

import httpx

from src import canonical, credibility, storage
from src.clock import epoch_now, struct_time_to_epoch

logger = logging.getLogger(__name__)

# feedparser is imported lazily so that the commands which do NOT poll
# (init-db, status, check-ready, list-sources) still work when it is missing.
# check-ready exists precisely to report a missing dependency, so it must not
# be crashed by that dependency's absence.
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
    FEEDPARSER_VERSION = getattr(feedparser, "__version__", "unknown")
except ImportError:  # pragma: no cover - depends on the environment
    feedparser = None  # type: ignore[assignment]
    FEEDPARSER_AVAILABLE = False
    FEEDPARSER_VERSION = ""


class FeedparserMissing(RuntimeError):
    """Raised when a polling command runs without feedparser installed."""

    def __init__(self) -> None:
        super().__init__(
            'feedparser is not installed, so feeds cannot be parsed.\n'
            'Install it with:  pip install "feedparser==6.0.14"\n'
            "Commands that do not poll (init-db, status, check-ready, list-sources) "
            "work without it."
        )

# Retryable transport/status conditions. 403 is NOT retryable-with-different-headers
# for Cloudflare-fingerprinted hosts, but a transient 403 is possible elsewhere, so
# it is counted as a failure and backed off rather than hammered.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504, 522, 524})

MAX_POLITENESS_DELAY = 120

# An RSS feed serves its back catalogue, not just what changed. On a first run
# that means months of history: a 100-entry Google News `site:` query returned
# posts dated 2012, 2016 and 2020 alongside today's. Without an age gate the
# first digest would present the May 2025 Trailer 2 announcement as today's news.
#
# This also removes the static-page problem structurally. Rockstar's
# "Do Not Sell My Personal Information" and "GTA Online License Plate Creator"
# pages are indexed by a site: query and carry first-party authority, but they
# are dated 2020 and 2023 — so an age gate drops them without needing a title
# blocklist to guess at what is and is not an article.
DEFAULT_MAX_ITEM_AGE_DAYS = 3


@dataclass
class FeedResult:
    """Outcome of polling one feed."""
    key: str
    name: str
    ok: bool
    status: int | None = None
    not_modified: bool = False
    entries_seen: int = 0
    items_new: int = 0
    items_dropped: int = 0
    items_held: int = 0
    items_stale: int = 0
    error: str | None = None
    suspected_dead: bool = False
    consecutive_failures: int = 0

    @property
    def short(self) -> str:
        if self.not_modified:
            return f"{self.key}: 304 unchanged"
        if not self.ok:
            return f"{self.key}: FAIL {self.status or ''} {self.error or ''}".strip()
        if self.suspected_dead:
            return f"{self.key}: 200 but 0 entries (suspected broken)"
        extra = f", {self.items_stale} stale" if self.items_stale else ""
        return f"{self.key}: {self.entries_seen} entries, {self.items_new} new{extra}"


@dataclass
class PollSummary:
    """Aggregate health, rendered into the digest footer."""
    results: list[FeedResult] = field(default_factory=list)
    started_epoch: int = 0

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def new_items(self) -> int:
        return sum(r.items_new for r in self.results)

    @property
    def problems(self) -> list[FeedResult]:
        return [r for r in self.results if not r.ok or r.suspected_dead]

    def health_line(self) -> str:
        """
        One-line feed health for the digest footer.

        This is deliberately always present. An empty digest carrying
        '10 feeds · 9 ok · 1 blocked (403)' is informative; an empty digest with
        no health line is indistinguishable from a dead bot.
        """
        bits = [f"{self.total} feeds", f"{self.ok_count} ok"]
        broken = [r for r in self.results if not r.ok]
        dead = [r for r in self.results if r.ok and r.suspected_dead]
        if broken:
            detail = ", ".join(
                f"{r.key} ({r.status or r.error or 'error'})" for r in broken[:3]
            )
            bits.append(f"{len(broken)} failing: {detail}")
        if dead:
            bits.append(f"{len(dead)} suspected broken: {', '.join(r.key for r in dead[:3])}")
        if self.started_epoch:
            age_min = max(0, (epoch_now() - self.started_epoch) // 60)
            bits.append(f"polled {age_min} min ago")
        return " · ".join(bits)


def user_agent(contact_url: str | None) -> str:
    """
    Identify the bot honestly and give feed owners a way to reach us.

    Deliberately not a browser UA: for Cloudflare-fingerprinted hosts a Chrome
    UA makes things worse (the TLS fingerprint says Python, so 'UA says Chrome'
    is itself a bot signal), and for everyone else honesty is the polite option.
    """
    contact = contact_url or "https://example.invalid/gta6-news-bot"
    return f"gta6-news-bot/1.0 (+{contact})"


async def _throttle(domain_last_hit: dict[str, float], domain: str, delay: float) -> None:
    """Per-domain spacing with jitter, so N feeds on one host don't burst."""
    now = time.monotonic()
    last = domain_last_hit.get(domain)
    if last is not None:
        wait = delay - (now - last)
        if wait > 0:
            await asyncio.sleep(wait + random.uniform(0, 0.5))
    domain_last_hit[domain] = time.monotonic()


async def poll_feed(
    conn,
    client: httpx.AsyncClient,
    feed_row,
    cfg: dict,
    *,
    domain_last_hit: dict[str, float],
    max_item_age_days: int | None = None,
) -> FeedResult:
    """Fetch one feed, ingest its items, and record health."""
    key = feed_row["key"]
    url = feed_row["url"]
    tier = int(feed_row["tier"])
    name = key
    result = FeedResult(key=key, name=name, ok=False)

    domain = canonical.source_domain(url)
    delay = max(1, int(feed_row["politeness_delay_s"] or 5))
    await _throttle(domain_last_hit, domain, delay)

    headers: dict[str, str] = {}
    if feed_row["etag"]:
        headers["If-None-Match"] = feed_row["etag"]
    if feed_row["last_modified"]:
        headers["If-Modified-Since"] = feed_row["last_modified"]

    try:
        resp = await client.get(url, headers=headers, follow_redirects=True)
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        await storage.record_fetch_failure(conn, key, status=None, error=result.error)
        result.consecutive_failures = int(feed_row["consecutive_failures"] or 0) + 1
        logger.warning("feed %s transport error: %s", key, result.error)
        return result

    result.status = resp.status_code

    if resp.status_code == 304:
        result.ok = True
        result.not_modified = True
        await storage.record_fetch_success(
            conn, key, status=304, etag=resp.headers.get("etag"),
            last_modified=resp.headers.get("last-modified"),
            entry_count=0, newest_item_epoch=None,
        )
        return result

    if resp.status_code == 429:
        # Sticky, persisted backoff — doubling, capped.
        new_delay = min(MAX_POLITENESS_DELAY, delay * 2)
        await storage.set_politeness_delay(conn, key, new_delay)
        retry_after = resp.headers.get("retry-after")
        result.error = f"429 rate limited (politeness delay now {new_delay}s"
        result.error += f", Retry-After={retry_after})" if retry_after else ")"
        await storage.record_fetch_failure(conn, key, status=429, error=result.error)
        result.consecutive_failures = int(feed_row["consecutive_failures"] or 0) + 1
        logger.warning("feed %s: %s", key, result.error)
        return result

    if resp.status_code >= 400:
        result.error = f"HTTP {resp.status_code}"
        if resp.status_code == 403:
            result.error += " (bot-protected; no User-Agent will fix a TLS-fingerprint block)"
        await storage.record_fetch_failure(conn, key, status=resp.status_code, error=result.error)
        result.consecutive_failures = int(feed_row["consecutive_failures"] or 0) + 1
        if resp.status_code not in _RETRYABLE_STATUS:
            logger.warning("feed %s: %s", key, result.error)
        return result

    parsed = feedparser.parse(resp.content)
    entries = list(parsed.entries or [])
    result.entries_seen = len(entries)

    # Dead-feed heuristic: 200 + parsed + zero entries on a feed that used to
    # have them means the endpoint changed shape, not that news stopped.
    if not entries and int(feed_row["ever_had_entries"] or 0) == 1:
        result.suspected_dead = True
        logger.warning(
            "feed %s returned HTTP 200 with 0 entries but has had entries before "
            "— endpoint likely broken (redirect to HTML, login wall, or CMS change)",
            key,
        )

    if getattr(parsed, "bozo", 0) and not entries:
        result.error = f"malformed feed: {getattr(parsed, 'bozo_exception', '')}"[:300]
        await storage.record_fetch_failure(conn, key, status=resp.status_code, error=result.error)
        result.consecutive_failures = int(feed_row["consecutive_failures"] or 0) + 1
        return result

    feed_title = (getattr(parsed, "feed", {}) or {}).get("title") or key
    result.name = feed_title

    newest_epoch: int | None = None
    for entry in entries:
        published = struct_time_to_epoch(
            getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        )
        if published and (newest_epoch is None or published > newest_epoch):
            newest_epoch = published

        outcome = await _ingest_entry(
            conn, client, entry, feed_key=key, feed_tier=tier, cfg=cfg,
            published_epoch=published, feed_title=feed_title,
            max_item_age_days=max_item_age_days,
        )
        if outcome == "new":
            result.items_new += 1
        elif outcome == "held":
            result.items_held += 1
        elif outcome == "dropped":
            result.items_dropped += 1
        elif outcome == "stale":
            result.items_stale += 1

    result.ok = True
    await storage.record_fetch_success(
        conn, key, status=resp.status_code, etag=resp.headers.get("etag"),
        last_modified=resp.headers.get("last-modified"),
        entry_count=len(entries), newest_item_epoch=newest_epoch,
    )
    return result


def _feed_conf(cfg: dict, feed_key: str) -> dict:
    """The config block for one feed, by key. Empty dict if absent."""
    for f in cfg.get("feeds", []):
        if f.get("key") == feed_key:
            return f
    return {}


async def _ingest_entry(
    conn, client: httpx.AsyncClient, entry, *,
    feed_key: str, feed_tier: int, cfg: dict,
    published_epoch: int | None, feed_title: str,
    max_item_age_days: int | None = None,
) -> str:
    """Normalise, judge and store one feed entry. Returns new|dup|held|dropped|skip."""
    raw_link = (getattr(entry, "link", "") or "").strip()
    title = (getattr(entry, "title", "") or "").strip()
    if not raw_link or not title:
        return "skip"

    # --- publisher attribution -------------------------------------------------
    # Google News wraps every link and its redirect chain dead-ends at a cookie
    # consent interstitial, so URL resolution cannot reveal the publisher. The
    # feed's own <source> element carries it authoritatively and for free, so
    # prefer that over anything derived from the URL.
    src = getattr(entry, "source", None)
    src_title = src_href = None
    if src is not None:
        get = src.get if isinstance(src, dict) else lambda k, d=None: getattr(src, k, d)
        src_title = get("title") or None
        src_href = get("href") or get("url") or None

    # Strip the " - Publisher" suffix Google News appends, using the exact
    # publisher name. This is what lets the Google News copy and the
    # publisher's own feed copy of one story share a title hash.
    title = canonical.strip_source_suffix(title, src_title)

    # --- link resolution -------------------------------------------------------
    #
    # Google News wrapper resolution almost always FAILS: the redirect chain
    # dead-ends at a cookie-consent interstitial whose `continue` points back at
    # the wrapper. Only successes used to be cached, so every failure was retried
    # on every poll — with Google News supplying the large majority of items and
    # a 15-minute cadence, that is on the order of 19,000 pointless requests a
    # day at a host we depend on. Caching the FAILURE too is what stops it.
    final_link = raw_link
    if canonical.is_wrapper(raw_link):
        cached = await storage.get_cached_resolution(conn, raw_link)
        if cached:
            # A sentinel equal to the wrapper itself means "known unresolvable".
            final_link = raw_link if cached == raw_link else cached
        else:
            resolved, ok = await canonical.resolve_redirects(client, raw_link)
            if ok and resolved != raw_link and not canonical.is_consent_wall(resolved):
                await storage.cache_resolution(conn, raw_link, resolved)
                final_link = resolved
            else:
                await storage.cache_resolution(conn, raw_link, raw_link)

    url_canon = canonical.canonicalise(final_link)
    if not url_canon:
        return "skip"

    # Age gate. Uses epoch seconds throughout — never naive local arithmetic —
    # so it behaves identically across a DST transition. Items with no
    # publication date are allowed through, because absence of a date is not
    # evidence of staleness and some feeds simply omit it.
    if published_epoch is not None:
        max_age_days = max_item_age_days if max_item_age_days is not None else DEFAULT_MAX_ITEM_AGE_DAYS
        if max_age_days > 0 and published_epoch < epoch_now() - max_age_days * 86400:
            return "stale"

    # Some feeds (notably a Google News `site:` query) index static site pages
    # alongside articles: "Rockstar Games", "Grand Theft Auto V", "Social Club
    # Account". Those carry a first-party domain and would post as OFFICIAL.
    # A real headline is a sentence; a page title is a noun phrase, so a minimum
    # word count separates them cheaply.
    #
    # Scoped PER FEED, never global: "GTA 6 delayed" is three words and is
    # exactly the headline we most want to keep.
    min_words = int(_feed_conf(cfg, feed_key).get("min_title_words", 0) or 0)
    if min_words and len(title.split()) < min_words:
        return "dropped"

    summary = (getattr(entry, "summary", "") or getattr(entry, "description", "") or "").strip()
    summary = _strip_html(summary)[:2000]

    # Tier on the PUBLISHER, not on the aggregator that relayed it. Falling back
    # to the URL's own host would tier every Google News item as news.google.com
    # (unknown -> tier 4 -> held forever), which is exactly the bug this avoids.
    domain = canonical.source_domain(src_href) if src_href else canonical.source_domain(url_canon)
    if not domain:
        domain = canonical.source_domain(url_canon)
    # Attribution is an editorial requirement, so it should read like a masthead
    # rather than an RSS channel title ("Eurogamer.net Latest Articles Feed").
    # Preference: curated display name > the feed's own <source> title > feed title.
    source_name = (
        cfg.get("publisher_names", {}).get(domain)
        or src_title
        or feed_title
    )

    verdict = credibility.judge(
        title=title, summary=summary, domain=domain, url=url_canon,
        feed_tier=feed_tier, cfg=cfg,
    )

    if verdict.decision == credibility.DROP:
        # Not stored: a dropped item is noise, and storing it would bloat the DB
        # with SEO spam. Relevance drops are the overwhelming majority.
        return "dropped"

    t_hash = canonical.title_hash(title)
    if await storage.title_hash_exists(conn, t_hash):
        return "dup"

    state = storage.STATE_HELD if verdict.decision == credibility.HOLD else storage.STATE_NEW
    item_id = await storage.insert_item(
        conn,
        feed_key=feed_key,
        url_canonical=url_canon,
        url_original=raw_link,
        title=title,
        title_hash=t_hash,
        source_name=source_name,
        source_domain=domain,
        published_epoch=published_epoch,
        summary_raw=summary,
        tier=verdict.tier,
        is_rumour=verdict.is_rumour,
        state=state,
        state_reason="; ".join(verdict.reasons)[:500] or None,
    )
    if item_id is None:
        return "dup"
    return "held" if state == storage.STATE_HELD else "new"


_TAG_RE = __import__("re").compile(r"<[^>]+>")
_WS_RE = __import__("re").compile(r"\s+")


def _strip_html(text: str) -> str:
    """Crude tag strip — feed summaries are HTML fragments."""
    import html as _html
    return _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub(" ", text))).strip()


async def poll_all(conn, cfg: dict, *, contact_url: str | None = None,
                   timeout: float = 20.0,
                   max_item_age_days: int | None = None) -> PollSummary:
    """Poll every enabled feed and return an aggregate health summary."""
    if not FEEDPARSER_AVAILABLE:
        raise FeedparserMissing()
    summary = PollSummary(started_epoch=epoch_now())
    feed_rows = await storage.get_feeds(conn, enabled_only=True)
    if not feed_rows:
        logger.warning("no enabled feeds configured")
        return summary

    if max_item_age_days is None:
        try:
            max_item_age_days = int(os.environ.get("MAX_ITEM_AGE_DAYS", "")
                                    or DEFAULT_MAX_ITEM_AGE_DAYS)
        except ValueError:
            max_item_age_days = DEFAULT_MAX_ITEM_AGE_DAYS

    domain_last_hit: dict[str, float] = {}
    headers = {
        "User-Agent": user_agent(contact_url),
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        for row in feed_rows:
            try:
                summary.results.append(
                    await poll_feed(conn, client, row, cfg,
                                    domain_last_hit=domain_last_hit,
                                    max_item_age_days=max_item_age_days)
                )
            except Exception as exc:
                logger.exception("unhandled error polling %s", row["key"])
                summary.results.append(
                    FeedResult(key=row["key"], name=row["key"], ok=False,
                               error=f"{type(exc).__name__}: {exc}")
                )

    # Cross-feed correlation: all feeds failing is far more likely to be local
    # (network, clock, IP block) than a global outage of every gaming outlet.
    if summary.total >= 3 and summary.ok_count == 0:
        logger.error(
            "ALL %d feeds failed — check network connectivity, system clock, or "
            "whether this IP has been blocked. This is almost never a news blackout.",
            summary.total,
        )
    return summary
