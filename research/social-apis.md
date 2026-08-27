# social-apis — Cost, quota and legality of programmatic social monitoring (verified 2026-08-24)

Research for `gta6-news-bot`. Locked context: English-only output, custom Python 3.12 bot,
self-hosted on the user's Windows 10 PC, daily digest + instant alerts for first-party news.

**Verification method note:** claims marked `EMPIRICAL` were tested with `curl` from the user's
own machine (residential Hungarian IP, 2026-08-24). Claims marked `PRIMARY` come from the
vendor's own docs. Claims marked `BLOG` could not be confirmed against a primary source —
several vendor legal/pricing pages actively block automated fetching (see Caveats).

---

## 1. X / Twitter API — pricing model changed to pay-per-use

`PRIMARY` — https://docs.x.com/x-api/getting-started/pricing and https://docs.x.com/x-api/introduction

The subscription-tier model (Free / Basic $200 / Pro $5,000) is **gone from current docs**.
The docs now state: *"pay-per-usage pricing. No subscriptions—pay only for what you use."*
and *"Purchase credits upfront. Deducted as you use the API."*

### Rate card (exact, from the pricing page)

| Operation | Price |
|---|---|
| Posts: Read | **$0.005 per resource** |
| User: Read | **$0.010 per resource** |
| Owned Reads (all types) | **$0.001 per resource** |
| Post: Create | $0.015 per request |
| Post: Create (with URL) | **$0.200 per request** |

### Constraints (primary)

- **Monthly cap:** *"pay-per-usage plans are capped at 3 million Post reads per monthly billing cycle."* Above that → Enterprise.
- **THE CRITICAL ONE — deduplication:** *"Deduplication occurs within a 24-hour UTC window for identical resources."* Re-reading the same post ID within the same UTC day is **not billed again**. This transforms polling economics: a poller that sees the same 10 posts 96×/day pays for 10 reads, not 960.
- **No free tier.** No free allowance of any kind for reads.
- Auto-recharge with configurable threshold/amount; **spending limits settable per billing cycle** (use this as a hard safety rail).
- Up to 20% back in xAI API credits at $1,000+/mo cumulative spend (irrelevant at this scale).
- Minimum credit purchase and credit-expiry policy: **not stated** on the pricing page.

### Cost model for this bot

Monitoring ~5 first-party accounts (@RockstarGames, @GTA, @RockstarNewswire etc.) via
`GET /2/users/:id/tweets`:

| Assumption | Math | Monthly |
|---|---|---|
| 5 accounts × 10 posts in response, dedup means ≤10 unique/account/UTC-day | 5 × 10 × $0.005 × 30 | **≈ $7.50** |
| Same, but tighter `max_results=5` | 5 × 5 × $0.005 × 30 | **≈ $3.75** |
| Realistic (few genuinely new posts/day) | ~25 new posts/day × $0.005 × 30 | **≈ $3.75** |

Plus a one-time `users/by/username` lookup at $0.010 each — cache the numeric IDs in SQLite forever.

So: **roughly $4–8/month**, IF the 24h dedup behaves as documented. Poll frequency barely
matters because of dedup — which means you can poll *often* for instant alerts at near-zero
marginal cost. That is a genuinely favourable change vs the old $200/mo Basic tier.

### Legality / ToS

- `BLOG` X ToS bars crawling or scraping *"in any form, for any purpose"* without prior written consent, and reportedly sets **liquidated damages at $15,000 per 1,000,000 posts** requested/viewed/accessed in any 24-hour period. Terms update effective **Jan 15, 2026**. Could not verify from primary — see Caveats.
- Using a logged-in account's `auth_token`/`ct0` cookies to read (Nitter, RSSHub twitter route) **violates the ToS** and risks account suspension. Not a grey area.

### RECOMMENDED APPROACH FOR X

**Use the official API with prepaid credits and a hard spending limit.** Concretely:
1. Buy a small credit balance; set the per-cycle spending limit to ~$15 so a bug cannot drain it.
2. Cache numeric user IDs in SQLite (avoid repeat $0.010 user reads).
3. Poll `GET /2/users/:id/tweets` with `since_id` persisted per account; small `max_results`.
4. Lean on the 24h UTC dedup — poll every 5–10 min for instant alerts without multiplying cost.
5. Store `newest_id` so a PC sleep/wake gap backfills rather than double-posts.

**But consider deprioritising X entirely.** For GTA 6 specifically, Rockstar's announcements
land on Newswire and YouTube first; X is a mirror. YouTube RSS + Newswire + Bluesky cover the
same news for $0. Treat X as an optional paid add-on, not the backbone.

---

## 2. Reddit — both `.json` AND `.rss` are now 403 unauthenticated

### EMPIRICAL test results (2026-08-24, residential IP, plain curl + browser UA)

| URL | Result |
|---|---|
| `https://www.reddit.com/r/GTA6/new.json?limit=5` | **403** |
| `https://www.reddit.com/r/GTA6/new/.rss` | **403** |
| `https://old.reddit.com/r/GTA6/new.json?limit=5` | **403** |
| `https://oauth.reddit.com/r/GTA6/new?limit=5` (no token) | 403 (expected) |

This is the single most important finding in this document: **the "just use Reddit RSS, no auth
needed" approach is dead.** `.rss` is blocked too, not just `.json`. Any design that assumes
unauthenticated Reddit access will fail on first run.

### Terms and limits

- `BLOG` Reddit announced deprecation of unauthenticated `.json` endpoints around **May 28, 2026**; RSS was flagged as the next surface to close. Consistent with the empirical 403s on both.
- `BLOG` Free tier: **100 queries/minute per OAuth client** for non-commercial use (personal projects, bots, mod tools, academic research), averaged over a 10-minute window so bursts are allowed. **10 QPM** if unauthenticated (now moot — unauthenticated is 403).
- `BLOG` **OAuth is mandatory.** No API-key-only path.
- `BLOG` Commercial use requires Reddit approval, billed **$0.24 per 1,000 API calls**.
- `BLOG` **Responsible Builder Policy** (announced on r/redditdev, late 2025): self-service app registration closed. Every new OAuth client — free or paid — goes through a **manual approval ticket** with a slow, opaque queue and real chance of silent rejection.
- `BLOG` Data API Terms bar you from *"sell, lease, or sublicense the Data APIs ... or derive revenues from the use or provision of the Data APIs"* without written approval.

### ToS risk specific to this user

An RP community Discord that takes donations / sells in-game perks could plausibly be read as
**commercial use**. Combined with the manual-approval gate, Reddit is the highest-friction,
highest-legal-ambiguity source in this project.

### Recommendation

**Drop Reddit from v1.** Rationale: mandatory OAuth + manual app approval with possible silent
rejection + commercial-use ambiguity + Reddit actively closing surfaces. It is a community-chatter
source, not a first-party news source, so it does not serve the "instant alerts for official news"
requirement anyway. Revisit only if the user specifically wants subreddit discussion in the digest,
and then only via an approved OAuth client.

---

## 3. YouTube Data API v3 vs channel RSS — the quota model CHANGED

### `PRIMARY` — quota allocation (confirmed twice, on two different Google pages)

https://developers.google.com/youtube/v3/getting-started and
https://developers.google.com/youtube/v3/determine_quota_cost both now state:

> *"Projects that enable the YouTube Data API have a default quota allocation of **100 `search.list` calls, 100 `videos.insert` calls, and 10,000 units per day** combined for all other endpoints."*

This is a **change from the long-standing model** where `search.list` cost 100 units out of a
single 10,000-unit pool. `search.list` is now metered as a **separate 100-calls/day allowance**.
Do not repeat the widely-cited "100 searches burns your whole 10k quota" claim — the docs no
longer describe it that way.

Also primary: *"All API requests, even if invalid, will cost at least one quota point."*
Pagination costs the quota again per supplementary page. Quota resets midnight Pacific.
No self-service quota purchase — extensions require a manual audit form.

### The free alternative — channel RSS `EMPIRICAL`, works

```
https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>
```

- HTTP **200**, no API key, no quota, no OAuth, no cost.
- **Rockstar Games channel ID verified: `UC6VcWc1rAoWdBCM0JxrRQ3A`**
  (resolved from the `@RockstarGames` channel page; 47 occurrences vs noise).
- Feed content on 2026-08-24 already included: *"Grand Theft Auto VI: An Extended Look Coming August 27"* and *"GTA Online: The Kortz Center Heist Now Available"*. Directly on-topic.
- Returns ~15 most recent videos. Atom format — `feedparser` handles it, or stdlib `xml.etree`.

**Recommendation: use RSS, skip the Data API entirely.** Zero quota risk, zero key management,
no Google Cloud project needed. Caveats: RSS latency is minutes-to-hours (not instant), and
Shorts/premieres/unlisted-then-public items can appear inconsistently. If a hard "within 60s of
publish" SLA were required you'd need the API — it isn't required here.

---

## 4. Third-party routes — mostly dead or ToS-violating

### RSSHub

`EMPIRICAL` — the public instance `rsshub.app` is Cloudflare-gated and **unusable programmatically**:

| Route | Result |
|---|---|
| `https://rsshub.app/twitter/user/RockstarGames` | **302** → Cloudflare interstitial |
| `https://rsshub.app/reddit/subreddit/GTA6/new` | **403** `"Just a moment..."` |
| `https://rsshub.app/youtube/channel/UC6VcWc1rAoWdBCM0JxrRQ3A` | **403** |

- Self-hosting is therefore **mandatory** (Docker image + Redis dependency). Extra moving parts on a Windows PC that sleeps.
- X routes require `TWITTER_COOKIE` (`auth_token` + `ct0`) from a logged-in account → **ToS violation + ban risk**. GitHub issue [#19420](https://github.com/DIYgod/RSSHub/issues/19420) shows the route returning HTTP 200 with **silently empty content** — the worst failure mode for a news bot (looks healthy, delivers nothing).
- The RSSHub Reddit route depends on Reddit `.json`, which is now 403 → **presumed broken**.
- Verdict: **not recommended.** Adds Docker+Redis, ToS exposure, and silent-failure modes to replace things that either work for free (YouTube) or work cheaply and legally (X official API).

### RSS-Bridge

- `BLOG` Last release **2025-01-02** — ~20 months stale as of today.
- Legacy `TwitterBridge` broke Feb 2023. `TwitterV2Bridge` works only if you supply **your own paid X API bearer token** — i.e. it saves nothing over calling the API directly.
- Reddit bridge relies on `.json` → **presumed broken** given the 403s.
- Verdict: no value here.

### Nitter

- `BLOG` **Effectively dead.** Declared discontinued by its developer after X removed guest accounts in Jan 2024; the public instance network has collapsed.
- Self-hosting now requires creating real X session tokens → **ToS violation**.
- Verdict: **do not use.** Treat any "working Nitter instance" list as stale.

### rss.app

- `BLOG` Free plan: **2 feeds, 1 widget, 24-hour refresh, 5 posts/feed.** A 24h refresh makes instant alerts impossible.
- Paid from **$8.32/mo** (annual billing) for faster refresh, more feeds, webhooks, filtering. Pro tier adds API access with 1,000 ops/month.
- Verdict: the free tier's 24h refresh disqualifies it; the paid tier costs about the same as just paying X directly, while adding a third-party dependency.

### Apify

- `BLOG` Free account: **$5/month platform credit.** X scraper actors **$0.15–$0.40 per 1,000 tweets**.
- Cheap per-unit, but it is **scraping X**, which violates X's ToS. Apify's model pushes the legal exposure onto you as the operator.
- Verdict: not recommended for a public-facing community bot.

---

## 5. Platforms that are actually free and legal

### Bluesky — best free option `EMPIRICAL`

Two working unauthenticated routes, both HTTP 200, no API key, no cost:

**Public AT Protocol AppView** (`public.api.bsky.app`, no auth supported, cached):
```
GET https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=<handle>&limit=3   → 200 JSON
GET https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=<handle>   → 200
GET https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=gta6                     → 403 (auth required)
```
So **author feeds are free and open; search requires authentication.**

**Native per-profile RSS** — verified redirect chain:
```
https://bsky.app/profile/<handle>/rss
  → 302 → https://bsky.app/profile/<did>/rss → 200  Content-Type: application/xml
```
Implementation note: **you must follow redirects** (`httpx.AsyncClient(follow_redirects=True)`),
otherwise you get a bare 302 and no content. Resolving handle→DID once and caching the DID URL
avoids the redirect on every poll.

- Rate limits: official docs say only "generous" for `public.api.bsky.app`; `BLOG` figures are ~3,000 requests / 5 min per IP, and 5,000 points/hour + 35,000/day for *authenticated* writes. No numeric public-read limit is published.
- Note: `docs.bsky.app` now **301-redirects to `bsky.network/docs`**; the new host returned empty content to automated fetches.
- **Unverified:** whether Rockstar Games maintains an official Bluesky account. Check before relying on it as a first-party source.

### Mastodon — free `EMPIRICAL`

`https://mastodon.social/@<user>.rss` → **200**. Standard on any Mastodon instance, no auth, no key.
Cannot be revoked the way a closed platform's API can. Useful only if a relevant account exists.

### Threads

`BLOG` Requires Meta **App Review** for `threads_content_publish`, `threads_manage_replies`,
`threads_manage_insights`, and the app must be published. No practical public read API for
arbitrary third-party accounts. **Skip.**

### TikTok

`BLOG` Research API is **academic-only** (qualifying institutions in US/EEA/UK/Switzerland,
EU non-profits, some Brazilian researchers), **commercial use prohibited**, rate limited to
**1,000 requests/day**. Independent devs and for-profit orgs are excluded. **Not accessible — skip.**

---

## 6. Rockstar Newswire has NO RSS feed `EMPIRICAL`

The most important first-party source for this bot does not expose a feed:

| URL | Result |
|---|---|
| `https://www.rockstargames.com/newswire` | **200** (HTML page exists) |
| `https://www.rockstargames.com/newswire.rss` | 404 |
| `https://www.rockstargames.com/newswire/feed` | 404 |
| `https://www.rockstargames.com/newswire/rss` | 404 |
| `https://www.rockstargames.com/feed.xml` | 404 |
| `https://www.rockstargames.com/rss` | 404 |

A probe for embedded `/api/...` or `newswire/api...` paths in the HTML returned nothing, so the
page is likely server-rendered or uses a non-obvious data route. **Instant alerts on official
Rockstar news therefore require polling and parsing the Newswire HTML** (or finding its internal
JSON route by inspecting the page in a browser — worth doing, as a JSON route would be far more
robust than HTML scraping). This is first-party public content, polite low-frequency polling with
a real User-Agent and conditional requests (ETag/If-Modified-Since) is the reasonable approach.

---

## 7. Recommended source stack for gta6-news-bot

| Priority | Source | Method | Cost | Legality |
|---|---|---|---|---|
| 1 | Rockstar Newswire | HTML poll + ETag (find internal JSON route if possible) | $0 | Fine — public first-party page |
| 2 | Rockstar YouTube | `feeds/videos.xml?channel_id=UC6VcWc1rAoWdBCM0JxrRQ3A` | $0 | Fine — official feed |
| 3 | Bluesky (if account exists) | `public.api.bsky.app` getAuthorFeed, or `/profile/<did>/rss` | $0 | Fine — public API |
| 4 | X / Twitter | Official API v2 + prepaid credits + spending limit | ~$4–8/mo | Fine via official API |
| — | Mastodon | `@user.rss` | $0 | Fine |
| SKIP | Reddit | OAuth + manual approval; `.json`/`.rss` both 403 | — | Commercial-use ambiguity |
| SKIP | RSSHub / RSS-Bridge / Nitter | cookie-based X access | — | **ToS violation** |
| SKIP | Apify | scraping X | $0.15–0.40/1k | **ToS violation** |
| SKIP | Threads, TikTok | app review / academic-only | — | Not accessible |

### Explicit ToS violations to avoid

1. Supplying logged-in X account cookies (`auth_token`/`ct0`) to RSSHub, Nitter, or any self-hosted front-end — violates X ToS, risks account suspension.
2. Scraping X HTML directly or via Apify — X ToS bars crawling/scraping "in any form, for any purpose" without written consent.
3. Circumventing Reddit's 403 on `.json`/`.rss` (rotating IPs, browser-cookie replay) — violates Reddit's Data API Terms and the Responsible Builder Policy.
4. Using Reddit's free non-commercial tier for a monetised RP community without checking commercial-use status.
5. TikTok Research API for any non-academic/commercial purpose — expressly prohibited.

### Design implications for the bot

- **X 24h UTC dedup window** interacts with the PC-sleep catch-up requirement: after a long sleep, the first poll of a new UTC day re-bills posts already seen. Persist `newest_id` per account in SQLite so you request only genuinely new posts and don't re-fetch history.
- Bluesky RSS needs `follow_redirects=True`; cache handle→DID.
- All feeds here are pollable with `httpx` + `feedparser`; `feedparser` is **not currently installed** (per environment notes) and would be the one new dependency, unless you parse Atom/RSS with stdlib `xml.etree.ElementTree` — viable given only 2–3 feed shapes.
- Store per-source `etag` / `last_modified` to keep polling cheap and polite.

---

## Caveats

1. **Vendor legal/pricing pages actively blocked automated fetching.** `x.com/en/tos` → HTTP 402; `developer.x.com/en/products/x-api` → HTTP 402; `help.x.com/.../x-automation` → 403; `www.redditinc.com/policies/data-api-terms` → blocked; `support.reddithelp.com` → 403. The X ToS scraping clause and the **$15,000 per 1,000,000 posts** liquidated-damages figure are therefore **BLOG-sourced and unverified**. Treat the exact number as indicative; the existence of a scraping prohibition is well established.
2. The X ToS PDF at `cdn.cms-twdigitalassets.com/.../x-terms-of-service-2025-05-08.pdf` **301-redirects to `x.ai/careers`** — a broken/hijacked CDN path. Do not cite it.
3. **Reddit's 403s could be IP-reputation-based** rather than a global policy block. Testing was from a single residential Hungarian IP. The result is what this bot would experience from this machine, which is what matters operationally — but it is not proof of a universal block. Retest before concluding Reddit is permanently closed.
4. **X legacy tier availability is unclear.** Current docs make no mention of Basic ($200) or Pro ($5,000). Blogs claim they persist for existing subscribers only, closed to new signups. Since the user has no existing subscription, pay-per-use is the only relevant path either way.
5. **X minimum credit purchase and credit expiry are undocumented** on the pricing page. Blogs claim $10 minimum and no expiry — unverified. Confirm in the Developer Console before budgeting.
6. **The X 24h dedup semantics are load-bearing for the cost estimate** but only one sentence of documentation supports them. If dedup turns out to be per-request-type rather than per-resource, polling costs could be 10–100× higher. **Set a hard spending limit before the first run and check actual spend after 48h.**
7. The YouTube `search.list` quota change (separate 100-calls/day allowance) was confirmed on two Google pages but contradicts a large body of older third-party writing. It does not affect the recommendation (use RSS, no quota at all).
8. **Rockstar's Bluesky presence was not verified.** Confirm the account exists before wiring it in.
9. Rockstar YouTube channel ID `UC6VcWc1rAoWdBCM0JxrRQ3A` was resolved by frequency analysis of the channel HTML and confirmed by fetching the feed (title `Rockstar Games`, on-topic GTA 6 items). High confidence, but a one-line assertion in code should still be accompanied by a startup sanity check on the feed title.
10. Prices and quotas are as of **2026-08-24** and all vendors reserve the right to change them. The X pricing page explicitly says current rates live in the Developer Console.

---

## All URLs found

### Primary / vendor
- https://docs.x.com/x-api/getting-started/pricing — X pay-per-usage rate card (PRIMARY, fetched OK)
- https://docs.x.com/x-api/introduction — X "no subscriptions / credits" statement (PRIMARY, fetched OK)
- https://developer.x.com/en/products/x-api — HTTP 402, blocked
- https://x.com/en/tos — HTTP 402, blocked
- https://help.x.com/en/rules-and-policies/x-automation — 403, blocked
- https://cdn.cms-twdigitalassets.com/content/dam/legal-twitter/site-assets/terms-of-service-2025-05-08/en/x-terms-of-service-2025-05-08.pdf — 301s to x.ai/careers, broken
- https://developers.google.com/youtube/v3/getting-started — YouTube quota allocation (PRIMARY, fetched OK)
- https://developers.google.com/youtube/v3/determine_quota_cost — YouTube per-method costs (PRIMARY, fetched OK)
- https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits — quota extension audits
- https://docs.bsky.app/docs/advanced-guides/rate-limits — 301 → bsky.network
- https://bsky.network/docs/advanced-guides/rate-limits — returned empty to automated fetch
- https://bsky.network/docs/rate-limits/ — Bluesky protocol services rate limits
- https://www.redditinc.com/policies/data-api-terms — blocked
- https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki — 403
- https://rss.app/pricing — rss.app pricing
- https://help.rss.app/en/articles/10657918-guide-to-pricing-and-feed-limits — feed limits
- https://help.rss.app/en/collections/13025947-pricing-and-plans

### Endpoints tested empirically
- https://www.reddit.com/r/GTA6/new.json?limit=5 — 403
- https://www.reddit.com/r/GTA6/new/.rss — 403
- https://old.reddit.com/r/GTA6/new.json?limit=5 — 403
- https://oauth.reddit.com/r/GTA6/new?limit=5 — 403 (no token)
- https://www.youtube.com/feeds/videos.xml?channel_id=UC6VcWc1rAoWdBCM0JxrRQ3A — 200, Rockstar Games
- https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw — 200 (control)
- https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=bsky.app — 200
- https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=gta6 — 403
- https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=bsky.app — 200
- https://bsky.app/profile/bsky.app/rss — 302 → https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur/rss — 200 application/xml
- https://mastodon.social/@Gargron.rss — 200
- https://www.rockstargames.com/newswire — 200
- https://www.rockstargames.com/newswire.rss , /newswire/feed , /newswire/rss , /feed.xml , /rss — all 404
- https://rsshub.app/twitter/user/RockstarGames — 302 Cloudflare
- https://rsshub.app/reddit/subreddit/GTA6/new — 403 Cloudflare challenge
- https://rsshub.app/youtube/channel/UC6VcWc1rAoWdBCM0JxrRQ3A — 403

### Third-party tools / repos
- https://github.com/DIYgod/RSSHub — RSSHub repo
- https://github.com/DIYgod/RSSHub/issues/19420 — X route returns 200 with empty content
- https://github.com/DIYgod/RSSHub/issues/16014 — Twitter 403 forbidden
- https://github.com/DIYgod/RSSHub/issues/17046 — X route InvalidArgumentError
- https://github.com/DIYgod/RSSHub/discussions/14956 — TWITTER_COOKIE config
- https://github.com/DIYgod/RSSHub/issues/14910 — TWITTER_COOKIE config
- https://docs.rsshub.app/routes/ — RSSHub route index (social-media subpage 404'd)
- https://hub.docker.com/r/diygod/rsshub — RSSHub Docker image
- https://github.com/RSS-Bridge/rss-bridge — RSS-Bridge repo
- https://github.com/RSS-Bridge/rss-bridge/releases — last release 2025-01-02
- https://github.com/RSS-Bridge/rss-bridge/issues/3603 — Twitter bridge help
- https://hub.docker.com/r/rssbridge/rss-bridge
- https://apify.com/apidojo/tweet-scraper — Tweet Scraper V2
- https://apify.com/xquik/x-tweet-scraper — $0.15/1k tweets
- https://apify.com/epctex/twitter-scraper
- https://github.com/vhogemann/rss2bsky
- https://github.com/CrackTC/xtoken

### Secondary / blog (used only where primary was blocked)
- https://twitterapi.io/blog/x-api-cost-breakdown-2026
- https://postproxy.dev/blog/x-api-pricing-2026/
- https://www.socialcrawl.dev/blog/x-twitter-api-2026
- https://xautodm.com/blog/x-api-pricing-explained-2026-cheaper-alternatives
- https://www.getxapi.com/twitter-api-pricing
- https://www.getxapi.com/pay-per-use-pricing
- https://www.netrows.com/blog/x-twitter-api-pricing-tiers-2026
- https://www.xpoz.ai/blog/guides/understanding-twitter-api-pricing-tiers-and-alternatives/
- https://api.sorsa.io/blog/twitter-api-pricing-2026
- https://tweetstream.io/blog/twitter-api-pricing
- https://opentweet.io/how-to/x-api-pay-per-use-explained
- https://opentweet.io/blog/twitter-automation-rules-2026
- https://nftnow.com/news/x-updates-terms-of-service-to-ban-unauthorized-data-crawling-scraping/
- https://techcrunch.com/2023/09/08/x-updates-its-terms-to-ban-crawling-and-scraping
- https://crypto.news/x-expands-content-to-ai-prompts-outputs-in-2026-terms-update/
- https://grokipedia.com/page/2026_X_terms_of_service_update
- https://www.socialcrawl.dev/blog/reddit-data-api-2026
- https://octolens.com/blog/reddit-api-pricing
- https://snitchfeed.com/blog/reddit-api-pricing
- https://www.painpointmap.com/blog/reddit-api-rate-limits-guide
- https://www.redditapis.com/blogs/reddit-api-pricing-2026
- https://www.redditapis.com/blogs/reddit-api-rate-limits-2026
- https://www.redditapis.com/blogs/reddit-json-endpoint-dead-2026
- https://www.redditapis.com/blogs/reddit-developer-platform-migration-2026
- https://www.redditapis.com/blogs/reddit-data-api-2026
- https://rawneed.com/guides/reddit-api-pricing-explained/
- https://prowlo.com/blog/reddit-data-api
- https://crawlora.net/blog/reddit-json-api-blocked-2026
- https://crawlora.hashnode.dev/why-reddit-blocked-unauthenticated-json-in-2026-and-how-to-still-get-reddit-data
- https://fetchlayer.dev/blog/reddit-api-closed-2026
- https://www.socialcrawl.dev/blog/youtube-data-api-2026
- https://www.getphyllo.com/post/youtube-api-limits-how-to-calculate-api-usage-cost-and-fix-exceeded-api-quota
- https://outlierkit.com/resources/youtube-api-quota/
- https://channelcrawler.com/insights/youtube-api-daily-limit-quotas-costs-and-how-to-scale-beyond-10000-units-channelcrawler
- https://elfsight.com/blog/youtube-data-api-v3-limits-operations-resources-methods-etc/
- https://simple-web.org/guides/nitter-alternatives-2026-view-twitter-x-timelines-anonymously
- https://techradar.info/is-nitter-still-working-the-definitive-2026-status-report/
- https://alternativeto.net/news/2024/1/privacy-oriented-x-front-end-nitter-is-shutting-down-following-changes-to-guest-accounts/
- https://perennialte.ch/blog/2024/02/14/public-nitter-instance-shutdown/
- https://www.cogipas.com/nitter-shut-down-x-twitter-alternatives/
- https://deepwiki.com/bluesky-social/bsky-docs/4.3-rate-limits-and-performance
- https://getskyscraper.com/blog/bluesky-rate-limits-api-guide
- https://publishq.com/blog/bluesky-api-post-limits
- https://www.blotato.com/blog/bluesky-api-pricing
- https://www.blotato.com/blog/social-media-api
- https://www.blotato.com/blog/tiktok-api-pricing
- https://alternativeto.net/news/2024/1/bluesky-social-media-platform-launches-rss-feeds-enhancing-user-experience
- https://singhamandeep.com/threads-api-app-review-permissions/
- https://www.xpoz.ai/blog/guides/tiktok-research-api-limits-access-and-alternatives/
- https://sociavault.com/blog/tiktok-data-without-research-api-2026
- https://sociavault.com/blog/tiktok-api-free-2026
- https://www.twitterapis.com/blogs/apify-twitter-scraper-vs-twitterapis-2026
- https://use-apify.com/docs/best-apify-actors/best-twitter-scrapers
- https://www.linkstartai.com/en/agents/rss-app
