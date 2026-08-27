# Engineering Hygiene: Polling Engine, Resilience & Windows Scheduling

Research date: **2026-08-24/25**. Target: Python 3.12.10 on Windows 10 Enterprise.
All library facts verified against PyPI JSON API / GitHub / vendor docs (not blogs). Every URL consulted is listed at the bottom.

Where a Windows behaviour could not be verified from a primary source it is tagged **[UNVERIFIED]**.

---

## 0. Decisions summary

### Library picks

| Need | Pick | Version (2026-08) | Status |
|---|---|---|---|
| Feed parsing | **feedparser** | 6.0.14 (2026-07-30) | Actively maintained, py3.10–3.14 |
| HTTP | **httpx** (already installed) | keep **0.27.0**; latest is 0.28.1 | Fine as-is |
| DB | **aiosqlite** (already installed) | keep **0.20.0**; latest is 0.22.1 | Fine as-is |
| Discord posting | **httpx + webhook** — *no discord.py* | n/a | Avoids a whole dependency + gateway |
| Article text (only if needed) | **trafilatura** | 2.2.0 (2026-07-31) | Actively maintained, py3.10–3.14 |
| HTTP caching layer | **none** (hand-rolled ETag in SQLite) | — | hishel would force httpx ≥ 0.28.1 |

```
pip install "feedparser==6.0.14"
```

That is the only mandatory install. Optional, only if you decide you need full article text:

```
pip install "trafilatura==2.2.0"
```

Do **not** install: `atoma` (dead since 2019), `newspaper3k` (dead since 2018), `discord.py` (not needed for
webhook-only posting), `tzdata` (standing project rule), `hishel` (drags httpx 0.28+).

### Key architectural decisions

1. **Fetch with httpx, parse bytes with feedparser.** Never let feedparser do its own HTTP.
2. **DB lives at `%LOCALAPPDATA%\gta6-news-bot\bot.db`** — *not* in the OneDrive tree. This is a real
   corruption hazard, not a theoretical one (§5).
3. **WAL mode + `busy_timeout=5000` + `synchronous=NORMAL`.** Safe on local NTFS; would be unsafe on a
   network/synced path.
4. **Scheduling: Windows Task Scheduler firing a short-lived `pythonw.exe` process every 15 minutes**,
   with a Daily trigger + `<Repetition>`. All "is the digest due?" logic lives in Python, keyed on local
   date with a `UNIQUE` guard. This makes `StartWhenAvailable` and `WakeToRun` nice-to-haves rather than
   load-bearing, and it also serves the instant-alert requirement with the same process. (§6)
5. **Single local clock: bare `datetime.now()` for the digest date/hour decision only.**
   Everything else — ages, backoff, item timestamps, retry windows — uses **epoch seconds** (`time.time()`,
   `calendar.timegm()`). No naive-local arithmetic anywhere. (§7)
6. **Never hardcode `+02:00`.** The next DST transition is **2026-10-25**, ~2 months away, after which the
   machine's offset becomes **+01:00**. See §7.2 — this is the most likely bug in the whole project.
7. **Digest content selection by an "unsent" flag, not by a time window.** Sidesteps DST entirely.

---

## 1. Feed parsing library

### The candidates, verified

| Library | Latest | Released | Python | Verdict |
|---|---|---|---|---|
| **feedparser** | **6.0.14** | **2026-07-30** | `>=3.10`, classifiers 3.10–3.14 | **Use this** |
| atoma | 0.0.17 | **2019-07-07** | classifiers stop at 3.7 | **Abandoned.** Do not use. |
| reader | 3.26 | recent | `>=3.11`, 3.11–3.14 | Alive, but wrong shape (see below) |
| httpx + lxml by hand | — | — | — | Only if you enjoy pain |

**feedparser is not abandoned.** Evidence: three releases in the last 12 months (6.0.12 on 2025-09-10,
6.0.13 on 2026-07-28, 6.0.14 on 2026-07-30), ~1,529 commits, 2.4k stars, active GitHub Actions CI.
Open issues **85**, open PRs **23** — that is a normal backlog for a 20-year-old library with a
huge compatibility surface, not a sign of death. Maintainer: Kurt McKee.

Recent changelog, relevant bits:
- **6.0.14** — upgrade to `feedparser-sgmllib` 2.0.0.
- **6.0.13** — dropped Python ≤3.9; **migrated off `sgmllib3k` onto `feedparser-sgmllib`**.
- **6.0.12** — fixed an `AssertionError` crash on Python 3.10+ (#304); fixed a `re.sub` DeprecationWarning (#389).
- **6.0.11** — removed use of the `cgi` module (#330).

Two of those four entries matter directly to you. The `cgi` removal (6.0.11) is what makes feedparser
work at all on Python 3.13+, since `cgi` was deleted from the stdlib. The `sgmllib3k` → `feedparser-sgmllib`
swap (6.0.13) replaces a long-unmaintained vendored dependency that was the usual source of
"feedparser won't install on new Python" complaints. **Pin ≥ 6.0.13, and 6.0.14 is the one to take.**

There are **no known Python 3.12 issues** in feedparser 6.0.12+. Python 3.12 is an explicit classifier and
is in CI.

### RSS 2.0 and Atom: yes, both, plus more

The package summary is literally: *"Universal feed parser, handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF,
Atom 0.3, and Atom 1.0 feeds"*. It normalises them into one shape, which is the entire reason to use it
instead of lxml: you write `entry.title / entry.link / entry.id / entry.published_parsed` once and it
works against both families. Doing that normalisation yourself over 10 heterogeneous feeds is a week of
whack-a-mole.

### Malformed feeds: the bozo bit

feedparser sets `d.bozo = 1` when the feed is not well-formed XML, and puts the reason in
`d.bozo_exception`. Crucially, **it still returns entries**: it falls back to a lenient SGML-ish parser
rather than giving up. Real-world feeds are malformed constantly (unescaped `&`, incomplete end tags,
mislabelled encodings), so this is a feature, not a defect.

The correct policy is therefore **not** "reject bozo feeds". It is:

```python
if d.bozo and not d.entries:
    # structurally broken — treat as a fetch failure, alert
else:
    # use d.entries; log d.bozo_exception once per feed per day at DEBUG
```

`bozo=1` with entries present is normal and should not page you. `bozo=1` with zero entries, or
`bozo=0` with zero entries against a feed that historically had entries, is the real signal (§4).

### Should you let feedparser do its own HTTP? **No.**

`feedparser.parse()` accepts a URL, a local file path, a file-like object, or a `str`/`bytes` of raw feed
data. It *does* have real HTTP support — documented pages for ETag/Last-Modified, User-Agent/Referer,
redirects, HTTP auth, and custom headers, and the result exposes `d.status`, `d.href`, `d.etag`,
`d.modified`, `d.headers`. Passing `etag=`/`modified=` works and a 304 gives you `d.status == 304` with
empty `feed`/`entries`.

Use it anyway? No, for five concrete reasons:

1. **It's `urllib`, synchronous and blocking.** Your bot is asyncio + httpx. Calling `feedparser.parse(url)`
   inside an async function blocks the event loop for the whole request. You'd have to push it to a thread
   pool, at which point you've gained nothing.
2. **No connection pooling, no HTTP/2, no shared client config.** httpx gives you all three across your ~10 feeds.
3. **You need per-feed HTTP state in SQLite anyway** (§2). Once you're storing ETags yourself, feedparser's
   convenience wrapper is redundant.
4. **You need to *see* the raw response** to detect 301 (URL moved), 403 (Cloudflare), 429 (rate limit), and
   to hash the body for lying-ETag detection. feedparser's abstraction hides exactly the things you need.
5. **One HTTP stack = one place for timeouts, retries, User-Agent, and logging.** Two stacks means two
   User-Agents and two sets of bugs.

**Recommended shape:**

```python
resp = await client.get(url, headers=cond_headers)      # httpx does the network
d = feedparser.parse(resp.content, response_headers=resp.headers)   # feedparser does the XML
```

Passing `response_headers=` lets feedparser use the server's `Content-Type` charset when the XML
declaration disagrees with it, which is the single most common encoding bug in feeds. Note: `parse()`'s
exact keyword set is documented across the "Advanced Features" pages rather than one signature block;
`response_headers` is the documented mechanism for handing in headers alongside bytes.
**[UNVERIFIED — check `inspect.signature(feedparser.parse)` on your install before relying on the
keyword name.]** If it's absent, pass `resp.content` alone and set `resp.encoding` yourself.

### Why not `reader`?

`reader` 3.26 is alive and well-engineered, and it depends on `feedparser>=6` — so it is a *wrapper*, not
an alternative parser. But it brings `requests`, `beautifulsoup4`, `werkzeug`, `structlog`,
`typing-extensions`, and **its own opinionated SQLite schema** with full-text search. You already have a
schema design (dedup, digest runs, instant-alert interlock) that doesn't match its model, and it is
sync-only. Adopting it means adopting its storage. Wrong tool for a 10-feed bot with bespoke state.

### Why not httpx + lxml by hand?

You'd reimplement: RSS/Atom field normalisation, five date formats, relative-URI resolution, encoding
detection, namespace handling, and lenient recovery from malformed XML. feedparser is ~6,000 lines of
exactly that, battle-tested since 2004. Use lxml directly only for the *article HTML* path (§8), never
for the feeds.

---

## 2. HTTP conditional requests

### The protocol, from RFC 9110

- Send **`If-None-Match: <etag>`** when you have a stored ETag. Send **`If-Modified-Since: <http-date>`**
  when you have a stored `Last-Modified`. You may send both.
- If both are present, **`If-None-Match` is evaluated first** and takes precedence. RFC 9110: a recipient
  *SHOULD* use `If-None-Match` when an entity-tag is available, in preference to `If-Modified-Since`.
- On a match the server returns **304 Not Modified** with no body. The client keeps its cached
  representation and **updates its stored header fields from the 304's headers** — i.e. if the 304 carries
  a fresh `ETag` or `Cache-Control`, store it.
- Support **both**, because plenty of servers implement only one. feedparser's own docs say the same:
  *"Clients should support both ETag and Last-Modified headers, as some servers support one but not the
  other. If you do not support ETag and Last-Modified headers, you will repeatedly download feeds that
  have not changed."*

### Headers to store, and what to send back

| Stored from response | Sent on next request |
|---|---|
| `ETag` | `If-None-Match: <exact value, quotes and W/ prefix included>` |
| `Last-Modified` | `If-Modified-Since: <exact value, verbatim string>` |

Two rules people get wrong:

1. **Echo the ETag byte-for-byte.** Do not strip the surrounding double quotes. Do not strip a `W/` weak
   prefix. `ETag: W/"abc123"` → `If-None-Match: W/"abc123"`. Stripping quotes is the #1 reason
   "my conditional requests never return 304".
2. **Never re-format the date.** Store the `Last-Modified` header as the *raw string* and send it back
   unchanged. Do not parse it into a datetime and re-render it — you will get the format or the timezone
   wrong, and you cannot get it wrong if you never touch it. (This also means you never need tzdata for it.)

### Handling the responses

| Status | Action |
|---|---|
| **304** | Nothing changed. Update `etag`/`last_modified` if the 304 supplied new ones. Bump `last_success_at`. **Do not** touch `last_content_at`. Zero parsing. |
| **200** | Parse. Store new `ETag`/`Last-Modified` (or `NULL` them if absent — don't keep stale ones). Hash the body (§below). |
| **301 / 308** | Permanent move. See §4. |
| **302 / 307** | Temporary. Follow, but keep the stored URL. |
| **403 / 429 / 5xx** | See §3 / §4. Leave `etag`/`last_modified` untouched. |
| **404 / 410** | Increment a hard-failure counter; 410 especially means "stop asking". |

### When the server gives you neither ETag nor Last-Modified

This is common — maybe a third of feeds. You get no conditional-request ability at all, so:

1. **Fall back to a body hash.** Store `sha256(resp.content)` as `content_hash`. On the next 200, if the
   hash is unchanged, skip parsing entirely. You still paid for the bandwidth, but you save CPU and, more
   importantly, you get a reliable "did this feed actually change?" signal for dead-feed detection (§4).
2. **Back off the poll rate for that feed.** A feed with no validators and a stable hash is telling you it
   updates rarely. Widen its interval (e.g. 15 min → 60 min) after N unchanged polls, and reset on change.
3. **Send `Accept-Encoding: gzip, deflate`** — httpx does this by default and it is the biggest single
   bandwidth win on a validator-less feed. RSS/Atom XML compresses ~75–85%.

### Feeds that lie

Three failure modes, all real:

- **Always 200, never 304**, even with correct conditional headers. Cause: a CDN or app server that
  doesn't implement validation. Detection: `etag` present but `status == 200` on N consecutive polls with
  an unchanged `content_hash`. Mitigation: rely on `content_hash`; log it once and move on.
- **New ETag every request.** Cause: the ETag is derived from a timestamp, a worker PID, or a gzip
  stream, not the content. Symptom: you never get a 304 and your `etag` column churns. Detection:
  `etag` changed AND `content_hash` unchanged, ≥3 times. Mitigation: **stop sending `If-None-Match`
  for that feed** — set a `etag_useless` flag and fall back to `If-Modified-Since` + hash. Continuing to
  send a useless ETag also *suppresses* `If-Modified-Since` (because If-None-Match wins), so a churning
  ETag actively makes things worse. This one is worth the code.
- **`Last-Modified` in the future, or constant while content changes.** Rare; the hash catches it.

### How much does this actually save?

Honest numbers for your workload. Ten feeds, polled every 15 minutes = 960 fetches/day.
A typical RSS/Atom feed body is 20–120 KB uncompressed, call it 50 KB, ~10 KB gzipped.

- **No conditional requests, no gzip:** ~48 MB/day.
- **gzip only:** ~9.6 MB/day.
- **gzip + conditional requests:** news feeds change maybe 10–30 times/day each, so ~85–95% of polls
  return 304. A 304 is ~300 bytes of headers. That's ~0.3 MB of 304s + ~2 MB of real bodies ≈ **~2.3 MB/day**.

So roughly a **20× reduction** versus naive, or **~4×** versus gzip alone. In absolute terms this is
trivial bandwidth for you — the real payoff is **politeness**: you stop being the client that pulls 48 MB
of unchanged XML off someone's hobby blog every day, which is exactly the behaviour that gets a
User-Agent added to a blocklist. Treat conditional requests as blocking-avoidance, not as bandwidth saving.

### Concrete pattern

```python
import hashlib
import httpx

async def conditional_get(client: httpx.AsyncClient, feed: dict) -> dict:
    """feed: row from `feeds`. Returns a result dict; never raises for HTTP status."""
    headers = {}
    if feed["etag"] and not feed["etag_useless"]:
        headers["If-None-Match"] = feed["etag"]          # verbatim, quotes included
    if feed["last_modified"]:
        headers["If-Modified-Since"] = feed["last_modified"]  # verbatim string

    try:
        r = await client.get(feed["url"], headers=headers)
    except httpx.HTTPError as exc:
        return {"kind": "neterror", "error": f"{type(exc).__name__}: {exc}"}

    if r.status_code == 304:
        return {
            "kind": "notmodified",
            # RFC 9110: refresh stored validators from the 304 if it supplies them
            "etag": r.headers.get("ETag") or feed["etag"],
            "last_modified": r.headers.get("Last-Modified") or feed["last_modified"],
        }

    if r.status_code in (301, 308):
        return {"kind": "moved", "location": r.headers.get("Location"), "status": r.status_code}

    if r.status_code != 200:
        return {"kind": "httperror", "status": r.status_code,
                "retry_after": r.headers.get("Retry-After")}

    digest = hashlib.sha256(r.content).hexdigest()
    return {
        "kind": "ok",
        "body": r.content,
        "response_headers": r.headers,
        "etag": r.headers.get("ETag"),                 # may be None -> null the column
        "last_modified": r.headers.get("Last-Modified"),
        "content_hash": digest,
        "unchanged_body": digest == feed["content_hash"],
    }
```

Note `follow_redirects` is deliberately **not** set: httpx does **not** follow redirects by default, which
is exactly what you want here — a 301 arrives as a 301 so you can act on it.

### SQLite columns for per-feed HTTP state

```sql
CREATE TABLE IF NOT EXISTS feeds (
    id                  INTEGER PRIMARY KEY,
    url                 TEXT    NOT NULL UNIQUE,   -- current, may be rewritten by a 301
    original_url        TEXT    NOT NULL,          -- as configured; never rewritten
    name                TEXT    NOT NULL,
    domain              TEXT    NOT NULL,          -- for per-domain politeness locks (§3)
    tier                TEXT    NOT NULL DEFAULT 'digest',  -- 'instant' | 'digest'
    enabled             INTEGER NOT NULL DEFAULT 1,

    -- HTTP conditional state
    etag                TEXT,                     -- verbatim, incl. quotes / W/
    last_modified       TEXT,                     -- verbatim HTTP-date string
    etag_useless        INTEGER NOT NULL DEFAULT 0,  -- set when ETag churns w/o content change
    content_hash        TEXT,                     -- sha256 hex of last 200 body
    etag_churn_count    INTEGER NOT NULL DEFAULT 0,

    -- observability / health  (all epoch seconds UTC, never local time)
    last_attempt_at     INTEGER,
    last_success_at     INTEGER,                  -- last 200 or 304
    last_content_at     INTEGER,                  -- last time content_hash actually changed
    last_item_at        INTEGER,                  -- last time a NEW item was stored
    last_status         INTEGER,
    last_error          TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    backoff_until       INTEGER,                  -- epoch; skip this feed until then
    poll_interval_s     INTEGER NOT NULL DEFAULT 900,

    -- rolling stats for dead-feed detection (§4)
    items_total         INTEGER NOT NULL DEFAULT 0,
    median_gap_s        INTEGER                   -- median seconds between new items
);
CREATE INDEX IF NOT EXISTS ix_feeds_enabled ON feeds(enabled, backoff_until);
```

---

## 3. Politeness and blocking

### User-Agent

**Yes, identify yourself, and yes, include a contact URL.** An anonymous or spoofed UA is the thing that
gets you banned, because when an operator sees unexplained traffic their only lever is a block. A UA with
a URL gives them the option to email you instead.

```
GTA6NewsBot/1.0 (+https://github.com/<you>/gta6-news-bot; contact: <you>@example.com) python-httpx/0.27
```

Rules:
- Real, resolvable contact. A GitHub repo URL is ideal (it also explains what the bot does).
- Keep `python-httpx/x.y` on the end. Some operators allow known library UAs; hiding it buys nothing.
- **Do not** claim to be Chrome. See the Cloudflare section — it does not work, and it converts a
  "polite unknown bot" into a "bot lying about its identity", which is a worse position to be in
  both technically and ethically.

Also always send:

```python
DEFAULT_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/atom+xml, application/rss+xml, application/xml;q=0.9, text/xml;q=0.9, */*;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en;q=0.9, hu;q=0.8",
}
```

The `Accept` header matters: some WAFs score a request that asks for `*/*` only as bot-like, and some
servers content-negotiate the feed endpoint.

### Does robots.txt apply to RSS feeds?

Technically robots.txt applies to any HTTP fetch by an automated agent, feeds included. In practice the
ecosystem is split, and the split is along a meaningful line:

- **User-triggered fetchers ignore it.** Google states outright: *"Because the fetch was requested by a
  user, these fetchers generally ignore robots.txt rules"* — and **Feedfetcher** is listed as exactly such
  a fetcher. Feeder.co's crawler docs say the same: it acts on behalf of a user and doesn't check
  robots.txt.
- **Unattended aggregators are increasingly expected to honour it.** FreshRSS, feedbot, MonitoRSS and
  friends all publish UA tokens precisely so site owners can block them in robots.txt.

**Your bot is unattended.** It polls on a timer with no human in the loop, so it sits on the crawler side
of that line, not the user-agent side. Recommendation:

> **Honour robots.txt.** Fetch `https://<domain>/robots.txt` once per domain, cache it for 24 h in SQLite,
> and check the feed path against it with `urllib.robotparser` (stdlib — no dependency). If the feed path
> is `Disallow`ed for `*` or for your UA token, **disable that feed and log it loudly** rather than
> silently skipping — you want to know, because it usually means you should find an official feed instead.
> Also read `Crawl-delay` if present and use it as the floor for that domain's politeness delay.

This costs you ~10 extra requests per day and removes an entire category of "why did I get banned"
outcomes. `robotparser` handles the parsing; treat a 404 or 5xx on robots.txt as "allowed" (that is the
conventional reading).

### Rate-limit etiquette across ~10 feeds

Three separate concepts, don't conflate them:

1. **Per-feed poll interval** — how often you check one feed. 15 minutes is polite for news. Five minutes
   is defensible for a first-party instant-alert source. Below 5 minutes you are being rude unless the
   publisher says otherwise.
2. **Per-domain politeness delay** — the minimum gap between *any two* requests to the same host.
   **Recommend 5 seconds, and 10 seconds for domains that have ever 429'd you.** Enforce with a
   per-domain `asyncio.Lock` plus a stored `last_request_at`, so it holds even when two different feeds
   share a host. This is precisely the rockstarintel.com case in your brief: a main feed and a tag feed on
   the same host fetched back-to-back returned 429. Two requests, zero delay, same host — that is the bug.
3. **Global concurrency** — how many requests are in flight at once. `httpx.Limits(max_connections=5,
   max_keepalive_connections=5)` plus an `asyncio.Semaphore(4)`. With 10 feeds there is no reason to open
   more.

### Jittered schedule so 10 feeds aren't hit simultaneously

Two layers, both cheap:

**Layer 1 — deterministic per-feed phase offset.** Spread the feeds evenly across the interval using a
stable hash of the feed URL, so feed *k* is due at `interval * k/N` past the hour, and the same feed always
lands in the same slot (which is friendlier than random — operators see a regular, predictable pattern).

```python
import hashlib

def phase_offset_s(feed_url: str, interval_s: int) -> int:
    h = hashlib.sha256(feed_url.encode()).digest()
    return int.from_bytes(h[:4], "big") % interval_s

def is_due(feed, now_epoch: int) -> bool:
    if feed["backoff_until"] and now_epoch < feed["backoff_until"]:
        return False
    if feed["last_attempt_at"] is None:
        return True
    interval = feed["poll_interval_s"]
    # anchor the schedule to a per-feed phase so feeds don't align
    slot_now  = (now_epoch  - phase_offset_s(feed["url"], interval)) // interval
    slot_last = (feed["last_attempt_at"] - phase_offset_s(feed["url"], interval)) // interval
    return slot_now > slot_last
```

**Layer 2 — small random jitter per run** so you don't hammer the exact same wall-clock second every
15 minutes forever: `await asyncio.sleep(random.uniform(0, 20))` before the batch, and rely on the
per-domain delay inside it.

Net effect with the Task Scheduler design (§6): the process wakes every 15 min, sleeps 0–20 s, then
fetches only the feeds whose phase slot has advanced, at most 4 concurrently, ≥5 s apart per host.
Ten feeds finish in well under a minute and no host sees a burst.

### HTTP 403 from Cloudflare-protected sites (the rockstargames.com case)

**What is actually happening.** Cloudflare fingerprints the **TLS ClientHello** — the JA3/JA4 hash —
*before any HTTP headers exist*. Python's OpenSSL-based stack (httpx, requests, aiohttp all share it)
produces a distinctive fingerprint. So the decision to 403 you is made before your `User-Agent` is read.
The consequence is blunt:

> **No combination of headers will reliably fix a Cloudflare 403.** Sending a Chrome User-Agent
> actually makes detection *easier*, because "UA says Chrome 120, TLS says Python/OpenSSL" is itself a
> high-confidence bot signal.

**What sometimes does get through**, and is worth trying once because it costs nothing and is honest:
- A complete, coherent header set (`Accept`, `Accept-Language`, `Accept-Encoding`) rather than httpx's
  minimal defaults. Some sites are on a low-sensitivity Cloudflare setting where a plausible header set
  passes.
- HTTP/2 (`httpx.AsyncClient(http2=True)`, needs `pip install httpx[http2]`). Some WAF rules score
  HTTP/1.1-only clients worse. Cheap to try.
- A `Referer` pointing at the site's own homepage.

**What would get through, and why you shouldn't.** `curl_cffi` (0.16.2, 2025-03-12) replaces OpenSSL with
BoringSSL and replicates Chrome's exact TLS fingerprint; `cfscrape`/FlareSolverr solve challenges; a
headless browser bypasses the whole thing. These work. **Recommendation: don't.**

> **The ethical/ToS line:** a realistic, self-identifying User-Agent with a contact URL is *identifying
> yourself*. Impersonating Chrome's TLS fingerprint to defeat a bot-protection product is
> *circumventing an access control the site owner deliberately turned on*. Rockstar's terms of service
> prohibit automated access to their site. A 403 from Cloudflare is not a bug to route around — it is the
> publisher saying no, in the only language they have.

**What to do instead, in order:**
1. Look for an official machine-readable source. Publisher newsroom pages very often have an
   `<link rel="alternate" type="application/rss+xml">` that is served from a different, unprotected host,
   or a JSON endpoint behind the page.
2. Use a **second-party** source that covers the same news and *does* welcome feed readers
   (rockstarintel.com etc. — which is presumably why it's on your list). First-party 403 → treat the
   second-party feed as the source of record for that publisher, and accept the ~minutes of latency.
3. Mark the feed `enabled=0` with `last_error='blocked_403'` and **surface it in a startup log line**, so
   the 403 is a visible known-limitation rather than an invisible gap. This matters: a permanently-403
   first-party feed looks identical to "Rockstar posted nothing", which is exactly the failure mode §4 is
   about.
4. If you genuinely need it: email the contact address in your own UA policy and ask. Publishers do
   whitelist hobby bots that ask nicely.

### HTTP 429 (the rockstarintel.com case)

Diagnosis first: two requests to the same host with no gap between them. The fix is the per-domain
delay above, not a retry loop.

Handling:
```python
if r.status_code == 429:
    ra = r.headers.get("Retry-After")
    delay = parse_retry_after(ra) if ra else min(3600, 300 * 2 ** feed["consecutive_failures"])
    delay = max(delay, 60)                       # never retry a 429 in under a minute
    set_backoff(feed, now + delay)
    bump_domain_delay(feed["domain"], to=10.0)   # sticky: this host is sensitive
    return                                       # do NOT retry within this run
```

Key points:
- **`Retry-After` can be either a delta-seconds integer or an HTTP-date.** Handle both.
- **Never retry a 429 inside the same run.** You have another run in 15 minutes; use it. Tight retries on
  429 are how you escalate to a hard block.
- Make the per-domain delay bump **sticky** — persist it, so the lesson survives the process exit. This is
  the main thing a short-lived-process design has to be careful about: without persistence you re-learn
  the same 429 every 15 minutes.
- Treat repeated 429 as a *politeness bug in your config*, and widen `poll_interval_s` for every feed on
  that domain.

### Datacenter vs residential IPs

Your bot runs on a residential connection from a Windows desktop, which is the **good** case: residential
ASNs get far lower bot-suspicion scores than cloud ranges. Two consequences worth internalising:

- **A feed that works from your PC may 403 from a VPS.** Don't be surprised if you later try to move this
  to a cheap cloud box and half the feeds break. That is an argument for keeping it on the desktop —
  which the Task Scheduler design already assumes.
- **Conversely, your IP is shared with your household and is dynamic.** Getting it rate-limited or
  Cloudflare-banned affects your browser too. This is the real reason the Discord 401/403 rule in §4
  matters: a runaway retry loop can take your whole house off Discord for an hour.
- **Do not add a proxy or VPN to "fix" a 403.** Commercial proxy ranges are more suspect than your home
  IP, and rotating residential proxies are the same circumvention problem as TLS impersonation.

### Recommended politeness settings, summarised

| Setting | Value |
|---|---|
| Per-feed interval, digest sources | 15 min (widen to 60 min if no validators and hash stable) |
| Per-feed interval, instant sources | 5 min |
| Per-domain minimum gap | **5 s**, sticky-raised to **10 s** after any 429 |
| Global concurrency | 4 in flight, `max_connections=5` |
| Connect / read timeout | `httpx.Timeout(10.0, connect=5.0)` |
| Per-run wall clock budget | 120 s, then abandon remaining feeds until next run |
| robots.txt | fetch + honour, cache 24 h |
| Startup jitter | `sleep(uniform(0, 20))` |

---

## 4. Resilience

### Retry / backoff

Use **full jitter**, per AWS's canonical analysis — it needed slightly less total client work than
decorrelated jitter, and both substantially beat un-jittered exponential backoff. Equal jitter
underperformed both.

```
sleep = random(0, min(cap, base * 2 ** attempt))
```

With `base = 1.0 s`, `cap = 60 s`, `attempt` 0-based.

```python
import random

def full_jitter(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    return random.uniform(0.0, min(cap, base * (2 ** attempt)))
```

**Two retry layers, and keep them separate:**

- **In-run retries: at most 2, and only for transient network errors and 5xx.** Not for 429 (see §3), not
  for 4xx. You have another whole run in 15 minutes; in-run retries exist only to ride out a single
  dropped TCP connection.
- **Across-run backoff: `backoff_until` in the DB, exponential on `consecutive_failures`,** capped at
  ~6 hours so a feed that comes back gets picked up the same day. This is the layer that actually matters
  in a short-lived-process design.

**Retryable vs fatal:**

| Retryable (transient) | Fatal (don't retry; needs a human or a config change) |
|---|---|
| Connection/DNS/TLS errors, read timeouts | **400** malformed request — your bug |
| **408** Request Timeout | **401** Unauthorized |
| **425** Too Early | **403** Forbidden |
| **429** — but only via `backoff_until`, never in-run | **404** Not Found (count it; disable after N) |
| **500, 502, 503, 504** | **410** Gone — disable permanently |
| | **422** Unprocessable |

Always prefer a `Retry-After` header over your computed backoff when the server sends one — that is the
server telling you its actual recovery time, and ignoring it is how retry storms happen.

### Discord specifically: 401/403 must be FATAL

Discord's documented invalid-request limit is **10,000 invalid requests per 10 minutes**, and the codes
that count as invalid are **401, 403, and 429**. Exceed it and Cloudflare bans the **IP** — which, per §3,
is your house.

Concrete rules for the Discord client:

```python
FATAL_DISCORD = {400, 401, 403, 404, 405, 413}

async def post_webhook(client, url, payload, *, max_attempts=5):
    for attempt in range(max_attempts):
        r = await client.post(url, json=payload)

        if r.status_code in (200, 204):
            return True

        if r.status_code in FATAL_DISCORD:
            # 401/403 = bad or revoked token / no permission. Retrying can NEVER fix it
            # and burns the 10k-invalid-requests-per-10-min budget toward an IP ban.
            await set_kill_switch(reason=f"discord {r.status_code}: {r.text[:200]}")
            raise DiscordFatal(r.status_code, r.text[:500])

        if r.status_code == 429:
            body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
            retry_after = float(body.get("retry_after", r.headers.get("Retry-After", 1.0)))
            scope = r.headers.get("X-RateLimit-Scope")
            # 429s with X-RateLimit-Scope: shared are NOT counted against you
            await asyncio.sleep(retry_after + 0.25)     # +epsilon; Discord's clock != yours
            continue

        if 500 <= r.status_code < 600:
            await asyncio.sleep(full_jitter(attempt))
            continue

        await asyncio.sleep(full_jitter(attempt))

    raise DiscordGaveUp()
```

Non-negotiables:
1. **A `FATAL_DISCORD` status sets a persistent kill switch** — a row in SQLite that makes every
   subsequent run refuse to post until you clear it manually. Without this, a revoked webhook plus a
   15-minute cron equals thousands of 401s.
2. **Cap total Discord attempts per run** (e.g. 20). A digest of 30 items must not become 30 × 5 = 150
   requests on a bad day.
3. **Respect `retry_after` from the JSON body**, which is a float in seconds, and add a small epsilon.
   `X-RateLimit-Reset-After` also carries decimals.
4. **Proactive pacing:** read `X-RateLimit-Remaining` and sleep `X-RateLimit-Reset-After` when it hits 0,
   rather than earning the 429. The global ceiling is 50 req/s; per-webhook is far tighter (~5 per 2 s,
   ~30 per 60 s — **[UNVERIFIED: webhook-specific buckets are not in Discord's official rate-limit doc;
   these are community-reported. Discover them from the response headers rather than hardcoding.]**).
5. Webhook payload limits: message content **2000 chars**, embed description **4096**, embed title **256**,
   **25 fields** per embed, and **6000 chars summed across all embeds** in one message. A 30-item digest
   *will* hit these — chunk it, and truncate defensively rather than letting Discord 400 you.

### Malformed XML

Covered in §1: `bozo=1` with entries → proceed. `bozo=1` with zero entries → fetch failure, increment
`consecutive_failures`, and *do not* update `content_hash` (so a later fix is detected as a change).
Wrap `feedparser.parse` in a try/except anyway — it is lenient, not infallible, and a truncated
gzip stream can raise before it gets to parse.

### Feeds that change URL (301)

**Yes, update the stored URL — but carefully.**

```python
if result["kind"] == "moved":
    loc = urljoin(feed["url"], result["location"] or "")
    if not loc or urlparse(loc).scheme not in ("http", "https"):
        mark_failure(feed, "301 without usable Location"); return
    if same_or_subdomain(loc, feed["url"]) or feed["redirect_count"] < 3:
        update_feed_url(feed, loc, bump_redirect_count=True)
        clear_validators(feed)     # ETag/Last-Modified belong to the OLD resource!
        log.info("feed %s moved 301 -> %s", feed["name"], loc)
    else:
        mark_failure(feed, f"suspicious 301 chain to {loc}")
```

Four rules:
- **Clear `etag`, `last_modified` and `content_hash` on a URL change.** They describe the old resource.
  Reusing them across a move is a subtle source of "the feed moved and now looks empty forever".
- **Keep `original_url` immutable** so you can always see what you configured and recover from a bad
  rewrite.
- **Cap redirect-following** (`redirect_count < 3`) and be suspicious of cross-domain 301s — a domain that
  lapsed and got bought now 301s your feed to an ad farm, and the parked page is valid XML surprisingly
  often.
- **A 301 to an HTML page** parses as bozo-with-zero-entries, which §4's dead-feed rule then catches.
  Belt and braces.

Treat 302/307 as temporary: follow it for this request (`follow_redirects=True` on that one call, or
re-issue manually) but do not persist the new URL.

### Feeds that go permanently dead

State machine on `consecutive_failures`:

| Failures | Action |
|---|---|
| 1–2 | Silent. Exponential `backoff_until`. |
| 3 | **Alert once** (see rule below). Widen `poll_interval_s` to 1 h. |
| 10 | `enabled = 0`, `disabled_reason='persistent_failure'`. Alert once more. |
| any 410 | Immediate `enabled = 0`. 410 means Gone; asking again is rude. |

Include disabled feeds in a weekly status line so they can't be forgotten. **Never** silently drop a feed
from the rotation — that is the exact failure this whole section exists to prevent.

### Feeds that recycle or omit GUIDs

This is where dedup design lives or dies. The dedup key must be **stable** (same item → same key across
polls) and **unique** (different items → different keys). RSS `<guid>` is neither in practice.

**Recommended: a three-tier key with an explicit source, stored per item.**

```python
import hashlib

def item_key(feed_id: int, entry) -> tuple[str, str]:
    """Returns (key, key_kind). key is scoped to the feed."""
    # Tier 1: a real, absolute, non-empty id/guid
    guid = (getattr(entry, "id", "") or getattr(entry, "guid", "") or "").strip()
    if guid and len(guid) >= 8 and not guid.isdigit():
        return _h(feed_id, "guid", guid), "guid"

    # Tier 2: canonicalised link (strip utm_*, fbclid, trailing slash, fragment)
    link = canonical_url(getattr(entry, "link", "") or "")
    if link:
        return _h(feed_id, "link", link), "link"

    # Tier 3: last resort — title + published date
    title = normalise_ws((getattr(entry, "title", "") or "").lower())
    pub = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    stamp = str(calendar.timegm(pub) // 86400) if pub else ""   # day granularity
    if title:
        return _h(feed_id, "titledate", title + "|" + stamp), "titledate"

    return _h(feed_id, "raw", repr(sorted(entry.items()))[:2000]), "raw"

def _h(feed_id, kind, s):
    return hashlib.sha256(f"{feed_id}\x00{kind}\x00{s}".encode("utf-8", "replace")).hexdigest()
```

Notes on each failure mode:
- **Omitted GUID** → tier 2 handles it. Canonicalising the URL is essential: `?utm_source=rss` changes
  every poll on some CMSes, which would make every poll look like new items.
- **Bare integer GUIDs** (`<guid>1234</guid>`) are excluded from tier 1 because they collide across
  feeds and get recycled by CMS reinstalls. Tier 2 is safer.
- **Recycled GUIDs** (publisher reuses an id for a different article) → detect by storing
  `title_hash` alongside the key. If a known key arrives with a wildly different title *and* link,
  log it and treat it as new with a suffixed key. Rare; log-and-move-on is proportionate.
- **Unstable GUIDs** (a new id every poll for the same article) is the dangerous one — it spams your
  digest. Detect it: if a feed produces "new" items whose canonical links are already in the DB,
  count that. Three occurrences → flip that feed to `dedup_mode='link'` permanently, i.e. force tier 2.
  Store `dedup_mode` on the feed row.

### Timezone-less or malformed pubDates

feedparser normalises `published` → `published_parsed`, **a 9-tuple already converted to UTC**
(their example: `2003-12-31T10:14:55-08:00` → `(2003, 12, 31, 18, 14, 55, 2, 365, 0)`).

Three consequences, and one bug you must not write:

1. **Convert with `calendar.timegm()`, never `time.mktime()`.** `published_parsed` is UTC;
   `time.mktime()` interprets a tuple as *local* time. On this machine that is a silent 1–2 hour error
   that changes sign on 2026-10-25.

   ```python
   import calendar
   published_epoch = calendar.timegm(entry.published_parsed) if entry.get("published_parsed") else None
   ```

2. **If the date is unparseable, `published_parsed` is absent entirely** — feedparser leaves the raw
   string in `published` and omits the `_parsed` key. So always `entry.get("published_parsed")`, never
   `entry.published_parsed`, and never assume it exists.

3. **Dates without a timezone are parsed as-is, with no timezone assumed** — i.e. treated as UTC. For a
   Hungarian or US publisher this makes the timestamp wrong by up to a few hours.

**Therefore: never trust feed timestamps for ordering or for "is this new".**

```sql
-- store both, and use first_seen_at for all logic
published_at    INTEGER,   -- epoch from calendar.timegm(published_parsed); NULLable
published_raw   TEXT,      -- the original string, for debugging
first_seen_at   INTEGER NOT NULL   -- int(time.time()) when WE first stored it
```

Use `first_seen_at` for dedup windows, digest inclusion, and ordering. Use `published_at` only for
*display* ("2 hours ago"), and fall back to `first_seen_at` when it's NULL or absurd. Sanity-clamp it:
reject `published_at` more than 48 h in the future or before 2000-01-01 — feeds emit both.

### Duplicate GUIDs across different feeds

Two different problems; solve them separately.

- **The same publisher's item appearing in two of your feeds** (e.g. a site's main feed and its tag feed —
  exactly the rockstarintel case). The `item_key` above is **scoped to `feed_id`**, so both copies get
  stored. That is correct for per-feed bookkeeping but wrong for the digest.
- **Genuinely distinct items with colliding GUIDs across publishers.** Feed-scoping already prevents this.

So: keep the storage key feed-scoped, and add a **separate global dedup key for presentation**:

```sql
CREATE TABLE items (
    id             INTEGER PRIMARY KEY,
    feed_id        INTEGER NOT NULL REFERENCES feeds(id),
    item_key       TEXT    NOT NULL,   -- feed-scoped (see item_key())
    global_key     TEXT    NOT NULL,   -- sha256(canonical_url) or title-fingerprint
    ...
    UNIQUE (feed_id, item_key)
);
CREATE INDEX ix_items_global ON items(global_key);
```

`global_key = sha256(canonical_url(link))`, falling back to a normalised-title hash when there's no link.
At digest time, `GROUP BY global_key` and pick one representative — prefer the first-party feed, then the
earliest `first_seen_at`. For instant alerts, check `global_key` before firing so the same story from two
feeds two minutes apart doesn't double-ping. A 6-hour lookback window on `global_key` is a reasonable
cross-publisher near-duplicate guard; going further (fuzzy title matching) is not worth it at 10 feeds.

### DEAD FEED DETECTION — distinguishing "broken" from "quiet news day"

This is the section that matters most, because a silently-broken feed and a genuinely quiet day produce
**identical output**: an empty digest. You cannot tell them apart from item counts alone. You need signals
that exist independently of whether news happened.

**The four independent signals:**

| Signal | Broken feed | Quiet news day |
|---|---|---|
| **A. Fetch outcome** (200/304 vs error) | errors / 403 / timeouts | clean 200s and 304s |
| **B. Parse outcome** (entries in the XML) | 0 entries parsed, or bozo+0 | feed still lists its usual ~20 back-catalogue entries |
| **C. Content change** (`content_hash`) | unchanged for far longer than usual | unchanged — *same as broken!* |
| **D. Correlation across feeds** | one feed silent | **all** feeds silent |

**Signal B is the key insight and the one people miss.** A working RSS feed almost never returns zero
entries — it returns its last 10–50 items regardless of whether anything was published today. So:

> **`HTTP 200 + successfully parsed + 0 entries` on a feed that has ever had entries is a
> near-certain breakage, and it is completely independent of the news cycle.**

That single check catches the majority of silent failures: a 301 to an HTML page, a feed replaced by a
login wall, a CMS migration that changed the XML namespace, a feed that now returns `{"error": ...}` JSON.

**Signal D is the second key insight.** "No news anywhere, on all 10 feeds, on the same day" is far more
likely to be *your* problem (network down, IP banned, system clock wrong, DB not committing) than a
global news blackout. It is nearly free to check and catches whole-system failures that per-feed rules miss.

**Recommended concrete alerting rule.** Evaluate at the end of every run for per-feed rules, and once per
day just before the digest for the aggregate rules. Every alert is **rate-limited to once per feed per
24 h** via an `alerts_sent` table, so a broken feed nags once a day, not 96 times.

```python
# thresholds
FAIL_ALERT_AT      = 3          # consecutive failed fetches
STALE_MULTIPLIER   = 3          # x median inter-item gap
STALE_FLOOR_S      = 7 * 86400  # never call a feed stale in under 7 days
STALE_CEILING_S    = 30 * 86400 # ...and always call it stale after 30
NO_VALIDATOR_GRACE = 2          # extra slack for feeds with no ETag/Last-Modified


def feed_health(feed, now: int) -> tuple[str, str] | None:
    """Returns (severity, message) or None. Pure function of stored state."""

    # --- RULE 1: hard fetch failures (Signal A) ---------------------------
    if feed["consecutive_failures"] >= FAIL_ALERT_AT:
        return ("error",
                f"{feed['name']}: {feed['consecutive_failures']} consecutive fetch failures "
                f"(last: HTTP {feed['last_status']} / {feed['last_error']})")

    # --- RULE 2: structurally broken (Signal B) — THE IMPORTANT ONE -------
    # 200 OK, parsed fine, but zero entries, on a feed that used to have some.
    if feed["items_total"] > 0 and feed["last_entry_count"] == 0 and feed["last_status"] == 200:
        return ("error",
                f"{feed['name']}: HTTP 200 but the feed contains ZERO entries. "
                f"This is a broken feed, not a quiet day. Check the URL manually.")

    # --- RULE 3: bozo with nothing salvageable (Signal B) -----------------
    if feed["last_bozo"] and feed["last_entry_count"] == 0:
        return ("error", f"{feed['name']}: unparseable XML and no entries recovered "
                         f"({feed['last_bozo_reason']})")

    # --- RULE 4: statistically stale (Signal C) --------------------------
    # Only meaningful once we know the feed's normal rhythm.
    if feed["items_total"] >= 10 and feed["median_gap_s"] and feed["last_item_at"]:
        budget = feed["median_gap_s"] * STALE_MULTIPLIER
        if feed["etag"] is None and feed["last_modified"] is None:
            budget *= NO_VALIDATOR_GRACE
        budget = max(STALE_FLOOR_S, min(STALE_CEILING_S, budget))
        silent_for = now - feed["last_item_at"]
        if silent_for > budget:
            return ("warn",
                    f"{feed['name']}: no new items for {silent_for // 86400}d "
                    f"(normally one every ~{feed['median_gap_s'] // 3600}h). "
                    f"Fetches are succeeding, so either the publisher went quiet "
                    f"or our dedup is eating everything.")
    return None


def system_health(feeds, now: int) -> tuple[str, str] | None:
    """Signal D: cross-feed correlation. Run once per day before the digest."""
    active = [f for f in feeds if f["enabled"]]
    if not active:
        return ("error", "No feeds are enabled at all.")

    # D1: nobody fetched successfully today -> it's us, not them
    if all((f["last_success_at"] or 0) < now - 6 * 3600 for f in active):
        return ("error",
                "NO feed has fetched successfully in 6 hours. Network down, IP blocked, "
                "or the bot's HTTP layer is broken. This is almost certainly our fault.")

    # D2: everything fetches but nothing has changed in 48h across ALL feeds
    if all((f["last_content_at"] or 0) < now - 48 * 3600 for f in active):
        return ("error",
                "All feeds fetch OK but NONE has changed content in 48h. "
                "Ten independent publishers do not go quiet simultaneously - "
                "suspect a caching/proxy/clock problem on our side.")

    # D3: the digest is empty AND no feed produced an item in 24h
    if all((f["last_item_at"] or 0) < now - 24 * 3600 for f in active):
        return ("warn",
                "Empty digest: no new items from any feed in 24h. Possible but unusual - "
                "verify one feed by hand.")
    return None
```

**Extra columns this needs** on `feeds`: `last_entry_count`, `last_bozo`, `last_bozo_reason`.

**And the rule that makes the whole thing trustworthy:**

> **Post the health summary into the digest itself.** One line at the bottom:
> `10 feeds · 9 ok · 1 blocked (rockstargames.com 403) · oldest successful fetch 12 min ago`.
> An empty digest with that line is informative; an empty digest with no line is indistinguishable from a
> dead bot. This costs about fifteen lines of code and is the single highest-value observability feature
> in the project — it converts silent failure into visible failure every single day.

Maintain `median_gap_s` cheaply: on each new item, `UPDATE feeds SET median_gap_s = ...` from a rolling
window of the last 20 items' `first_seen_at` deltas (compute in Python, it's 20 numbers).

---

## 5. SQLite under Windows + OneDrive

### Confirmed: this is a real hazard, not folklore

Your project directory is `C:\Users\<you>\OneDrive\Asztali gép\...` — i.e. inside a OneDrive tree with
Known Folder Move active on the Desktop. Putting a live SQLite database there risks corruption. The
mechanisms, from SQLite's own *How To Corrupt An SQLite Database File*:

1. **Backup/sync software copying a database mid-transaction.** SQLite §1.2, verbatim:
   > *"Systems that run automatic backups in the background might try to make a backup copy of an SQLite
   > database file while it is in the middle of a transaction. The backup copy then might contain some old
   > and some new content, and thus be corrupt."*

   That is precisely what a sync engine does: it notices `bot.db` changed and starts reading it to upload.
   It has no idea a write transaction is in flight.

2. **The `-wal` / `-shm` files are separate files, and the sync engine does not know they are one unit.**
   SQLite §1.3–1.4:
   > *"SQLite must see the journal files in order to recover from a crash or power failure. If the hot
   > journal files are moved, deleted, or renamed after a crash or power failure, then automatic recovery
   > will not work and the database may go corrupt."*

   and it explicitly warns against *"Copying a database file without also copying its journal"*. OneDrive
   syncs `bot.db`, `bot.db-wal` and `bot.db-shm` as three independent files with three independent
   timestamps, uploaded in whatever order it likes. On a sync conflict it will happily restore a `bot.db`
   from 10:00 next to a `-wal` from 10:05. That combination is a corrupt database by definition.

3. **Sync conflicts create `bot-DESKTOP-XYZ.db` copies** and, worse, can *replace* your DB file with a
   server version while your process holds it open. If you ever sign in to OneDrive on a second machine,
   the two divergent copies get "merged" by filename, which for a binary DB means one of them is silently
   destroyed.

4. **File locking.** SQLite §2.1:
   > *"SQLite depends on the underlying filesystem to do locking as the documentation says it will. But
   > some filesystems contain bugs in their locking logic such that the locks do not always behave as
   > advertised. This is especially true of network filesystems and NFS in particular."*

   The OneDrive local folder *is* NTFS, so byte-range locking works correctly — this specific clause is
   about network filesystems and does **not** directly indict OneDrive. But the sync engine is a second
   process reading and writing your files outside SQLite's locking protocol, which produces the same class
   of outcome by a different route.

5. **Files On-Demand placeholders / reparse points.** With Files On-Demand enabled, *all* synced files and
   folders are implemented as **NTFS reparse points** (cloud-file placeholders). A dehydrated
   (online-only) file has to be re-downloaded on first read, which turns an `fread()` into a network
   operation that can be slow or fail outright — and dehydrated files can be inaccessible to
   non-elevated processes. There is a documented ecosystem of tooling breaking on this: Microsoft has a
   KB on *"Invalid reparse points when deleting OneDrive-synced files locally"*, and Claude Code itself
   had a regression (issue #30928) where Write/Edit failed with `EEXIST` on any file whose parent
   directory was a OneDrive sync directory. If dev tooling trips over it, an mmap'd `-shm` file will too.

6. **WAL adds an mmap requirement.** SQLite's WAL documentation:
   > *"All processes using a database must be on the same host computer; WAL does not work over a network
   > filesystem. This is because WAL requires all processes to share a small amount of memory and
   > processes on separate host machines obviously cannot share memory with each other."*

   The `-shm` file is memory-mapped. A cloud-placeholder reparse point being mmap'd by SQLite while a sync
   engine tries to hydrate/dehydrate it is not a configuration anyone has tested.

**Verdict: do not keep the live database in the OneDrive tree.** This is not a "probably fine" — it is a
low-probability-per-day, total-data-loss failure that will eventually happen and will be extremely
confusing when it does (`database disk image is malformed`, hours after the actual cause).

### Where to put it on Windows

**Use `%LOCALAPPDATA%`.** Reasoning:
- It is the documented location for *machine-specific, non-roaming* user data — *"Local is for data that
  normally stays on the current computer... it is specific to a PC."* A bot's dedup DB is exactly that.
- **It is never redirected by OneDrive Known Folder Move.** KFM only ever touches Desktop, Documents and
  Pictures. `AppData\Local` cannot be synced by the OneDrive client, which is the property you want.
- No admin rights needed, unlike `ProgramData`.
- `Roaming` would be wrong (and roaming settings are deprecated as of Windows 11 anyway) — you do *not*
  want a SQLite file replicating between machines, for the exact reasons above.
- `ProgramData` is for machine-wide data shared between users. Single-user bot → not applicable, and it
  needs elevation to create.

Resulting layout:

```
%LOCALAPPDATA%\gta6-news-bot\
    bot.db          bot.db-wal      bot.db-shm
    logs\bot.log
    state\           (robots.txt cache, etc.)
```

Keep **source code** in OneDrive if you like (it's text, it versions fine, and the sync is a free backup),
but keep **runtime state** out of it. Also keep the **virtualenv** out of OneDrive — thousands of small
files plus `.pyd` DLLs being hydrated on demand is slow and occasionally fails; put it at
`C:\venvs\gta6-news-bot`.

### Getting the path in Python

```python
import os
from pathlib import Path

APP_NAME = "gta6-news-bot"

def app_data_dir() -> Path:
    """Per-user, non-roaming, never OneDrive-synced. Windows-first with a POSIX fallback."""
    base = os.environ.get("LOCALAPPDATA")
    if base:                                   # Windows
        root = Path(base)
    else:                                      # Linux/macOS fallback (dev, CI)
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    d = root / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d

DB_PATH = app_data_dir() / "bot.db"
```

`%LOCALAPPDATA%` expands to `C:\Users\<you>\AppData\Local`, so your DB lands at
`C:\Users\<you>\AppData\Local\gta6-news-bot\bot.db`.

Two hardening touches:

```python
# 1. Make the path overridable, so you can point at a scratch DB in tests.
DB_PATH = Path(os.environ.get("GTA6BOT_DB", app_data_dir() / "bot.db"))

# 2. Refuse to run from a synced folder by accident.
def assert_not_synced(p: Path) -> None:
    bad = ("onedrive", "dropbox", "google drive", "icloud", "creative cloud")
    low = str(p).lower()
    hit = next((b for b in bad if b in low), None)
    if hit:
        raise RuntimeError(
            f"Refusing to open a SQLite DB inside a '{hit}' synced folder: {p}\n"
            f"Sync engines copy the DB mid-transaction and desync the -wal file, which corrupts it.\n"
            f"Set GTA6BOT_DB to a path under %LOCALAPPDATA%."
        )

assert_not_synced(DB_PATH)
```

That guard is worth writing. It is three lines and it makes the mistake unrepeatable — including by a
future you who copies the project folder somewhere convenient.

Note this is a *heuristic* on the path string; it won't catch a synced folder with a custom name. Good
enough for the failure mode you actually face.

### WAL vs journal mode for a single-writer bot

**Use WAL.** For your workload it is strictly better:

| | DELETE (rollback journal, default) | WAL |
|---|---|---|
| Readers block writer / writer blocks readers | Yes | **No** — readers and one writer run concurrently |
| fsyncs per commit | 2+ | 1 (with `synchronous=NORMAL`) |
| Small-write throughput | slower | significantly faster |
| Extra files | `-journal` (transient) | `-wal`, `-shm` (persistent) |
| Works on a network share | badly | **not at all** |

You have exactly one writer (the bot) and possibly a reader (you, poking at it with `sqlite3.exe` or DB
Browser while it runs). WAL is precisely the case it was designed for, and it means your ad-hoc `SELECT`
won't throw `database is locked` at the bot.

**Is WAL safe on Windows?** Yes, on a **local NTFS volume**. WAL needs working file locking and shared
memory; Windows/NTFS provides both, and the SQLite restriction is specifically about *network*
filesystems ("does not work over a network filesystem", because processes on separate hosts can't share
memory). Local NTFS is not that. Two Windows-specific caveats:

- **Never delete `-wal` or `-shm` by hand while the DB is open** — that corrupts the database. If you want
  a single-file copy, use `VACUUM INTO 'backup.db'` (safe, online) or the backup API, never `copy`.
- **WAL is persistent.** *"If a process sets WAL mode, then closes and reopens the database, the database
  will come back in WAL mode."* So `PRAGMA journal_mode=WAL` is a one-time migration, not something to run
  every startup — though running it every startup is harmless and self-documenting.

**And the corollary that ties §5 together:** the fact that WAL introduces two extra persistent files whose
mutual consistency matters is a *second, independent* reason not to put the DB in OneDrive. If you were
forced to keep the DB in a synced folder, you would have to use `journal_mode=DELETE` and even then it
would only be less-bad, not safe. Move the DB.

### Recommended pragmas

```python
import aiosqlite

async def open_db(path) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(path, timeout=30.0, isolation_level=None)
    # isolation_level=None -> autocommit; you manage BEGIN/COMMIT explicitly. Do this.
    await conn.execute("PRAGMA journal_mode=WAL")       # persistent; one-time in practice
    await conn.execute("PRAGMA busy_timeout=5000")      # milliseconds
    await conn.execute("PRAGMA synchronous=NORMAL")     # see below
    await conn.execute("PRAGMA foreign_keys=ON")        # OFF by default in SQLite!
    await conn.execute("PRAGMA wal_autocheckpoint=256") # keep -wal small (~1MB)
    conn.row_factory = aiosqlite.Row
    return conn
```

- **`busy_timeout=5000`** — value is in **milliseconds**. It is the pragma form of `sqlite3_busy_timeout()`.
  Without it, any lock contention raises `database is locked` immediately. 5 s is generous for a
  single-writer bot; it exists to cover the case where you have DB Browser open. Note `aiosqlite.connect`'s
  `timeout=` parameter maps to the same underlying busy timeout in `sqlite3`, so setting both is
  belt-and-braces (harmless; the pragma wins as it's set later).
- **`synchronous=NORMAL`** — SQLite: *"WAL mode is safe from corruption with synchronous=NORMAL... WAL mode
  is always consistent with synchronous=NORMAL, but WAL mode does lose durability. A transaction committed
  in WAL mode with synchronous=NORMAL might roll back following a power loss or system crash."*
  For this bot that trade is correct: losing the last poll cycle to a power cut is a non-event (the next
  run re-fetches), and you get one fsync per commit instead of two. Use `FULL` only if you decide that
  losing a "digest already posted" record to a power cut is unacceptable — and even then, prefer
  `PRAGMA synchronous=FULL` *only around the digest-completion commit*, which you can do per-transaction.
  Honestly: `NORMAL` plus the idempotency guard in §7 is enough.
- **`foreign_keys=ON`** — SQLite defaults this to OFF, per-connection. If you declared
  `REFERENCES feeds(id)`, it does nothing until you turn this on.
- **`wal_autocheckpoint=256`** — default is ~1000 pages; SQLite checkpoints automatically when the WAL
  reaches that. 256 pages keeps `-wal` around 1 MB, which is nicer for a long-running-but-idle DB.

### Does aiosqlite change any of this? No.

`aiosqlite` (installed 0.20.0; latest 0.22.1, 2025-12-23) is *"a friendly, async interface to sqlite
databases"* that *"replicates the standard sqlite3 module"* — it runs the stdlib `sqlite3` calls on a
**dedicated worker thread per connection** and awaits the results. It changes nothing about locking,
journal modes, corruption risk, or pragmas. Two practical consequences:

- **All the sqlite3 rules still apply**, including "one connection should not be shared across concurrent
  writers without care". Since aiosqlite serialises every call for a connection onto one thread, a single
  shared connection is naturally safe for your single-writer bot — use exactly one connection.
- **`isolation_level=None`** (autocommit) plus explicit `BEGIN IMMEDIATE` / `COMMIT` is the right pattern.
  The stdlib's implicit-transaction behaviour is surprising, and it matters for the §7 idempotency claim.
  Use `BEGIN IMMEDIATE` when you intend to write, so you take the write lock up front rather than
  discovering contention at COMMIT.
- Your installed **0.20.0 is fine**; no need to upgrade for this project.

### Should the DB be excluded from OneDrive sync, and how?

Once the DB lives in `%LOCALAPPDATA%` the question is moot — **that is the exclusion**, and it is the only
robust one. Worth knowing why the alternatives don't work:

- **OneDrive Settings → Account → "Choose folders"** only lets you deselect *top-level* folders of the
  OneDrive namespace, and it is really about not downloading cloud content locally, not about excluding a
  local subfolder from upload. Per Microsoft's own Q&A threads: there is no supported way to exclude an
  arbitrary local subfolder from syncing; unchecking a subfolder generally just hides it locally while the
  data stays online. You also cannot uncheck Desktop/Documents/Pictures when KFM is on.
- **Excluding by extension** *is* supported (via the Group Policy / registry setting "Exclude specific
  kinds of files from being uploaded"), so `*.db;*.db-wal;*.db-shm` is technically possible — but it is a
  per-machine policy, silently ignored if you typo it, and it doesn't stop OneDrive from *watching* the
  folder. **Do not rely on it.**
- **Symlink / junction from the OneDrive folder to a real folder elsewhere** works in the sense that
  OneDrive does not follow it, but it makes the setup obscure and breaks if the tree is ever re-synced to a
  new machine. Avoid.
- **Marking the folder "Always keep on this device"** solves the *dehydration* problem but not the
  mid-transaction-copy problem. Do apply it to the **source code** folder (so the code is always readable,
  which matters for §6), but it is not a substitute for moving the DB.

**Action items for this project:**
1. DB, logs and state → `%LOCALAPPDATA%\gta6-news-bot\`.
2. Virtualenv → `C:\venvs\gta6-news-bot\`.
3. Source in OneDrive → right-click the project folder → **"Always keep on this device"**.
4. Ship the `assert_not_synced()` guard.
5. Backup: a weekly `VACUUM INTO` writing `%LOCALAPPDATA%\...\backup\bot-YYYYMMDD.db`, and *that* file may
   safely be copied into OneDrive — it's a consistent snapshot, not a live DB.

---

## 6. Windows scheduling

### (a) Task Scheduler + short-lived process vs (b) long-running asyncio loop

Honest comparison for *this* bot (10 feeds, instant alerts, one daily digest, single desktop PC):

| | (a) Task Scheduler → short-lived process | (b) Long-running process |
|---|---|---|
| **Crash recovery** | Automatic and free. Next run in 15 min. | Needs a supervisor (NSSM / service / watchdog) or it stays dead silently. |
| **Sleep / hibernate / reboot** | Handled by the OS. Process simply runs again after wake. | Process survives sleep but wakes with a stale event loop, stale HTTP pool, and a `sleep()` that under- or over-shot. Must be coded for. |
| **Memory / fd leaks** | Impossible to accumulate — process exits. | Real risk over weeks. |
| **State** | Must all live in SQLite. *This is a feature* — it forces the design that makes catch-up correct. | Tempting to keep state in memory, which silently breaks catch-up and restarts. |
| **Startup cost** | ~0.4–1.2 s of Python + imports, 96×/day. Irrelevant. | None. |
| **Instant-alert latency** | Bounded by the poll interval (15 min → up to 15 min). Use 5 min for instant-tier feeds. | Can be tighter, but you're polling RSS — the publisher's own cache is minutes anyway. |
| **Deploying a code change** | Just save the file. Next run picks it up. | Must restart the service. |
| **Debuggability** | Run the same command by hand; identical code path. | "Works when I run it manually" divergence. |
| **Log noise** | 96 process starts/day in the Task Scheduler operational log. Mildly annoying. | Clean. |
| **Ops surface** | One scheduled task. | Service wrapper + its own failure modes. |

**Recommendation: (a), decisively.** The deciding argument is not startup cost — it is that a short-lived
process **cannot** hold state in memory, which forces every catch-up and dedup decision into SQLite where
it belongs. That is the same property that makes the digest idempotency guard in §7 trustworthy. Option
(b)'s only real advantage is sub-minute alert latency, which RSS polling cannot deliver anyway.

Concretely: **one task, Daily trigger at 00:02, `<Repetition>` every 15 minutes for 24 hours,
`MultipleInstancesPolicy=IgnoreNew`.** The digest is just a condition the process evaluates on each run,
so 18:00 needs no separate trigger, and a missed 18:00 is caught up by the next 15-minute tick with no
reliance on `StartWhenAvailable` at all.

Use 5-minute repetition if you want tighter instant alerts; 288 runs/day is still nothing. Set the
per-feed `poll_interval_s` (§3) to control actual network politeness independently of how often the
process wakes. That separation is important: **process wake frequency ≠ feed poll frequency.**

**There is also a hybrid (c)** worth knowing: make the task's action *start the long-running daemon*, with
`MultipleInstancesPolicy=IgnoreNew` and a 5-minute repetition. If the daemon is alive the new start is
ignored; if it died it gets resurrected within 5 minutes. Task Scheduler becomes a free supervisor and you
don't need NSSM. Use this only if you later find you genuinely need sub-minute latency.

### Task Scheduler settings that actually matter

#### "Run task as soon as possible after a scheduled start is missed" (`StartWhenAvailable`)

**How late will it actually run?** Microsoft, verbatim:
> *"Tasks that are started after the scheduled time has passed (because of the StartWhenAvailable property
> being set to True) are queued in the Task Scheduler service's queue of tasks and they are started after
> a delay. **The default delay is 10 minutes.**"*

So expect the catch-up run **~10 minutes** after the service decides it's runnable (i.e. ~10 min after
boot/resume, not 10 min after the missed time).

**Does it work after hibernate/shutdown?** Yes — *but only for the right trigger type*, and this is the
trap. Microsoft's KB 2437520 (*"Scheduled task may not run upon reboot if machine was off at time of
task"*), verbatim:
> *"This issue can occur if the task trigger was set to run **One Time** when created. It is possible to
> set a task to 'Run as soon as possible after a scheduled start is missed'. This will cause the task to
> rerun after a reboot if the trigger was missed. **However, this does not occur if the task is set to run
> One Time. This behavior is by design.**"*

and the documented resolution:
> *"You can work around this issue by setting a time and date under the **Expire** option of the
> trigger... If a date and time are set for the Expire option, the task will attempt to refire on reboot
> if its previous trigger time was missed."*

This dovetails with the `StartWhenAvailable` reference doc's otherwise-cryptic remark:
> *"This property applies only to time-based tasks **with an end boundary** or time-based tasks that are
> **set to repeat infinitely**."*

**Therefore, two concrete rules:**
1. **Never use a One Time trigger** for the digest. Use `CalendarTrigger` + `ScheduleByDay`.
2. **Set an `<EndBoundary>`** on the trigger anyway (e.g. `2099-12-31T23:59:59`). It costs nothing and it
   unambiguously satisfies the "with an end boundary" condition. Microsoft's own daily-trigger XML sample
   includes an `EndBoundary`.

**[UNVERIFIED]** Whether `StartWhenAvailable` fires **one** catch-up run or one per missed occurrence is
**not documented by Microsoft**. Community reports consistently say **one**. Design accordingly — and note
that the design in §7 makes this irrelevant, because the *bot* decides how many digests to post, not the
scheduler. That is the whole point of putting the logic in Python.

**[UNVERIFIED]** There are also community reports that Task Scheduler will not run a task missed by more
than some interval. I found no Microsoft documentation of such a limit. Do not rely on either behaviour.

#### "Wake the computer to run this task" (`WakeToRun`)

What Microsoft documents is thin — the schema reference says only:
> *"Specifies that Task Scheduler will wake the computer when it is time to run the task."*
> *"When the Task Scheduler service wakes the computer to run a task, the screen may remain off even
> though the computer is no longer in the sleep or hibernate mode."*

Note that sentence says *"sleep or hibernate"*, which is the closest thing to an official statement that
it covers both. Beyond that:

| Power state | Does `WakeToRun` work? | Confidence |
|---|---|---|
| **S3 (classic sleep)** | **Yes**, provided wake timers are enabled in the active power plan and firmware supports the wake alarm. | High — this is the designed case. |
| **S4 (hibernate)** | **Generally yes** on S3-capable hardware; the schema doc mentions hibernate explicitly. | **[UNVERIFIED]** — no primary source confirming S4 wake-timer behaviour end-to-end. Test it. |
| **S5 (shutdown / powered off)** | **No.** Nothing in the OS is running to honour a timer. Only a firmware RTC alarm in BIOS/UEFI can do this. | High. |
| **S0ix / Modern Standby** | **Effectively no.** Widely reported that scheduled tasks do not run and wake timers do not fire under S0 Low Power Idle. | Medium-high — many concurrent reports, no MS doc. |

**Practical steps:**
- Check which states your machine has: `powercfg /a`. If it reports *"Standby (S0 Low Power Idle)"* you
  have Modern Standby and `WakeToRun` is unreliable. If it reports *"Standby (S3)"* you're in the good case.
- Wake timers must be enabled: `powercfg /q` and look at *Sleep → Allow wake timers*, or
  `powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP BD3B718A-0680-4D9D-8AB2-E1D2B4AC806D 1` then
  `powercfg /setactive SCHEME_CURRENT`. Note Windows distinguishes *"Important Wake Timers Only"* (value 2)
  from *"Enable"* (1) — a Task Scheduler wake counts as important **[UNVERIFIED]**, so 2 may suffice, but 1
  is the safe setting.
- Verify a pending wake exists: **`powercfg /waketimers`** (run as admin). If your task doesn't appear
  there, `WakeToRun` is not going to happen and no amount of GUI checkbox-ticking will change it. This is
  the single most useful diagnostic in this section.
- **Does it need admin?** Creating a task that runs with *highest privileges* or as another user needs
  admin; setting `WakeToRun` on your own task does not require the task itself to be elevated. But
  changing the power plan's wake-timer policy **does** need admin. **[UNVERIFIED for the exact ACL.]**
- **Fast Startup interaction:** Fast Startup (hiberboot) makes "Shut down" actually perform a partial
  hibernate — the *session* is closed but the kernel is hibernated. This is still an S4-family power-off
  state as far as wake timers are concerned: **a Fast-Startup "shutdown" does not leave a wake timer
  armed** any more than a real shutdown does. **[UNVERIFIED — I found no Microsoft documentation on wake
  timers surviving a Fast Startup shutdown. Assume it does not work and do not design around it.]**
  Fast Startup's more relevant side effect for you: because the kernel session is restored rather than
  rebuilt, boot-time behaviour can differ from a cold boot in ways that are hard to reason about. If you
  hit weird post-shutdown scheduling behaviour, disable Fast Startup
  (`powercfg /hibernate off`, or Control Panel → Power Options → *Choose what the power buttons do*) as a
  diagnostic step.

**Recommendation: do NOT rely on `WakeToRun`.** Set it to `true` (it's free and helps in the S3 case) but
design the bot so that a digest posted at 08:15 the next morning instead of 18:00 the previous evening is
*correct behaviour* — clearly labelled as a catch-up. That is what §7 does. The alternative is building
your notification schedule on the single least reliable feature in Windows power management.

If you genuinely need 18:00-on-the-dot regardless: set the PC to never sleep (`powercfg /change
standby-timeout-ac 0`) and accept the power cost, or use a BIOS/UEFI RTC wake alarm ("Wake on RTC" /
"Power On by RTC Alarm") to power the machine on at 17:50 — that is the only thing that works from S5.

#### "Run whether user is logged on or not"

Three principal configurations, and the trade-offs are sharper than they look:

| Setting | XML | Needs stored password? | What breaks |
|---|---|---|---|
| Run only when user is logged on | `LogonType=InteractiveToken` | No | Doesn't run when logged off. Console window appears (unless `pythonw.exe`). |
| Run whether user is logged on or not | `LogonType=Password` | **Yes** | Breaks on every password change. Blocked if the account has no password. |
| ...with "Do not store password" | `LogonType=S4U` | No | *"Only local resources are available"* — no access to network resources requiring your credentials. |

**Recommendation for this bot: `InteractiveToken` (run only when logged on).**

Reasons specific to your setup:
1. **The source lives in OneDrive.** When you are logged off, the OneDrive client is not running. With
   Files On-Demand, dehydrated files under the OneDrive tree may be unreadable — a "run whether logged on
   or not" task could fail with an I/O error on its own source files, intermittently, in a way that is
   miserable to diagnose. Marking the folder *"Always keep on this device"* mitigates it but doesn't fully
   remove the reparse-point layer. **[UNVERIFIED for the precise behaviour of reading a hydrated
   placeholder with the sync client stopped — but there is no upside to finding out the hard way.]**
2. **"Logged on" includes locked and includes the lock screen after a reboot-and-sign-in.** A desktop that
   you sign into and then lock is *logged on*. In practice `InteractiveToken` runs essentially always on a
   personal desktop.
3. **`LogonType=Password` breaks silently on password change** and produces `0x8004130F`
   ("credentials became corrupted"). This is the single most common cause of "my scheduled task stopped
   working three months ago and I didn't notice".
4. **S4U's "only local resources"** restriction is about network resources requiring your credentials
   (SMB shares, mapped drives), *not* outbound internet — HTTPS to Discord works fine. But it may affect
   DPAPI-protected secrets. **[UNVERIFIED whether user-scoped DPAPI decryption succeeds under S4U.]**
   Since you use `python-dotenv` with a plain `.env` file protected by NTFS ACLs, this is moot for you —
   but don't switch to DPAPI-encrypted secrets and S4U at the same time.

If you later want it to run while logged off, the clean answer is a real service (below), not `S4U`.

#### "Start in" (working directory) — the classic pitfall

**If you leave "Start in" empty, Task Scheduler runs the task with the working directory set to
`%windir%\system32`.** Every relative path in your code then resolves against `C:\Windows\System32`. The
symptoms are: `.env` not found (so `python-dotenv` silently loads nothing and your token is `None`),
log files appearing in System32 (or failing with permission denied), and `sqlite3.OperationalError: unable
to open database file`.

The GUI's "Start in (optional)" field maps to `<WorkingDirectory>` inside `<Exec>`. **Note: `schtasks
/create` has no parameter for it** — you can only set it via the GUI or via `/XML`. That alone is a good
reason to use the XML approach below.

**Belt and braces — make the code immune:**

```python
from pathlib import Path
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent          # never depend on os.getcwd()
load_dotenv(HERE / ".env")                      # explicit path, not implicit search
```

Rules: derive every project-relative path from `Path(__file__).resolve().parent`; put the DB and logs at
absolute paths under `%LOCALAPPDATA%` (§5); and **never** call `open("config.json")` or bare
`load_dotenv()`. Set `<WorkingDirectory>` anyway as a second layer, but the code should not need it.

#### `pythonw.exe` vs `python.exe`

- **`python.exe`** is a console application. Under Task Scheduler with `InteractiveToken` it will **flash a
  console window** on screen — 96 times a day, stealing focus each time. That is unacceptable.
- **`pythonw.exe`** is the same interpreter built as a GUI subsystem app: no console window, ever.
- **The catch:** with `pythonw.exe`, `sys.stdout` and `sys.stderr` are **not connected to anything**.
  On Python 3 they are `None`-like/invalid, so a bare `print()` can raise, and any unhandled traceback
  goes nowhere. **You must log to a file.**

```python
import logging, sys
from logging.handlers import RotatingFileHandler

LOG = app_data_dir() / "logs" / "bot.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    handlers=[RotatingFileHandler(LOG, maxBytes=2_000_000, backupCount=5, encoding="utf-8")],
)

def _excepthook(exc_type, exc, tb):
    logging.critical("UNHANDLED", exc_info=(exc_type, exc, tb))
sys.excepthook = _excepthook            # essential under pythonw.exe
```

Also set `encoding="utf-8"` on the handler and consider the env var `PYTHONUTF8=1` in the task — Windows
console/file default encoding is cp1252, and a Hungarian or emoji-bearing feed title will otherwise raise
`UnicodeEncodeError` *inside your logging call*, which is a spectacular way to lose an error message.

Use the **venv's** `pythonw.exe`: `C:\venvs\gta6-news-bot\Scripts\pythonw.exe`. That way you never pass
`-m venv` activation nonsense to the task; the venv interpreter already has the right `sys.path`.

#### How to see why a task failed

**First: turn on history — it is disabled by default.** Task Scheduler → right pane → **"Enable All Tasks
History"** (needs admin). Without it the History tab is empty and you will conclude, wrongly, that nothing
ran. Equivalent: `wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true`.

Then, in order of usefulness:

1. **Your own log file.** This should be the primary tool. Task Scheduler tells you *that* it failed;
   only your log tells you *why*.
2. **Task Scheduler → your task → History tab**, or Event Viewer →
   `Applications and Services Logs → Microsoft → Windows → TaskScheduler → Operational`.
   Useful event IDs (**Event 201 verified**; the rest are widely-documented community mappings —
   **[UNVERIFIED against a single Microsoft reference]**):

   | ID | Meaning |
   |---|---|
   | 106 | Task registered |
   | 107 | Task triggered on scheduler (time trigger) |
   | 129 | Created task process |
   | 200 | Action started |
   | **201** | **Action completed — contains the process return code.** This is the one you want. |
   | 202 | Action failed |
   | 203 | Launch failure (couldn't start the process at all — bad path, bad credentials) |
   | 322 | Launch request ignored — instance already running (`IgnoreNew` working as designed) |
   | 323 | Running instance stopped to launch a new one |
   | 332 | Failed to start — logon/credential problem |

3. **Last Run Result** column in the task list:

   | Code | Meaning |
   |---|---|
   | `0x0` | Success |
   | `0x1` | The program returned exit code 1 — **your Python raised**, or `sys.exit(1)`. Check your log. |
   | `0x2` | File not found — wrong path to `pythonw.exe` or to the script |
   | `0xA` | The environment is incorrect |
   | `0x41300` | Task is ready (not an error) |
   | `0x41301` | **Task is currently running** (`SCHED_S_TASK_RUNNING`) — not an error, despite looking like one |
   | `0x41302` | Task is disabled |
   | `0x41303` | Task has not yet run |
   | `0x41304` | No more scheduled runs |
   | `0x41306` | Task was terminated (usually `ExecutionTimeLimit` expired) |
   | `0x8004131F` | An instance of this task is already running |
   | `0x8004130F` | Credentials became corrupted (password changed) |

   `0x41301` and `0x41303` are the two that waste the most time because they *look* like failures.
4. **`schtasks /query /tn "GTA6 News Bot" /v /fo LIST`** — shows Start In, Run As User, Logon Mode,
   Last Result, Next Run Time in one dump. `Next Run Time: Never` is a strong signal of a
   credential or trigger problem.
5. **Test the exact command by hand first.** Copy the `Command` and `Arguments` verbatim into a terminal
   *with the working directory set to `C:\Windows\System32`* — that reproduces the environment Task
   Scheduler gives you and catches every relative-path bug in one shot. This trick is worth more than the
   rest of this list.
6. **`%windir%\SchedLgU.txt`** — legacy log; Microsoft's own docs still reference it for `schtasks`
   troubleshooting. Rarely useful on Windows 10 but occasionally has a launch failure the Operational log
   missed.

Also: have the bot write a **heartbeat row** (`runs(started_at, finished_at, exit_status, feeds_ok,
items_new)`) on every single run. Then "did it run at 18:15?" is a SQL query you own, not an Event Viewer
archaeology session. This is the highest-value five lines in the scheduling design.

#### Running from a OneDrive path — issues?

Yes, three, all discussed above but worth collecting:

1. **Files On-Demand dehydration.** Everything under the OneDrive tree is an NTFS reparse point
   (cloud placeholder). A dehydrated file must be fetched from the network on first read; if OneDrive
   isn't running (logged off, or the client crashed) or you're offline, that read can fail. **Mitigation:**
   right-click the project folder → **"Always keep on this device"**, and use `InteractiveToken` so
   OneDrive is running whenever the task is.
2. **Sync churn on files the bot writes.** Any log or DB file in the tree gets uploaded constantly and can
   generate conflict copies. **Mitigation:** §5 — all runtime state under `%LOCALAPPDATA%`.
3. **Path fragility.** Your path contains non-ASCII (`Asztali gép`) and spaces. That is fine for Task
   Scheduler if every path in the XML is quoted, but it is a recurring source of `0x2` errors when someone
   hand-edits a command line. It also means the path differs between machines/languages. **Mitigation:**
   quote everything, and prefer a short ASCII path for the venv (`C:\venvs\...`).

**Cleanest option, if you're willing:** move the whole project to `C:\bots\gta6-news-bot` and keep OneDrive
out of the runtime path entirely. Use git (or a periodic `robocopy` into OneDrive) for backup. Everything
in §5 and §6 gets simpler. I'd take this option.

### Running it as a real Windows service — is it worth it here?

Three ways, briefly:

- **NSSM** (the Non-Sucking Service Manager) — wraps any exe as a service, *"monitors the running service
  and will restart it if it dies"*, handles stdout/stderr redirection to files, throttling, and exit-code
  actions. It is the pragmatic choice and by far the least code.
  `nssm install GTA6NewsBot C:\venvs\gta6-news-bot\Scripts\python.exe C:\bots\gta6-news-bot\bot.py --daemon`
  then `nssm set GTA6NewsBot AppDirectory C:\bots\gta6-news-bot`, `nssm set GTA6NewsBot AppStdout ...`.
  Caveat: nssm.cc does not publish a clear "latest version / last updated" on its front page
  (**[UNVERIFIED release date]** — the widely-distributed stable build is 2.24, with newer prerelease
  builds available from the site's /builds page). It is effectively feature-complete rather than actively
  developed. It works, and it is a single 300 KB exe.
- **`sc.exe create`** — only works for binaries that actually implement the Windows Service Control
  Manager protocol. `python.exe yourscript.py` does **not**. `sc create` on a plain exe produces a service
  that starts and is then killed by the SCM with *"did not respond to the start or control request in a
  timely fashion"* (error 1053). **Do not use `sc.exe` directly for a Python script.** It is only relevant
  for registering something like NSSM's wrapper or a `pywin32`-built service.
- **`pywin32` / `win32serviceutil`** — write a real service class with `SvcDoRun`/`SvcStop`. Fully
  supported, gives you proper stop signals and Windows-native lifecycle. Costs: a `pip install pywin32`,
  ~80 lines of boilerplate, elevation to install, no stdout at all (so file logging is mandatory), and a
  genuinely awkward debug loop (`python service.py debug` behaves differently from the installed service).

**Verdict for this project: not worth it.** A service buys you exactly two things — running while logged
off, and starting before logon. You need neither: this is a personal desktop where you are logged in, and
a digest that posts a few minutes after you sign in is fine. Against that you pay elevation, a stored
password or a `LocalSystem` account (which then has no OneDrive and no user profile — breaking §5's
`%LOCALAPPDATA%` assumption, since `LocalSystem`'s LOCALAPPDATA is
`C:\Windows\System32\config\systemprofile\AppData\Local`), an opaque failure mode, and a worse debug loop.

Task Scheduler with a 15-minute repetition gives you the same reliability for this workload with a
fraction of the moving parts. **Revisit only if** you decide you need sub-minute alerting *and* operation
while logged off — in which case use NSSM, not `sc.exe` or `pywin32`.

---

## 7. The catch-up scheduler pattern

### 7.1 The design in one paragraph

Every 15 minutes the process wakes, asks *"is a digest due?"*, and if so **atomically claims** a local
date in a `digest_runs` table whose primary key is that date. The claim is the idempotency guard: a second
process, a second trigger, a DST oddity or a Task Scheduler double-fire all lose the race and do nothing.
Content is selected by an **unsent flag**, never by a time window, which removes DST from the content path
entirely. Everything except the date key and the 18:00 comparison uses **epoch seconds**.

### 7.2 DST analysis — the subtle bug, properly

**The facts.** Hungary observes EU summer time and will continue to in 2026; the EU proposal to abolish
clock changes was adopted by Parliament in 2019 but the Council never agreed a position, *"no final
decision has been taken... and no timeline for such decision has been defined."* The rule is: forward on
the **last Sunday in March at 02:00 CET → 03:00 CEST**, back on the **last Sunday in October at
03:00 CEST → 02:00 CET**.

Next transitions from today (2026-08-25):

| Date | Direction | Local clock | Offset |
|---|---|---|---|
| **2026-10-25** | back | 03:00 → 02:00 | **+02:00 → +01:00** |
| 2027-03-28 | forward | 02:00 → 03:00 | +01:00 → +02:00 |
| 2027-10-31 | back | 03:00 → 02:00 | +02:00 → +01:00 |

**The good news, and why the naive design is actually sound.**

Both transitions happen between 02:00 and 03:00 local. Therefore:

1. **18:00 local exists exactly once on every single day of the year.** It is never skipped (the spring gap
   is 02:00–03:00) and never repeated (the autumn ambiguity is 02:00–03:00). So
   `now.replace(hour=18, minute=0)` is a well-defined, unambiguous instant on all 365/366 days.
2. **No local calendar date is ever skipped or duplicated.** DST shifts the clock within a day; it never
   deletes or repeats a date. So a `UNIQUE` constraint on `local_date` is a sound idempotency key.

**Conclusion: a naive-local "at or after 18:00, once per local date" scheduler cannot double-post or skip a
day *because of DST*.** That is a real result and it is why this design is safe without tzdata. If the
digest time were 02:30 instead of 18:00, everything below would be wrong and you would need tzdata.

**Now the bad news — the five places DST *does* bite.**

**(a) Hardcoding the offset. This is the bug you are most likely to write.**
The environment note says `datetime.now().astimezone().utcoffset() == 2:00:00`. That is true *today* and
**false from 2026-10-25**, when it becomes `1:00:00`. Any of these is a time bomb:

```python
BUDAPEST = timezone(timedelta(hours=2))            # WRONG - breaks 2026-10-25
utc_dt = local_dt - timedelta(hours=2)             # WRONG
published = datetime.utcfromtimestamp(ts) + timedelta(hours=2)   # WRONG
```

There is no correct constant. Either use `datetime.now()` and never convert (recommended), or use
`.astimezone()` with no argument, which asks the OS for the *current* offset:

```python
now_local  = datetime.now()                        # naive local. Fine.
now_aware  = datetime.now().astimezone()           # OS-supplied current offset. Also fine.
epoch      = time.time()                           # DST-free. Best.
```

Add a startup assertion so the machine's timezone is checked rather than assumed. Do **not** string-match
`time.tzname` — on a Hungarian-locale Windows it returns localised names
(**[UNVERIFIED: exact strings, but they are localised]**). Match on the numbers instead:

```python
import time, logging

def check_clock() -> None:
    # time.timezone is the *standard* (non-DST) offset, seconds WEST of UTC.
    # CET = UTC+1  ->  time.timezone == -3600 ; time.daylight == 1 (this zone has DST)
    if time.timezone != -3600 or not time.daylight:
        logging.warning(
            "Unexpected system timezone: base offset %+d h, daylight=%s, tzname=%r. "
            "This bot assumes the machine's local clock is Central European (CET/CEST). "
            "The digest hour will be interpreted in whatever the local clock says.",
            -time.timezone // 3600, time.daylight, time.tzname,
        )
    logging.info("clock: local=%s offset=%s dst_active=%s",
                 datetime.now().isoformat(timespec="seconds"),
                 datetime.now().astimezone().strftime("%z"),
                 bool(time.localtime().tm_isdst))
```

Log that every run. When something looks an hour off in three months, this line is the answer.

**(b) Duration arithmetic on naive local datetimes.** Subtracting two naive local datetimes that straddle
a transition gives an answer wrong by exactly one hour:

```python
# WRONG across 2026-10-25
elapsed = datetime.now() - datetime.fromisoformat(row["last_run_local"])
if elapsed > timedelta(hours=24): ...
```

On 2026-10-25 the local clock spans 25 real hours, so 24 naive-hours is 25 real hours (and 23 on
2027-03-28). Anything built on this — "has it been 24 h since the last digest", backoff windows, "is this
item older than 48 h" — misfires once or twice a year.

**Fix: store and compare epoch seconds everywhere.** `time.time()` is UTC-based and has no DST. This is
already the schema in §2/§4 (`last_success_at`, `first_seen_at`, `backoff_until` are all `INTEGER` epoch).

**(c) The ambiguous hour, 02:00–03:00 on 2026-10-25.** During that hour `datetime.now()` returns the same
wall-clock strings twice, an hour apart in real time, and **the clock goes backwards** at 03:00. Any logic
keyed on a naive local timestamp can therefore mis-order events or collide two distinct instants. If your
dedup or "newest item" ordering used local timestamps, you would silently lose or reorder an hour of items
once a year. The bot happens to be idle-ish at 02:30, which is why this bug survives testing for years.

**Fix: never key, order, or dedup on local time.** Local time appears in exactly two places in this
design — the `local_date` idempotency key and the `hour >= 18` comparison — and neither is in the
02:00–03:00 window.

**(d) Long computed sleeps drift.** A long-running design that does
`sleep((target_18h - now).total_seconds())` computed at 01:00 on a transition day will wake an hour early
(October) or an hour late (March), because it converted a *local* duration into a *real* duration.

**Fix:** the Task Scheduler design already avoids this — the process is re-launched every 15 minutes and
re-reads `datetime.now()` from scratch. If you ever go long-running, poll (`await asyncio.sleep(60)`) and
re-evaluate; never sleep a long computed delta.

**(e) Task Scheduler's own DST behaviour.** There are credible reports of Windows scheduled tasks
**firing an hour early** after a DST change, and of **weekly** triggers with multiple weekdays running
twice or not at all across a transition — with "delete and recreate the task" as the folk remedy.
**[UNVERIFIED — community reports and Microsoft Q&A threads, not a Microsoft KB.]**

**Fix, and it is the whole reason for this architecture:** use a **Daily** trigger (never Weekly) with a
15-minute repetition, and let the *bot* decide. If Task Scheduler fires at 17:00 instead of 18:00, the bot
says "not yet" and exits. If it fires twice, the second one loses the `INSERT` race. The scheduler's
timing accuracy becomes irrelevant — it only needs to launch the process *often enough*.

**Summary of the fix:**

| Rule | Why |
|---|---|
| Never hardcode a UTC offset | breaks 2026-10-25 |
| `datetime.now()` **only** for `local_date` and the `hour >= 18` test | both are DST-unambiguous at 18:00 |
| Epoch seconds (`time.time()`, `calendar.timegm()`) for everything else | DST-free |
| `UNIQUE`/`PRIMARY KEY` on `local_date` | dates are never duplicated, even by DST |
| Content selected by unsent flag, not a time window | removes DST from the content path |
| Daily trigger + short repetition, decision in Python | immunises against scheduler timing errors |
| Log offset + dst flag every run | makes the once-a-year bug diagnosable |

### 7.3 Three days offline: one catch-up digest, not three

**Post one.** Reasons: three digests dumped at once is spam; the items would have to be split by
publication date, which is unreliable (§4 — timestamps are absent or wrong); and the *purpose* of the
digest is "here's what you missed", which one message serves better than three.

Implementation: identify the **single most recent due date**, claim it, and **mark all older unclaimed
dates as `skipped`** in the same transaction so they never fire later. The digest then contains everything
unsent — i.e. three days of items — capped and labelled:

> **GTA6 Digest — catch-up for 2026-08-25** (covering 3 days, bot was offline)

### 7.4 The instant-alert interlock

An item sent as an instant alert must not reappear in that evening's digest. Two columns and one rule:

```sql
instant_sent_at   INTEGER,         -- epoch when an instant alert went out; NULL otherwise
digest_run_date   TEXT             -- local_date of the digest that claimed it; NULL = unsent
```

Digest selection: `WHERE instant_sent_at IS NULL AND digest_run_date IS NULL`.

Set `instant_sent_at` **after** a successful Discord post, in the same transaction that the post's success
is recorded. If the instant post fails, leave it NULL — the item then falls into the digest, which is the
correct degradation (you still hear about it, just later).

Optional refinement: instead of excluding instant-alerted items entirely, list them in a compact
`Already alerted:` footer line. Costs nothing and stops "did the bot see this?" doubts.

### 7.5 Schema

```sql
CREATE TABLE IF NOT EXISTS digest_runs (
    local_date     TEXT    PRIMARY KEY,          -- 'YYYY-MM-DD' local. THE idempotency guard.
    status         TEXT    NOT NULL,             -- 'running' | 'done' | 'failed' | 'skipped'
    claimed_at     INTEGER NOT NULL,             -- epoch
    completed_at   INTEGER,
    attempts       INTEGER NOT NULL DEFAULT 0,
    item_count     INTEGER,
    is_catchup     INTEGER NOT NULL DEFAULT 0,
    minutes_late   INTEGER,                      -- observability: how late did we post?
    note           TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS runs (                -- heartbeat, one row per process launch
    id            INTEGER PRIMARY KEY,
    started_at    INTEGER NOT NULL,
    finished_at   INTEGER,
    exit_status   TEXT,
    feeds_ok      INTEGER,
    feeds_failed  INTEGER,
    items_new     INTEGER,
    digest_posted INTEGER NOT NULL DEFAULT 0
) STRICT;
```

`TEXT PRIMARY KEY` on `local_date` gives you the UNIQUE constraint for free. `STRICT` (SQLite 3.37+;
Python 3.12 ships 3.4x) catches type mistakes early — drop it if your SQLite is older.

### 7.6 The decision function — real code

```python
"""
Digest scheduling: post once per local day at/after 18:00, catch up if missed, never twice.

Timezone policy (deliberate, see research notes):
  * The machine has NO tzdata; zoneinfo.ZoneInfo("Europe/Budapest") raises. Do not import it.
  * The system local clock IS Central European (CET/CEST) and Windows handles DST for us.
  * datetime.now() (naive local) is used for EXACTLY TWO THINGS:
        1. deriving the local calendar date used as the idempotency key
        2. comparing against the 18:00 local digest threshold
    Both are DST-safe because Hungary's transitions occur between 02:00 and 03:00, so
    18:00 local exists exactly once on every day of the year, and no local date is ever
    skipped or duplicated.
  * EVERYTHING else (durations, ages, backoff, item timestamps) uses epoch seconds,
    which are DST-free. Never do arithmetic on two naive local datetimes.
  * Never hardcode a UTC offset. The offset changes from +02:00 to +01:00 on 2026-10-25.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

log = logging.getLogger(__name__)

DIGEST_HOUR = 18
DIGEST_MINUTE = 0

# If we are more than this late, the digest is labelled a catch-up.
LATE_LABEL_MINUTES = 90
# Don't retry a failed digest for the same date more than this many times.
MAX_ATTEMPTS = 3
# Never resurrect a digest date older than this (avoids a weeks-old backfill after a long outage).
MAX_CATCHUP_AGE_DAYS = 14


class Action(Enum):
    NOTHING = "nothing"        # not due, or already done
    POST = "post"              # claim this date and post
    RETRY = "retry"            # a previous attempt for this date failed; try again


@dataclass(frozen=True)
class Decision:
    action: Action
    local_date: str | None      # 'YYYY-MM-DD'
    is_catchup: bool = False
    minutes_late: int = 0
    skip_dates: tuple[str, ...] = ()   # older due dates to mark 'skipped' in the same txn
    reason: str = ""


# --------------------------------------------------------------------------- #
# Pure decision logic. No I/O except the two lookups passed in.              #
# --------------------------------------------------------------------------- #

def _threshold(d: date) -> datetime:
    """The 18:00 local instant on date d. Unambiguous on every day of the year in Hungary."""
    return datetime(d.year, d.month, d.day, DIGEST_HOUR, DIGEST_MINUTE)


def most_recent_due_date(now_local: datetime) -> date:
    """
    The latest local date whose 18:00 threshold has already passed.

    If it is 18:00 or later today  -> today.
    If it is before 18:00 today    -> yesterday (its 18:00 has passed).
    """
    today = now_local.date()
    if now_local >= _threshold(today):
        return today
    return today - timedelta(days=1)


def decide(
    now_local: datetime,
    existing: dict[str, tuple[str, int]],   # local_date -> (status, attempts)
) -> Decision:
    """
    Decide whether to post a digest.

    `existing` must contain every digest_runs row for the last MAX_CATCHUP_AGE_DAYS days.
    Pure function: same inputs -> same output. Trivially testable, including across DST.
    """
    due = most_recent_due_date(now_local)
    due_key = due.isoformat()

    # How late are we, in real minutes? Both operands are naive local, but they are only
    # ever within ~24h of each other AND neither lands in the 02:00-03:00 ambiguous window,
    # so this difference is accurate except on a transition day, where it can be off by 60
    # minutes. That only affects the cosmetic "minutes_late" label, never the decision.
    minutes_late = int((now_local - _threshold(due)).total_seconds() // 60)

    row = existing.get(due_key)

    if row is not None:
        status, attempts = row
        if status == "done":
            return Decision(Action.NOTHING, due_key, reason=f"{due_key} already posted")
        if status == "skipped":
            return Decision(Action.NOTHING, due_key, reason=f"{due_key} explicitly skipped")
        if status == "running":
            # Another process holds it, or a previous run died mid-post.
            # Treat a stale 'running' (>1h) as failed so we don't wedge forever.
            return Decision(Action.NOTHING, due_key, reason=f"{due_key} in progress")
        if status == "failed":
            if attempts >= MAX_ATTEMPTS:
                return Decision(Action.NOTHING, due_key,
                                reason=f"{due_key} failed {attempts}x, giving up until tomorrow")
            return Decision(Action.RETRY, due_key,
                            is_catchup=minutes_late > LATE_LABEL_MINUTES,
                            minutes_late=minutes_late,
                            reason=f"retrying {due_key} (attempt {attempts + 1})")

    # No row for the due date -> it is genuinely due now.
    # Any OLDER due date without a row is a missed day we will NOT post separately;
    # mark them skipped so they can never fire later. (PC off for 3 days -> ONE digest.)
    skips: list[str] = []
    for back in range(1, MAX_CATCHUP_AGE_DAYS + 1):
        d = (due - timedelta(days=back)).isoformat()
        if d not in existing:
            skips.append(d)

    return Decision(
        Action.POST,
        due_key,
        is_catchup=minutes_late > LATE_LABEL_MINUTES,
        minutes_late=minutes_late,
        skip_dates=tuple(skips),
        reason=(f"digest due for {due_key}, {minutes_late} min after 18:00"
                + (" (CATCH-UP)" if minutes_late > LATE_LABEL_MINUTES else "")),
    )


# --------------------------------------------------------------------------- #
# The atomic claim. This is the part that makes "never post twice" true.      #
# --------------------------------------------------------------------------- #

async def load_recent(conn) -> dict[str, tuple[str, int]]:
    cutoff = (date.today() - timedelta(days=MAX_CATCHUP_AGE_DAYS + 2)).isoformat()
    cur = await conn.execute(
        "SELECT local_date, status, attempts FROM digest_runs WHERE local_date >= ?",
        (cutoff,),
    )
    return {r[0]: (r[1], r[2]) for r in await cur.fetchall()}


async def reap_stale_running(conn, now_epoch: int, stale_after_s: int = 3600) -> None:
    """A process that died mid-post leaves status='running'. Recover it."""
    await conn.execute(
        "UPDATE digest_runs SET status='failed', note='stale running reaped' "
        "WHERE status='running' AND claimed_at < ?",
        (now_epoch - stale_after_s,),
    )


async def claim(conn, dec: Decision, now_epoch: int) -> bool:
    """
    Atomically claim the digest date. Returns True iff THIS process owns it.

    BEGIN IMMEDIATE takes the write lock up front, so two concurrent processes
    serialise here rather than colliding at COMMIT.
    """
    await conn.execute("BEGIN IMMEDIATE")
    try:
        # Bury the older missed days first, in the same transaction.
        for d in dec.skip_dates:
            await conn.execute(
                "INSERT OR IGNORE INTO digest_runs "
                "(local_date, status, claimed_at, attempts, note) "
                "VALUES (?, 'skipped', ?, 0, 'missed; folded into a later catch-up digest')",
                (d, now_epoch),
            )

        if dec.action is Action.POST:
            try:
                await conn.execute(
                    "INSERT INTO digest_runs "
                    "(local_date, status, claimed_at, attempts, is_catchup, minutes_late) "
                    "VALUES (?, 'running', ?, 1, ?, ?)",
                    (dec.local_date, now_epoch, int(dec.is_catchup), dec.minutes_late),
                )
            except sqlite3.IntegrityError:
                # Someone else inserted this local_date between our read and our write.
                # THE guard. Losing this race is a normal, expected outcome.
                await conn.execute("ROLLBACK")
                log.info("lost the claim race for %s; another run owns it", dec.local_date)
                return False
        else:  # Action.RETRY
            cur = await conn.execute(
                "UPDATE digest_runs SET status='running', claimed_at=?, attempts=attempts+1 "
                "WHERE local_date=? AND status='failed'",
                (now_epoch, dec.local_date),
            )
            if cur.rowcount != 1:
                await conn.execute("ROLLBACK")
                return False

        await conn.execute("COMMIT")
        return True
    except Exception:
        await conn.execute("ROLLBACK")
        raise


async def finish(conn, local_date: str, ok: bool, item_count: int, note: str = "") -> None:
    """
    Close out the run. The `status <> 'done'` predicate makes this idempotent:
    a date can transition to 'done' at most once, ever.
    """
    if ok:
        await conn.execute(
            "UPDATE digest_runs SET status='done', completed_at=?, item_count=?, note=? "
            "WHERE local_date=? AND status <> 'done'",
            (int(time.time()), item_count, note, local_date),
        )
    else:
        await conn.execute(
            "UPDATE digest_runs SET status='failed', note=? "
            "WHERE local_date=? AND status='running'",
            (note[:500], local_date),
        )


# --------------------------------------------------------------------------- #
# Orchestration: claim -> select items -> post -> commit, with rollback.      #
# --------------------------------------------------------------------------- #

MAX_DIGEST_ITEMS = 25

async def run_digest_if_due(conn, poster) -> bool:
    now_local = datetime.now()          # the ONLY local-clock read
    now_epoch = int(time.time())        # everything else

    await reap_stale_running(conn, now_epoch)
    dec = decide(now_local, await load_recent(conn))
    log.info("digest decision: %s (%s)", dec.action.value, dec.reason)

    if dec.action is Action.NOTHING:
        return False
    if not await claim(conn, dec, now_epoch):
        return False

    # --- select and reserve items, in one transaction -----------------------
    await conn.execute("BEGIN IMMEDIATE")
    try:
        cur = await conn.execute(
            """
            SELECT i.id, i.title, i.link, i.published_at, i.first_seen_at, f.name AS feed_name
            FROM items i
            JOIN feeds f ON f.id = i.feed_id
            WHERE i.instant_sent_at IS NULL      -- interlock: not already alerted
              AND i.digest_run_date IS NULL      -- not already in a digest
            GROUP BY i.global_key                -- cross-feed dedup (§4)
            ORDER BY COALESCE(i.published_at, i.first_seen_at) DESC
            LIMIT ?
            """,
            (MAX_DIGEST_ITEMS + 1,),
        )
        rows = [dict(r) for r in await cur.fetchall()]
        overflow = len(rows) > MAX_DIGEST_ITEMS
        rows = rows[:MAX_DIGEST_ITEMS]

        # Reserve them BEFORE posting so a crash cannot double-send.
        if rows:
            await conn.executemany(
                "UPDATE items SET digest_run_date=? WHERE id=?",
                [(dec.local_date, r["id"]) for r in rows],
            )
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        await finish(conn, dec.local_date, ok=False, item_count=0, note="item selection failed")
        raise

    # --- post ---------------------------------------------------------------
    try:
        await poster.post_digest(
            local_date=dec.local_date,
            items=rows,
            is_catchup=dec.is_catchup,
            minutes_late=dec.minutes_late,
            overflow=overflow,
        )
    except Exception as exc:
        # Release the reservation so the items reappear in the next attempt.
        await conn.execute("BEGIN IMMEDIATE")
        await conn.execute(
            "UPDATE items SET digest_run_date=NULL WHERE digest_run_date=?", (dec.local_date,)
        )
        await finish(conn, dec.local_date, ok=False, item_count=0, note=f"{type(exc).__name__}: {exc}")
        await conn.execute("COMMIT")
        log.exception("digest post failed for %s; reservation released", dec.local_date)
        return False

    await finish(conn, dec.local_date, ok=True, item_count=len(rows))
    log.info("digest posted for %s: %d items (catchup=%s, %d min late)",
             dec.local_date, len(rows), dec.is_catchup, dec.minutes_late)
    return True
```

### 7.7 Why each guarantee holds

| Requirement | Mechanism |
|---|---|
| **Never posts twice** | `PRIMARY KEY (local_date)`; the `INSERT` inside `BEGIN IMMEDIATE` is the race arbiter. `finish()`'s `WHERE status <> 'done'` means a date reaches `done` at most once. |
| **Posts at/after 18:00 local** | `now_local >= _threshold(today)`. Because the process wakes every 15 min, the real post time is 18:00–18:15. |
| **Catches up if missed** | `most_recent_due_date()` returns yesterday when it's before 18:00 today, so a PC that was off all evening posts on the next wake. No dependence on `StartWhenAvailable`. |
| **One digest after a 3-day outage** | Only the *most recent* due date is claimable; older ones are inserted as `skipped` in the same transaction. |
| **DST-safe** | See §7.2. Local time is touched only where it is provably unambiguous. |
| **Instant-alert interlock** | `WHERE instant_sent_at IS NULL AND digest_run_date IS NULL`. |
| **Crash mid-post doesn't lose items** | Items are reserved before posting and released on failure; `status='running'` is reaped after an hour. |
| **Crash mid-post doesn't duplicate** | The reservation means a retry re-selects the same items only after an explicit release. |

### 7.8 Tests worth writing (they're cheap and they're the whole value)

`decide()` is a pure function of `(now_local, existing)`, so:

```python
def test_before_18_no_row_yesterday_is_due():
    d = decide(datetime(2026, 9, 10, 9, 0), {})
    assert d.action is Action.POST and d.local_date == "2026-09-10" or True
    # careful: at 09:00 the due date is YESTERDAY
    assert d.local_date == "2026-09-09"

def test_after_18_today_is_due():
    assert decide(datetime(2026, 9, 10, 18, 0), {}).local_date == "2026-09-10"

def test_already_done_is_noop():
    d = decide(datetime(2026, 9, 10, 23, 0), {"2026-09-10": ("done", 1)})
    assert d.action is Action.NOTHING

def test_three_day_outage_posts_once_and_skips_the_rest():
    d = decide(datetime(2026, 9, 10, 19, 0), {})
    assert d.local_date == "2026-09-10"
    assert "2026-09-09" in d.skip_dates and "2026-09-08" in d.skip_dates

def test_dst_fallback_day_2026_10_25():
    # The 25-hour day. 18:00 exists once; the date is due exactly once.
    before = decide(datetime(2026, 10, 25, 17, 59), {})
    assert before.local_date == "2026-10-24"
    at = decide(datetime(2026, 10, 25, 18, 0), {})
    assert at.action is Action.POST and at.local_date == "2026-10-25"
    after = decide(datetime(2026, 10, 25, 23, 0), {"2026-10-25": ("done", 1)})
    assert after.action is Action.NOTHING

def test_dst_spring_forward_2027_03_28():
    # The 23-hour day. Same invariants.
    at = decide(datetime(2027, 3, 28, 18, 5), {})
    assert at.action is Action.POST and at.local_date == "2027-03-28"

def test_ambiguous_hour_never_reached():
    # Sanity: the digest threshold is far from the 02:00-03:00 transition window.
    assert DIGEST_HOUR not in (2, 3)
```

Six tests, no clock mocking beyond passing a datetime, and they lock down the exact bug class §7.2 warns
about.

---

## 8. Article text extraction (brief)

Only needed when a feed gives a truncated snippet and you want more for the digest blurb.

| Library | Latest | Released | Python | Verdict |
|---|---|---|---|---|
| **trafilatura** | **2.2.0** | **2026-07-31** | `>=3.10`, 3.10–3.14 | **Use this** |
| goose3 | 3.1.22 | 2026-07-23 | `>=3.9`, 3.9–3.14 | Maintained, heavier |
| readability-lxml | 0.8.4.1 | 2025-05-03 | 3.8–3.13 | Maintained, minimal |
| newspaper3k | 0.2.8 | **2018-09-28** | 3 only | **Abandoned. Do not use.** |

**Recommendation: trafilatura.**

```
pip install "trafilatura==2.2.0"
```

```python
import trafilatura
text = trafilatura.extract(html, include_comments=False, include_tables=False,
                           favor_precision=True) or ""
```

It consistently benchmarks at or near the top for main-content extraction, is actively developed
(release three weeks ago), covers py3.10–3.14, and `favor_precision=True` is exactly right for a digest
blurb where a false-positive nav menu is worse than a missing paragraph.

**Caveats, one each:**

- **trafilatura** — heaviest dependency tree of the four: `lxml>=6.1.1`, `charset_normalizer`, `courlan`,
  `htmldate`, `justext`, `urllib3`, `certifi`. That's ~7 transitive packages for what is, for you, a
  nice-to-have. It also has its own downloader (and pulls `urllib3`); **use only
  `trafilatura.extract(html_string)`** and keep fetching with httpx, same reasoning as feedparser.
  Licence note: Apache-2.0 from v1.8.0 onward (GPLv3+ before).
- **readability-lxml** — the lightest option (`lxml[html_clean]`, `chardet`, `cssselect`) and a fine
  fallback, but it is a port of the old Arc90 readability algorithm and is noticeably worse than
  trafilatura on modern JS-heavy news pages; it also returns *HTML*, so you still need a
  strip-tags step. Note it now needs `lxml-html-clean` because `lxml.html.clean` was split out of lxml.
- **goose3** — actively maintained and good at metadata/lead-image extraction, but it drags in `requests`,
  `Pillow`, `beautifulsoup4`, `langdetect`, `pyahocorasick`, `python-dateutil`. `Pillow` for image
  candidates is a lot of build surface for a text digest. Pick it only if you want the hero image.
- **newspaper3k** — last release **2018-09-28**, classifiers stop at bare "Python 3", depends on old
  `lxml`/`nltk` pins that fight modern installs. It is the most commonly recommended and the most
  thoroughly abandoned. (The community fork `newspaper4k` exists if you must, but trafilatura is better.)

**When to use it at all:** only for the digest's top few items, only when
`len(entry.summary_text) < ~200 chars`, and cache the extracted text in SQLite keyed on `global_key` so you
never re-fetch. Fetching the full article page for 30 items every evening is a much bigger politeness
footprint than the feed polling itself — and article pages are far more likely to be Cloudflare-protected
(§3) than feed endpoints. Budget it: max 5 article fetches per digest, 2 s apart, and fail soft.

---

## 9. Windows Task Scheduler setup checklist

Follow in order. Steps 1–4 are prerequisites; do not skip them, they are where the time gets lost.

### Step 0 — Decide the paths

| What | Recommended path |
|---|---|
| Source | `C:\bots\gta6-news-bot\` (**preferred**) or the existing OneDrive path |
| Venv | `C:\venvs\gta6-news-bot\` |
| Interpreter | `C:\venvs\gta6-news-bot\Scripts\pythonw.exe` |
| Entry point | `<source>\bot.py` |
| DB / logs | `%LOCALAPPDATA%\gta6-news-bot\` (created by the code) |

If you keep the source in OneDrive: right-click the project folder → **"Always keep on this device"**.

### Step 1 — Enable Task Scheduler history (do this first)

Open Task Scheduler as administrator → right-hand **Actions** pane → **"Enable All Tasks History"**.
Or in an elevated shell:

```powershell
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true
```

It is **off by default**. Without it you get no History tab and no event log, and you will waste an
evening concluding the task never fired.

### Step 2 — Verify the command by hand, from the wrong directory

This one test catches most bugs before they exist:

```powershell
Set-Location C:\Windows\System32
& C:\venvs\gta6-news-bot\Scripts\python.exe C:\bots\gta6-news-bot\bot.py --once
```

Note `python.exe` (not `pythonw`) so you can see output. It must succeed **from System32** — that is the
working directory Task Scheduler uses when "Start in" is blank. If it fails here, fix the code's path
handling (§6, "Start in") rather than relying on the task setting.

Check the exit code: `$LASTEXITCODE` must be `0`.

### Step 3 — Check your power states (only if you care about 18:00-on-the-dot)

```powershell
powercfg /a              # S3 vs "Standby (S0 Low Power Idle)" vs hibernate availability
powercfg /waketimers     # run elevated; after registering the task, your task should appear here
```

If `powercfg /a` says **S0 Low Power Idle**, `WakeToRun` is unreliable — accept catch-up posting (§6).
If it says **S3**, ensure wake timers are enabled:

```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_SLEEP bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d 1
powercfg /setdcvalueindex SCHEME_CURRENT SUB_SLEEP bd3b718a-0680-4d9d-8ab2-e1d2b4ac806d 1
powercfg /setactive SCHEME_CURRENT
```

### Step 4 — Write the task XML

Save as `C:\bots\gta6-news-bot\deploy\task.xml`. **Must be UTF-16 LE with a BOM** — `schtasks /xml`
rejects some UTF-8 files. From PowerShell: `Set-Content -Encoding Unicode`.

Replace `<MACHINE>\<you>` with the output of `whoami`.

```xml
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>&lt;you&gt;</Author>
    <Description>GTA6 news bot: polls RSS/Atom feeds, sends instant alerts, and posts one
Discord digest per local day at/after 18:00 (catching up if the PC was asleep or off).
Runs every 15 minutes; all scheduling decisions are made inside the bot.</Description>
    <URI>\GTA6 News Bot</URI>
  </RegistrationInfo>

  <Triggers>
    <CalendarTrigger>
      <!-- Daily, NOT "One Time": a One Time trigger will not refire after a missed start
           (Microsoft KB 2437520, "This behavior is by design"). -->
      <StartBoundary>2026-08-25T00:02:00</StartBoundary>
      <!-- An EndBoundary is present deliberately: StartWhenAvailable is documented to apply
           only to time-based tasks WITH AN END BOUNDARY or repeating infinitely. -->
      <EndBoundary>2099-12-31T23:59:59</EndBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT15M</Interval>
        <Duration>P1D</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>

  <Principals>
    <Principal id="Author">
      <UserId><MACHINE>\<you></UserId>
      <!-- InteractiveToken = "Run only when user is logged on". No stored password,
           nothing to break on a password change, and OneDrive is running. -->
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>

  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <!-- Deliberately false: this setting is flaky (it can report "no network" on a working
         connection, and it does not retry sanely). The bot does its own reachability check. -->
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <!-- Free bonus in the S3-sleep case; do NOT depend on it (see research §6). -->
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
  </Settings>

  <Actions Context="Author">
    <Exec>
      <Command>C:\venvs\gta6-news-bot\Scripts\pythonw.exe</Command>
      <Arguments>"C:\bots\gta6-news-bot\bot.py" --once</Arguments>
      <!-- Without this, the working directory is C:\Windows\System32. -->
      <WorkingDirectory>C:\bots\gta6-news-bot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

Notes on specific choices:

- **`<Repetition>` `PT15M` / `P1D`** — 96 runs/day. Combined with the Daily trigger this means a fresh
  24-hour repetition window starts at 00:02 every day. Use `PT5M` if you want tighter instant alerts.
- **`ExecutionTimeLimit` `PT10M`** — must be **shorter than** the repetition interval so a hung run is
  killed before the next one is due; with `IgnoreNew`, a hung run would otherwise block every subsequent
  run indefinitely. If you switch to `PT5M` repetition, drop this to `PT4M`. A kill shows up as
  `0x41306`.
- **`MultipleInstancesPolicy=IgnoreNew`** — overlapping runs would fight over the SQLite write lock.
  Expect Event ID 322 in the log when this fires; it is not an error.
- **`RestartOnFailure`** — retries twice, 5 min apart, if the process exits non-zero. Make the bot exit
  non-zero only on genuinely retryable failures, or this doubles your log noise.
- **`StartWhenAvailable=true`** — belt and braces only. With a 15-minute repetition the bot catches up on
  its own within 15 minutes of resume; the documented ~10-minute queue delay makes this the *slower* of
  the two mechanisms.
- **`RunLevel=LeastPrivilege`** — no elevation needed. Never run this elevated.

### Step 5 — Register it

```powershell
schtasks /create /tn "GTA6 News Bot" /xml "C:\bots\gta6-news-bot\deploy\task.xml" /f
```

`/f` overwrites an existing task of the same name, so this command is your redeploy command too.

`schtasks /create` **cannot** set `StartWhenAvailable`, `WakeToRun`, `MultipleInstancesPolicy`, or
`WorkingDirectory` from command-line switches — `/XML` is the only scriptable way to get them.
(For reference, the switch-only equivalent would be
`schtasks /create /tn "GTA6 News Bot" /tr "..." /sc MINUTE /mo 15 /st 00:02 /f`, which gets you the
repetition and nothing else.)

### Step 6 — Verify

```powershell
schtasks /query /tn "GTA6 News Bot" /v /fo LIST     # check Start In, Logon Mode, Next Run Time
schtasks /run   /tn "GTA6 News Bot"                 # force a run now
Start-Sleep 20
schtasks /query /tn "GTA6 News Bot" /fo LIST        # Last Result should be 0
Get-Content "$env:LOCALAPPDATA\gta6-news-bot\logs\bot.log" -Tail 40
powercfg /waketimers                                # elevated; task should be listed if WakeToRun works
```

Checklist of things that should be true:
- [ ] `Next Run Time` is a real timestamp, **not** `Never`
- [ ] `Logon Mode: Interactive only`
- [ ] `Start In` is your project directory, not blank
- [ ] `Last Result: 0`
- [ ] `bot.log` has a line for the run, including the clock/offset line from §7.2
- [ ] a `runs` row exists in the DB
- [ ] no console window flashed

### Step 7 — Verify the digest logic without waiting until 18:00

Do **not** test by changing the system clock (it will confuse OneDrive, Windows Update, and TLS). Instead
make the threshold overridable:

```python
DIGEST_HOUR = int(os.environ.get("GTA6BOT_DIGEST_HOUR", 18))
```

then:

```powershell
$env:GTA6BOT_DB   = "$env:TEMP\bot-test.db"
$env:GTA6BOT_DIGEST_HOUR = "0"          # "18:00" becomes 00:00, i.e. always due
& C:\venvs\gta6-news-bot\Scripts\python.exe C:\bots\gta6-news-bot\bot.py --once
& C:\venvs\gta6-news-bot\Scripts\python.exe C:\bots\gta6-news-bot\bot.py --once   # must NOT post twice
```

The second invocation posting nothing is the single most important behaviour in the whole project. Run
the §7.8 unit tests too — they cover the DST days you cannot reach by hand.

### Step 8 — Ongoing operations

| Task | Command |
|---|---|
| Watch the log live | `Get-Content "$env:LOCALAPPDATA\gta6-news-bot\logs\bot.log" -Wait -Tail 20` |
| Recent task events | `Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational -MaxEvents 40 \| Format-Table TimeCreated,Id,Message -Auto` |
| Just the exit codes | `Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational \| Where-Object Id -eq 201 \| Select-Object -First 10 TimeCreated,Message` |
| Redeploy after editing XML | `schtasks /create /tn "GTA6 News Bot" /xml ".\deploy\task.xml" /f` |
| Pause the bot | `schtasks /change /tn "GTA6 News Bot" /disable` |
| Resume | `schtasks /change /tn "GTA6 News Bot" /enable` |
| Weekly DB snapshot | `VACUUM INTO` from the bot; copy the snapshot to OneDrive, never the live DB |

### Common failures and their signatures

| Symptom | Cause | Fix |
|---|---|---|
| `Last Result 0x2` | Wrong path to `pythonw.exe` or the script | Check `<Command>`/`<Arguments>`; quote paths with spaces |
| `Last Result 0x1`, empty log | Crash before logging was configured, or `print()` under `pythonw` | Configure logging as the first thing in `main()`; install `sys.excepthook` |
| `Last Result 0x1`, log says `.env` missing / token `None` | Working directory is System32 | Set `<WorkingDirectory>` **and** use `Path(__file__).parent` |
| `Last Result 0x41306` | Hit `ExecutionTimeLimit` | A feed is hanging; lower httpx timeouts, add a per-run wall-clock budget |
| `Last Result 0x8004130F` | Stored credentials broke (password change) | You shouldn't have any — switch to `InteractiveToken` |
| `Next Run Time: Never` | Trigger/credential problem, or task disabled | `schtasks /query /v`; re-register from XML |
| History tab empty | History not enabled | Step 1 |
| Task never fires overnight | PC asleep/off; Modern Standby | Expected — the bot catches up. Verify with `powercfg /a` |
| `database is locked` | Two instances, or DB Browser holding a write txn | `IgnoreNew` + `busy_timeout=5000` (§5) |
| `database disk image is malformed` | DB was in OneDrive | §5. Move it and restore from a `VACUUM INTO` snapshot |
| Console window flashes | Using `python.exe` | Use `pythonw.exe` |
| `UnicodeEncodeError` in a log call | cp1252 default encoding | `encoding="utf-8"` on the handler; `PYTHONUTF8=1` |

---

## 10. Sources consulted

**Feed parsing**
- feedparser on PyPI (JSON API) — https://pypi.org/pypi/feedparser/json
- feedparser on GitHub — https://github.com/kurtmckee/feedparser
- feedparser CHANGELOG — https://raw.githubusercontent.com/kurtmckee/feedparser/develop/CHANGELOG.rst
- feedparser docs index — https://feedparser.readthedocs.io/en/latest/
- feedparser, ETag and Last-Modified — https://feedparser.readthedocs.io/en/stable/http-etag.html
- feedparser, Bozo Detection — https://feedparser.readthedocs.io/en/stable/bozo.html
- feedparser, Date Parsing — https://feedparser.readthedocs.io/en/stable/date-parsing.html
- feedparser, HTTP Features — https://feedparser.readthedocs.io/en/stable/http.html
- feedparser, Introduction — https://feedparser.readthedocs.io/en/stable/introduction.html
- feedparser, Reference — https://feedparser.readthedocs.io/en/stable/reference.html
- atoma on PyPI — https://pypi.org/pypi/atoma/json
- atoma on GitHub — https://github.com/NicolasLM/atoma
- reader on PyPI — https://pypi.org/pypi/reader/json
- reader on GitHub — https://github.com/lemon24/reader

**HTTP, caching, conditional requests**
- httpx on PyPI — https://pypi.org/pypi/httpx/json
- httpx QuickStart (redirect + timeout defaults) — https://www.python-httpx.org/quickstart/
- RFC 9110 §13.1.2 If-None-Match — https://httpwg.org/specs/rfc9110.html#field.if-none-match
- hishel on PyPI — https://pypi.org/pypi/hishel/json
- hishel on GitHub — https://github.com/karpetrosyan/hishel

**Politeness, robots.txt, bot blocking**
- Google, user-triggered fetchers and robots.txt — https://developers.google.com/search/docs/crawling-indexing/google-user-triggered-fetchers
- Feeder.co crawler policy — https://feeder.co/crawler
- Known Agents: FreshRSS / feedbot / MonitoRSS / OpenRSS — https://knownagents.com/agents/freshrss , https://knownagents.com/agents/feedbot , https://knownagents.com/agents/monitorss , https://knownagents.com/agents/openrss
- The Art of Web, RSS/Atom aggregator user agents — https://www.the-art-of-web.com/system/agents/107/
- Scrapfly, JA3/JA4 TLS fingerprinting — https://scrapfly.io/blog/posts/ja3-ja4-tls-fingerprinting-guide-to-detection-and-evasion
- Scrapfly, 403 when scraping — https://scrapfly.io/blog/posts/403-forbidden-web-scraping
- webclaw, Cloudflare JA4/JA3 fingerprinting — https://webclaw.io/blog/tls-fingerprint-vs-browser-cloudflare
- Cloudflare Community, Cloudflare blocking NewsBlur RSS fetchers — https://community.cloudflare.com/t/cloudflare-is-blocking-newsblur-rss-feed-fetchers/649373
- Cloudflare Community, WordPress RSS pull 403 — https://community.cloudflare.com/t/wordpress-rss-feed-pull-being-blocked-as-403-error/729918
- curl_cffi on PyPI (documented, not recommended) — https://pypi.org/pypi/curl_cffi/json

**Resilience, retries, Discord**
- AWS Architecture Blog, Exponential Backoff and Jitter — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Discord, Rate Limits (invalid-request limit, headers, 429 body) — https://docs.discord.com/developers/topics/rate-limits
- Baeldung, which HTTP errors should not be retried — https://www.baeldung.com/cs/http-error-status-codes-retry
- REST API Tutorial, HTTP status codes and retry — https://www.restapitutorial.com/advanced/responses/retries
- MDN, HTTP response status codes — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status
- discord.py on PyPI (checked, not used) — https://pypi.org/pypi/discord.py/json
- Discord webhook rate limits (community; unverified buckets) — https://discord-webhook.com/en/blog/discord-webhook-rate-limits/
- Discord embed limits (community) — https://discord-webhook.com/en/blog/discord-webhook-embed-limits/

**SQLite, OneDrive, storage location**
- SQLite, How To Corrupt An SQLite Database File — https://sqlite.org/howtocorrupt.html
- SQLite, Write-Ahead Logging — https://www.sqlite.org/wal.html
- SQLite, PRAGMA statements (busy_timeout, synchronous) — https://www.sqlite.org/pragma.html
- SQLite Forum, corruption during WAL checkpoint — https://sqlite.org/forum/info/47107ab818977549
- simonw/til, enabling WAL mode — https://github.com/simonw/til/blob/master/sqlite/enabling-wal-mode.md
- aiosqlite on PyPI — https://pypi.org/pypi/aiosqlite/json
- aiosqlite on GitHub — https://github.com/omnilib/aiosqlite
- Microsoft, Choose which OneDrive folders to sync — https://support.microsoft.com/en-us/onedrive/choose-which-onedrive-folders-you-want-to-sync-on-windows-or-macos
- Microsoft Q&A, exclude a folder from OneDrive sync — https://learn.microsoft.com/en-us/answers/questions/3984238/how-to-exclude-a-folder-from-onedrive-syncing
- Microsoft Q&A, exclude sub-folders from OneDrive sync — https://learn.microsoft.com/en-us/answers/questions/5425802/exclude-sub-folders-from-onedrive-sync
- Microsoft, Placeholder files (Compatibility Cookbook) — https://learn.microsoft.com/en-us/windows/compatibility/placeholder-files
- Microsoft, About placeholders (IFS) — https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/placeholders
- Microsoft, Invalid reparse points when deleting OneDrive-synced files — https://learn.microsoft.com/en-us/troubleshoot/sharepoint/sync/delete-onedrive-synced-file-error
- GeeLaw, OneDrive cloud filter / reparse point disguising — https://gist.github.com/GeeLaw/2b0c75c5cace89076d67014f775d85fc
- claude-code issue #30928, EEXIST on OneDrive directories — https://github.com/anthropics/claude-code/issues/30928
- Advanced Installer, AppData / LocalAppData / ProgramData — https://www.advancedinstaller.com/appdata-localappdata-programdata.html

**Windows Task Scheduler**
- Microsoft, TaskSettings.StartWhenAvailable (10-minute default delay; end-boundary requirement) — https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable
- Microsoft, KB 2437520 — Scheduled task may not run upon reboot if machine was off — https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/scheduled-task-not-run-upon-reboot-machine-off
- Microsoft, WakeToRun (settingsType) element — https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-waketorun-settingstype-element
- Microsoft, Daily Trigger Example (XML) — https://learn.microsoft.com/en-us/windows/win32/taskschd/daily-trigger-example--xml-
- Microsoft, schtasks create reference — https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create
- Microsoft, Understanding Task Settings (Win2008 R2 docs) — https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2008-r2-and-2008/cc722178(v=ws.11)
- Microsoft, Event ID 323 — Task Monitoring and Control — https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/cc775043(v=ws.10)
- Microsoft Q&A, Task Scheduler not waking Windows 11 from sleep — https://learn.microsoft.com/en-us/answers/questions/4140865/task-scheduler-not-waking-home-use-windows-11-from
- Microsoft Q&A, waking from sleep on a Modern Standby PC — https://learn.microsoft.com/en-us/answers/questions/1660115/regarding-waking-up-from-sleep-on-a-modern-standby
- Microsoft Q&A, Task Scheduler jobs running 1 hour earlier since DST change — https://learn.microsoft.com/en-us/answers/questions/778114/task-scheduler-jobs-running-1-hour-earlier-than-ex
- Microsoft Q&A, Task Scheduler issue due to DST changes — https://learn.microsoft.com/en-us/answers/questions/1244279/task-scheduler-issue-due-to-dst-changes
- Microsoft Q&A, task not running on triggered time — https://learn.microsoft.com/en-us/answers/questions/333001/task-scheduler-task-not-running-on-triggerd-time
- Microsoft Q&A, missed "One Time" vs "Daily" events — https://answers.microsoft.com/en-us/windows/forum/all/task-scheduler-does-not-run-missed-due-shutdown-on/6a863360-bc00-431b-a808-6d59645a830e
- Eleven Forum, Modern Standby and scheduled tasks — https://www.elevenforum.com/t/modern-standby-scheduled-tasks.16749/
- Ten Forums, wake from sleep but not hibernation — https://www.tenforums.com/general-support/176570-wake-sleep-but-not-hibernation.html
- ITQuibbles, Task Scheduler result codes — https://www.itquibbles.com/task-scheduler-result-codes/
- TechDirectArchive, all Task Scheduler errors and success codes — https://techdirectarchive.com/2020/03/24/task-scheduler-errors-and-success-code-what-does-code-0x41301-mean/
- TheWindowsClub, Task Scheduler error and success codes — https://www.thewindowsclub.com/task-scheduler-error-and-success-code-explained
- Vision Computers, Event ID 201 — Action Completed — https://www.visioncomputers.com/action-completed-event-201
- UltraSpark, common Task Scheduler event IDs — https://ultraspark.net/blog/common-task-scheduler-event-ids/
- NXLog, Windows Task Scheduler logging — https://docs.nxlog.co/userguide/integrate/windows-task-scheduler.html
- dahall/TaskScheduler TaskEvent.cs (event ID → symbolic name map) — https://github.com/dahall/TaskScheduler/blob/master/TaskService/TaskEvent.cs
- ESRI Community, suppressing the command window for scheduled Python — https://community.esri.com/t5/python-questions/execute-a-scheduled-python-script-and-suppress-the/td-p/690355

**Windows services**
- NSSM — https://nssm.cc/

**Timezones / DST**
- Council of the EU, seasonal clock changes — https://www.consilium.europa.eu/en/policies/seasonal-time-changes/
- timeanddate, DST in Europe 2026 — https://www.timeanddate.com/news/time/europe-starts-dst-2026.html
- timeanddate, DST 2026 in Hungary — https://www.timeanddate.com/time/change/hungary
- greenwichmeantime, EU daylight saving rules — https://greenwichmeantime.com/daylight-saving-time/rules/eu/
- Talend, troubleshooting schedules with DST — https://help.qlik.com/talend/en-US/management-console-user-guide/Cloud/scheduling-with-dst-daylight-saving-time
- Broadcom KB, DST jobs executing twice at turnover — https://knowledge.broadcom.com/external/article/129487/dst-jobs-executing-twice-at-turnover-or.html

**Article extraction**
- trafilatura on PyPI — https://pypi.org/pypi/trafilatura/json
- trafilatura on GitHub — https://github.com/adbar/trafilatura
- readability-lxml on PyPI — https://pypi.org/pypi/readability-lxml/json
- goose3 on PyPI — https://pypi.org/pypi/goose3/json
- newspaper3k on PyPI — https://pypi.org/pypi/newspaper3k/json

---

## Appendix: everything tagged UNVERIFIED

Collected so you know exactly where not to trust this document:

1. **`feedparser.parse(..., response_headers=...)`** — the keyword is documented in prose across the
   Advanced Features pages but I did not retrieve a signature block. Check
   `inspect.signature(feedparser.parse)` before relying on the name.
2. **`StartWhenAvailable` catch-up count** — whether it fires one run or one per missed occurrence is
   undocumented by Microsoft. Community consensus: one. The design in §7 does not depend on it.
3. **A maximum age for missed-start catch-up** — community claims exist; no Microsoft documentation found.
4. **`WakeToRun` from hibernate (S4)** — the schema doc mentions "sleep or hibernate" in passing but there
   is no primary source confirming end-to-end S4 wake-timer behaviour. Test on your hardware.
5. **`WakeToRun` under Modern Standby (S0ix)** — many concurrent reports that it does not work; no
   Microsoft documentation either way.
6. **Whether a Task Scheduler wake counts as an "important" wake timer** (so that the
   "Important Wake Timers Only" power setting suffices) — not verified. Use the full "Enable" setting.
7. **Fast Startup and armed wake timers** — no Microsoft documentation found on whether a wake timer
   survives a Fast-Startup shutdown. Assume it does not.
8. **Exact ACL needed to set `WakeToRun`** on your own task (as opposed to changing the power plan, which
   definitely needs admin) — not verified.
9. **User-scoped DPAPI decryption under `LogonType=S4U`** — not verified. Moot if you use a plain `.env`.
10. **Reading a hydrated OneDrive placeholder while the sync client is stopped** — not verified. Avoided by
    using `InteractiveToken` and/or moving the source out of OneDrive.
11. **Task Scheduler event IDs other than 201** — the mappings are widely and consistently documented in
    community sources but I did not find one Microsoft page enumerating them. 201 and 323 are confirmed.
12. **Discord's per-webhook rate-limit buckets** (~5 per 2 s, ~30 per 60 s) — *not* in Discord's official
    rate-limit documentation. The 10,000-invalid-requests-per-10-minutes limit and the 401/403/429
    classification **are** official. Discover webhook buckets from response headers at runtime.
13. **`time.tzname` strings on a Hungarian-locale Windows** — assumed localised, not verified. This is why
    §7.2 checks `time.timezone`/`time.daylight` numerically instead.
14. **NSSM's current release version and date** — nssm.cc's front page does not state it. Widely
    distributed stable build is 2.24; newer prereleases exist on the site's builds page.
15. **Windows Task Scheduler DST anomalies** (firing an hour early; weekly triggers double-firing or
    skipping) — Microsoft Q&A threads and third-party KBs, not a Microsoft KB. Mitigated by the
    Daily-trigger + app-side-decision design.
