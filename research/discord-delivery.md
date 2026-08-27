# Discord Delivery Mechanics — GTA 6 News Bot

Research date: **2026-08-25**. Supersedes the 2026-08-24 draft; adds AutoMod rule content,
channel/permission layout, library status, policy, and crosspost detail.

Target: post-only Python 3.12 bot on the user's own Windows PC. One 18:00 digest to `#news`,
instant alerts for first-party sources only, pinging an **opt-in** role, never `@everyone`.

> **Doc host moved.** `discord.com/developers/docs/*` now **301-redirects** to
> `docs.discord.com/developers/*`. Use the new host.
> `support.discord.com` and `support-dev.discord.com` return **HTTP 403** to automated fetchers,
> so support-site facts below come from search snippets, not direct primary fetch.

**Confidence legend:**

- **[OFFICIAL]** — read directly from Discord's official API reference / policy page.
- **[SUPPORT]** — Discord's own support/safety site, retrieved via search snippet (403 on fetch).
  Re-verify in a browser before hard-coding.
- **[UNVERIFIED]** — widely reported by the community, **NOT** in official docs. Do not hard-code
  with a comment claiming Discord documents it. Discover it from response headers at runtime instead.

---

## 1. QUICK REFERENCE TABLE — every hard numeric limit

### 1.1 Message & embed limits

| Thing | Limit | Confidence |
|---|---|---|
| `content` — **Execute Webhook** | **2000** characters | [OFFICIAL] |
| `content` — **Create Message** (bot token) | docs render **4000**; see §4.1 — **use 2000** | **[AMBIGUOUS]** |
| Human user message | 2000 (4000 with full Nitro; Nitro **Basic** stays 2000) | [SUPPORT] |
| Embeds per message | **10** | [OFFICIAL] |
| `embed.title` | **256** | [OFFICIAL] |
| `embed.description` | **4096** | [OFFICIAL] |
| Fields per embed | **25** | [OFFICIAL] |
| `field.name` | **256** | [OFFICIAL] |
| `field.value` | **1024** | [OFFICIAL] |
| `footer.text` | **2048** | [OFFICIAL] |
| `author.name` | **256** | [OFFICIAL] |
| **TOTAL across ALL embeds in one message** | **6000** | [OFFICIAL] |
| `allowed_mentions.roles` array | max **100** snowflakes | [OFFICIAL] |
| `allowed_mentions.users` array | max **100** snowflakes | [OFFICIAL] |

The 6000 budget sums only `title` + `description` + `field.name` + `field.value` + `footer.text` +
`author.name`, across **every** embed in the message. **Excluded** from the sum: `url`, `image.url`,
`thumbnail.url`, `footer.icon_url`, `author.url`, `author.icon_url`, `timestamp`, `color`, and the
message-level `content`. So `content` is a **separate** budget on top of the 6000.

Violating any single constraint returns **`400 Bad Request`** and the *entire message is rejected* —
Discord does **not** silently truncate. Truncate client-side before sending.

### 1.2 Rate limits

| Thing | Limit | Confidence |
|---|---|---|
| Global, all bots | **50 requests/second** | [OFFICIAL] |
| Invalid-request / Cloudflare ban threshold | **10,000 per 10 minutes** | [OFFICIAL] |
| Statuses counted as "invalid" | **401, 403, 429** | [OFFICIAL] |
| Exclusion from that count | 429 with `X-RateLimit-Scope: shared` is **not** counted | [OFFICIAL] |
| Per-webhook execute | ~**30 requests / 60 s** per webhook ID | **[UNVERIFIED]** |
| Per-channel message send | ~**5 messages / 5 s** | **[UNVERIFIED]** |
| Crosspost / "Publish" | **10 per hour** | [SUPPORT] |
| Emoji routes | per-guild, does not follow normal conventions | [OFFICIAL] |

### 1.3 AutoMod limits

| Thing | Limit | Confidence |
|---|---|---|
| `KEYWORD` (trigger type 1) rules per guild | **6** | [OFFICIAL] |
| `SPAM` (3) rules per guild | **1** | [OFFICIAL] |
| `KEYWORD_PRESET` (4) rules per guild | **1** | [OFFICIAL] |
| `MENTION_SPAM` (5) rules per guild | **1** | [OFFICIAL] |
| `MEMBER_PROFILE` (6) rules per guild | **1** | [OFFICIAL] |
| Max total AutoMod rules | **10** (6+1+1+1+1) | derived |
| `keyword_filter` entries | **1000**, each max **60** chars | [OFFICIAL] |
| `regex_patterns` entries | **10**, each max **260** chars | [OFFICIAL] |
| `allow_list` — KEYWORD | **100** entries, 60 chars each | [OFFICIAL] |
| `allow_list` — KEYWORD_PRESET | **1000** entries, 60 chars each | [OFFICIAL] |
| `allow_list` — MEMBER_PROFILE | **100** entries, 60 chars each | [OFFICIAL] |
| `mention_total_limit` | max **50** | [OFFICIAL] |
| Custom block message (`custom_message`) | **150** chars | [OFFICIAL] |
| Timeout duration max | **2,419,200 s** (4 weeks) | [OFFICIAL] |
| `exempt_roles` | **20** | [OFFICIAL] |
| `exempt_channels` | **50** | [OFFICIAL] |
| Regex flavour | **Rust** regex only. No lookahead/lookbehind/backreferences | [OFFICIAL] |

### 1.4 Channels, roles, application

| Thing | Limit | Confidence |
|---|---|---|
| Slow mode (`rate_limit_per_user`) | **0–21600** s (6 h). **Bots are unaffected** | [OFFICIAL] |
| Onboarding prerequisite | **≥7** default channels, **≥5** letting `@everyone` send | [SUPPORT] |
| Bot verification threshold | **100 servers** | [SUPPORT] |
| Privileged intents threshold (changed 2026) | **>10,000 unique users** — no longer 100 servers | [SUPPORT] |
| `GUILD_ANNOUNCEMENT` channel type | **5** | [OFFICIAL] |
| `GUILD_FORUM` channel type | **15** | [OFFICIAL] |
| API base / version | `https://discord.com/api/v10` | [OFFICIAL] |

### 1.5 Constants to paste into code

```python
# Hard API limits — see research/discord-delivery.md §1
DISCORD_CONTENT_MAX    = 2000    # Execute Webhook: officially 2000
EMBED_TOTAL_BUDGET     = 6000    # summed across ALL embeds in one message
EMBED_TITLE_MAX        = 256
EMBED_DESC_MAX         = 4096
EMBED_FIELD_NAME_MAX   = 256
EMBED_FIELD_VALUE_MAX  = 1024
EMBED_FOOTER_MAX       = 2048
EMBED_AUTHOR_MAX       = 256
EMBED_FIELDS_MAX       = 25
EMBEDS_PER_MESSAGE     = 10
GLOBAL_RPS             = 50      # all bots
INVALID_REQ_BUDGET     = 10_000  # per 10 min -> Cloudflare IP ban (401/403/429)
CROSSPOST_PER_HOUR     = 10      # [SUPPORT] verify in browser
SLOWMODE_MAX_SECONDS   = 21_600
```

**Do not hard-code the per-webhook or per-channel numbers.** Discord's own docs say rate limits may
change at any time and can differ per application. Read the headers (§3).

---

## 2. WEBHOOK VS BOT TOKEN

Source: https://docs.discord.com/developers/resources/webhook [OFFICIAL]

### 2.1 What a webhook token CAN do

`POST /webhooks/{webhook.id}/{webhook.token}` — Execute Webhook. Requires **at least one** of
`content`, `embeds`, `components`, `file`, or `poll`.

| Capability | Supported? | Notes |
|---|---|---|
| Post `content` | Yes | max **2000** chars |
| Post `embeds` | Yes | up to **10** |
| `allowed_mentions` | Yes | full object supported |
| Per-message `username` override | **Yes** | webhook-only superpower; a bot cannot do this |
| Per-message `avatar_url` override | **Yes** | webhook-only superpower |
| `tts` | Yes | never use it |
| File upload (`files[n]`, `attachments`, `payload_json`) | Yes | multipart |
| `flags` | Partial | **only** `SUPPRESS_EMBEDS`, `SUPPRESS_NOTIFICATIONS`, `IS_COMPONENTS_V2` |
| `thread_id` query param | Yes | posts into a thread, auto-unarchives it |
| `thread_name` | Yes | creates a **forum/media** channel thread |
| `applied_tags` | Yes | forum tags |
| `poll` | Yes | |
| **Edit own message** | **Yes** | `PATCH /webhooks/{id}/{token}/messages/{message.id}` |
| **Delete own message** | **Yes** | `DELETE /webhooks/{id}/{token}/messages/{message.id}` |
| **Get own message** | **Yes** | `GET /webhooks/{id}/{token}/messages/{message.id}` |
| `wait=true` to get the message object back | Yes | **required** if you want the message ID |

> **Correction to a very common myth:** webhooks **can** edit and delete their own messages. Those
> three message endpoints exist on the token-authenticated webhook route. This matters for the digest —
> you can post at 18:00 and PATCH it later if a story is corrected or retracted. **You must pass
> `wait=true` on the original execute call to receive the message ID**, otherwise you have nothing to
> PATCH against, and there is no "list my messages" endpoint on the webhook route. Persist the ID.

### 2.2 What a webhook token CANNOT do

| Cannot | Consequence for this project |
|---|---|
| **Add reactions** | No auto-reactions on digest posts. Needs a bot token (`PUT .../reactions/{emoji}/@me`). |
| **Crosspost / Publish** | Crosspost is `POST /channels/{id}/messages/{id}/crosspost` — a **`/channels`** route. Webhook tokens only authenticate `/webhooks/...` routes. See §5. |
| **Interactive components** | Official wording: *"Application-owned webhooks can always send components. Non-application-owned webhooks cannot send interactive components"* — and with `with_components=true` they get **non-interactive only**. So **no buttons, no select menus** from a plain incoming webhook. This kills a button-based role picker on webhooks alone. |
| **Start a thread on a text channel** | `thread_name` works on **forum/media** channels only. It cannot start a thread under a normal `#news` text post. |
| **Read anything** | No message history, no member list, no guild info beyond the webhook object. |
| **Configure AutoMod** | AutoMod routes are `/guilds/{id}/auto-moderation/rules`, bot token + `MANAGE_GUILD`. |
| **Assign roles** | Needs a bot token with `MANAGE_ROLES`. |
| **Timeout / moderate members** | Needs a bot token with `MODERATE_MEMBERS`. |

### 2.3 Can a webhook post to an Announcement channel?

**Yes.** An Announcement channel (`GUILD_ANNOUNCEMENT`, type 5) accepts webhook messages normally.
What the webhook cannot do is **publish** them. Two separate operations:

1. Posting into the announcement channel — webhook: **fine**.
2. Crossposting ("Publish") that message to follower servers — needs a **bot token** (§5).

### 2.4 Is a webhook rate-limited differently?

Yes.

- **Bot token** requests share your application's **global 50 req/s** budget, plus per-route buckets
  keyed on the major parameter (`channel_id` for message routes).
- **Webhook** execute calls are bucketed **per webhook ID**, reportedly ~**30 / 60 s**
  **[UNVERIFIED — not in official docs]**. Webhook token calls are not authenticated as your bot, so a
  runaway webhook loop cannot globally rate-limit your bot application.
- Both are subject to the **10,000 invalid requests / 10 minutes** Cloudflare ban, which is
  **per IP** — and this bot runs on the user's home PC. See §3.4. That is the real risk, and it is
  identical for both approaches.

For this workload the numbers are irrelevant either way: one digest per day plus a handful of instant
alerts is ~5–20 requests/day. You will never approach any limit unless you write a bug.

### 2.5 The webhook URL as a bearer credential

The URL is `https://discord.com/api/webhooks/{id}/{token}`. The token **is** the credential — no
separate secret, no signature, no IP allowlist.

**Blast radius if leaked:**

- Anyone can post arbitrary `content` + up to 10 embeds into **that one channel**, with **arbitrary
  `username` and `avatar_url`** — a perfect impersonation of your official news bot or of a moderator.
  This is the worst part: a leaked webhook lets an attacker post a fake "official" Rockstar item, or a
  leak link, wearing your bot's identity.
- They can **edit and delete** any message that webhook created.
- They **can mass-ping.** The *default* mention behaviour for webhooks is safe
  (`{"parse":["users"]}`, §6.3) — but the attacker controls the payload and can set
  `allowed_mentions: {"parse":["everyone","roles"]}` explicitly. Assume a leaked webhook equals an
  `@everyone` ping capability.
- **Scope limit (the good news):** the token reaches **only that channel**. It cannot read messages,
  list members, enumerate the guild, touch roles, or reach any other channel. It is not a guild-wide
  compromise.

**Rotation:** there is **no rotate-in-place / regenerate-token API**. To rotate you **delete the
webhook and create a new one**, yielding a new ID **and** token, i.e. a whole new URL. Do it in
Server Settings → Integrations → Webhooks, or `DELETE /webhooks/{webhook.id}` with a bot token holding
`MANAGE_WEBHOOKS`. The old URL is invalidated immediately. Note Discord's docs warn that repeated
attempts against an invalid/deleted webhook trigger temporary restrictions — make sure the bot stops
calling the dead URL.

**Hardening for a home-PC bot:**

- Secret in `.env` / `config.local.json`, **never** committed. Add to `.gitignore` **before** the first
  commit. Leaked webhook URLs are scraped from public repos and abused within hours.
- Never log the URL. Redact it in exception handlers — `httpx` puts the full URL into
  `RequestError`/`HTTPStatusError` strings, which then land in your log file.
- The project lives under a **OneDrive-synced path**. OneDrive-synced secrets are a real exposure
  surface (shared links, web access, sync to other machines). Keep the secret file outside the synced
  folder, or at minimum outside the repo.

### 2.6 RECOMMENDATION

**Use a real bot application with a bot token, and post with it. Do not build on an incoming webhook.**

Reasons, in order of weight:

1. **Moderation is now a first-class requirement.** The Take-Two §512(h) campaign makes AutoMod
   configuration, alert routing, and possibly timeouts part of the product. Those are all
   `/guilds/...` bot-token routes a webhook fundamentally cannot reach. You need the bot token anyway —
   so adding a webhook alongside it means two credentials, two failure modes, two rotation procedures,
   for zero gain.
2. **The opt-in role picker needs components.** A non-application-owned webhook **cannot send
   interactive components**. If you ever want a button/select role picker, the webhook path is a dead
   end. (Native Onboarding avoids this entirely — see §7 — but the option should stay open.)
3. **Crossposting needs a bot token** (§5), if Announcement channels are ever enabled.
4. **Impersonation risk is asymmetric.** In a community whose core safety promise is "we only carry
   first-party news, we never carry leaks", a spoofed official-looking post carrying a leak link is
   close to a worst-case outcome — both for member safety and for the server's exposure. A bot token is
   also a secret, but it lives in one place and is never handed out as a channel-scoped URL that tends
   to get copy-pasted into configs, screenshots, and CI logs.

**Cost of the bot-token choice:** create an application at `discord.com/developers/applications`,
invite it with a permissions integer, handle one token. You do **not** need the gateway and you do
**not** need any privileged intent for a post-only bot — plain HTTPS `POST` with
`Authorization: Bot <token>` is enough, so `httpx` alone suffices (§9).

**If you still prefer a webhook for v1** (legitimate: nothing to register, fastest path), the honest
split is **webhook for posting now, bot token added later for moderation**. That works. Just note you
will end up holding the bot token regardless.

---

## 3. RATE LIMITS — mechanics and correct backoff

Source: https://docs.discord.com/developers/topics/rate-limits [OFFICIAL]

### 3.1 The numbers

Official wording: *"All bots can make up to 50 requests per second to our API."*

Beyond the global limit, limits are **per-route + major-parameter buckets**. For message sends the
major parameter is `channel_id`, so `#news` and `#news-discussion` have independent buckets.

Discord explicitly warns limits **may change at any time** and **can differ per application**.
Therefore: **discover limits from headers, do not hard-code them.**

The often-quoted **30 requests / 60 s per webhook** and **5 messages / 5 s per channel** are
**[UNVERIFIED]** — I could not find either in the official reference. Multiple community sources agree
on both, and there are long-standing developer complaints that this behaviour "heavily deviates from
the documentation". Treat them as design guidance for pacing, not as constants to assert against.

### 3.2 Headers you MUST honour

| Header | Meaning | Action |
|---|---|---|
| `X-RateLimit-Limit` | total requests allowed in this bucket's window | informational |
| `X-RateLimit-Remaining` | requests left in this window | **if 0, do not send — wait** |
| `X-RateLimit-Reset` | epoch seconds when bucket resets | avoid; clock-skew sensitive |
| `X-RateLimit-Reset-After` | **seconds until reset (float)** | **prefer this** — relative, skew-proof |
| `X-RateLimit-Bucket` | opaque bucket ID | **use as the key of your limiter dict** |
| `Retry-After` | seconds to wait (429) | honour exactly |
| `X-RateLimit-Global` | present on 429 = you hit the **global** limit | pause **all** requests |
| `X-RateLimit-Scope` | `user` \| `global` \| `shared` (429 only) | see §3.4 |

429 JSON body:

```json
{ "message": "You are being rate limited.", "retry_after": 0.57, "global": false, "code": 20028 }
```

`retry_after` is a **float** of seconds. The `Retry-After` header may be rounded; **prefer the body's
`retry_after`** for sub-second precision.

Implementation notes:

- **Key the limiter on `X-RateLimit-Bucket`**, not on the URL. Discord shares buckets across routes;
  URL-keyed limiters both over- and under-throttle.
- **Use `X-RateLimit-Reset-After`, not `X-RateLimit-Reset`.** A home Windows PC's clock can drift;
  relative timing is immune.
- **Pre-emptively sleep when `Remaining` hits 0** rather than sending and eating the 429 — every 429
  counts toward the Cloudflare ban budget.

### 3.3 What happens on 429 abuse

1. **Ordinary 429** — HTTP 429 + `Retry-After`. Harmless if you back off, but **does** count as an
   invalid request.
2. **Cloudflare IP ban** — exceed the invalid-request budget and you are banned at the **Cloudflare
   edge**, before Discord's API. Symptom: HTML error pages / error `1015` instead of JSON, affecting
   the whole IP. On a home connection that means **Discord breaks for everyone on that network**,
   including the user's own Discord client. This is the actual danger for a home-PC bot.

### 3.4 The invalid-request budget — the one that will bite

> *"This limit is 10,000 per 10 minutes. An invalid request is one that results in 401, 403, or 429
> statuses."*
> *"429 errors returned with `X-RateLimit-Scope: shared` are not counted against you."*

Consequences:

- **A bad token is the classic way to get IP-banned.** Wrong bot token → every request 401. A retry
  loop with no backoff burns 10,000 requests in minutes and bans the household IP.
- **Mandatory rule: 401 and 403 are FATAL — never retried.** They mean the credential or permissions
  are wrong, which retrying cannot fix. Log, notify the operator, stop.
- 404 is **not** in the invalid list, but a deleted webhook returning 404 in a loop triggers Discord's
  separate anti-abuse restriction. Treat 404 as fatal too.
- Only **429, 5xx, and transport errors** are retryable.

### 3.5 Correct backoff strategy

```python
# 429   -> honour retry_after from the BODY (float seconds), then retry. Cap attempts (~5).
# 5xx   -> exponential backoff with FULL JITTER:
#          sleep = random.uniform(0, min(60, 1.0 * 2 ** attempt))
# 401/403/404 -> FATAL. Do not retry. Log + notify operator.
# X-RateLimit-Global present, or scope == "global"
#       -> pause EVERY outbound request, not just this bucket.
```

- **Full jitter, not plain exponential.** Costs nothing, protects you if two instances ever run.
- **Cap total attempts.** An unbounded retry loop is exactly how the 10,000/10min budget is burned.
- **Circuit-break.** After N consecutive failures, stop for a long window (e.g. 15 min) and raise a
  desktop notification. Never let a scheduled job spin.
- **A `User-Agent` header is mandatory.** Format: `DiscordBot ($url, $versionNumber)`. Requests without
  a valid User-Agent **may be blocked by Cloudflare**. `httpx` sends its own default UA, so override
  it explicitly:

```python
headers = {
    "Authorization": f"Bot {TOKEN}",
    "User-Agent": "DiscordBot (https://github.com/you/gta6-news-bot, 1.0.0)",
    "Content-Type": "application/json",
}
```

This is a genuine footgun: not optional, and the failure mode is an opaque Cloudflare block rather
than a clean API error.

---

## 4. EMBED LIMITS — each number verified individually

Source: https://docs.discord.com/developers/resources/message [OFFICIAL]

Official framing: *"To facilitate showing rich content, rich embeds do not follow the traditional
limits of message content. However, some limits are still in place to prevent excessively large
embeds."* And: *"Violating any of these constraints will result in a `Bad Request` response."*

| Field | Limit | Verified wording |
|---|---|---|
| `title` | **256** | "256 characters" |
| `description` | **4096** | "4096 characters" |
| `fields` | **25** | "Up to 25 field objects" |
| `field.name` | **256** | "256 characters" |
| `field.value` | **1024** | "1024 characters" |
| `footer.text` | **2048** | "2048 characters" |
| `author.name` | **256** | "256 characters" |
| **All embeds combined** | **6000** | across all `title`, `description`, `field.name`, `field.value`, `footer.text`, `author.name` fields of **all** embeds attached to the message |
| Embeds per message | **10** | "array of up to 10 embed objects" |

### 4.1 Message content limit — AMBIGUITY, READ THIS

This is the one number I could **not** resolve cleanly, and it is exactly the kind of thing that
becomes a production bug.

- **Execute Webhook** `content`: the official docs say **"the message contents (up to 2000
  characters)"**. Unambiguous. **2000.**
- **Create Message** (`POST /channels/{id}/messages`) `content`: on the current docs page this field
  rendered as **"4000 characters"** when I fetched it. I attempted three further fetches to quote the
  exact row verbatim and the page kept truncating before the Create Message params table, so I
  **could not confirm it verbatim**.
- Human users: **2000**, raised to **4000** with **full Nitro**; **Nitro Basic stays at 2000**
  [SUPPORT].

**Most likely explanation** (stated as a hypothesis, not a verified fact): the `content` field's
*schema* maximum was raised to 4000 to accommodate Nitro users, while the *effective* limit for any
given sender is still gated on that sender's premium status — and a bot is not a Nitro subscriber.

**Engineering decision: treat 2000 as the hard limit.** It is the officially documented number on the
route you are most likely to use, it is correct for every sender type, and the cost of being
conservative is zero for a digest that uses embeds anyway. If you ever need >2000 in `content`, test
it against your own server before relying on it.

### 4.2 Do embed limits differ for webhooks?

**No.** The embed limits are properties of the embed object, and both Execute Webhook and Create
Message document the same `embeds` cap of **10**. There is no separate webhook embed table and no
reduced webhook budget. The only route-specific difference I found is the `content` field wording
(§4.1) and the restricted `flags` set for webhooks (§2.1).

### 4.3 Markdown and formatting inside embeds

| Location | Markdown? | Masked links `[text](url)`? |
|---|---|---|
| `description` | **Yes** | **Yes** |
| `field.value` | **Yes** | **Yes** |
| `title` | No (plain text) | **No** |
| `author.name` | No | **No** |
| `footer.text` | No | **No** |
| `field.name` | No | **No** |

Confidence: **[UNVERIFIED by official docs]** — Discord's API reference does not spell out which embed
fields render markdown. This table is the consistent, long-standing consensus across library
documentation and guides, and matches observed behaviour. **Verify with one test post before building
the digest formatter around it.**

Practical rules for the digest:

- **Put every clickable headline in `description` or `field.value`**, formatted as
  `[Headline](https://example.com)`. This is the single most valuable formatting fact for this
  project — it lets one embed carry N clickable stories without N ugly bare URLs.
- **Masked links only render in bot/webhook/embed content**, not in text a human types. So this is a
  bot-only capability, which is fine here.
- Escape or strip `[`, `]`, `(`, `)` and backticks from **scraped headline text** before wrapping it in
  a masked link, or a headline containing a bracket will break the link syntax. Rockstar Newswire
  headlines and YouTube video titles absolutely do contain brackets and parentheses.
- `title` supports a separate `url` field — use `embed.url` to make the title clickable rather than
  trying to put markdown in `title` (which will render literally).
- **Masked links are also a phishing vector.** Since only bots can create them, and your bot is the
  only thing posting in `#news`, that risk is contained here. But it is a reason not to let any
  member-facing bot echo user-supplied text into an embed.

### 4.4 Colour, timestamp, thumbnail, image

| Field | Type | Behaviour |
|---|---|---|
| `color` | integer | **Decimal, not hex string.** `0xFCAF17` → `16560407`. Renders as the left-edge stripe. Use it to encode source: e.g. Rockstar green, Take-Two IR blue, YouTube red. |
| `timestamp` | **ISO 8601** string | Rendered bottom-right next to footer text, **localised to each viewer's timezone**. Set this to the *article's* publish time, not "now" — it is the cheapest correct-looking touch in the whole digest. |
| `thumbnail.url` | object with `url` | Small image, **top-right**. Best for a source logo. |
| `image.url` | object with `url` | Large image, **full-width at the bottom**. Best for the article hero image / YouTube thumbnail. |
| `footer.icon_url` | string | Small icon beside footer text. |
| `author.icon_url` | string | Small icon beside author name. |
| `url` | string | Makes `title` clickable. |
| `fields[].inline` | boolean | `true` packs up to **3 fields per row**. Non-inline fields are full-width. |

Notes:

- Image/thumbnail URLs must be **publicly reachable HTTPS**; Discord fetches and proxies them. A URL
  behind auth, hotlink protection, or a `robots`-hostile CDN silently renders as a broken/absent image.
  Rockstar's CDN and `i.ytimg.com` both work.
- `timestamp` must be ISO 8601. In Python: `datetime.now(timezone.utc).isoformat()`. A naive datetime
  will be rejected or misinterpreted — always attach tzinfo.
- None of `color`, `timestamp`, or any `*url` field counts toward the **6000** budget.
- Discord may not re-fetch a changed image at the same URL (proxy cache). Use cache-busting query
  params if an image needs to change.

### 4.5 Digest sizing — what actually fits

The realistic failure mode is the **6000** combined cap, not any individual field.

- One embed, 12 stories as masked links in `description` at ~250 chars each ≈ **3000 chars** →
  comfortably fits, with the whole 6000 in one embed if needed (description itself caps at 4096).
- One embed per story, 10 embeds, each with a 256-char title + 400-char description ≈ **6560** →
  **exceeds 6000 and 400s the whole request.**

**Therefore: prefer ONE embed with many masked-link lines over MANY embeds.** It is cheaper against the
6000 budget, renders more compactly, and avoids the 10-embed ceiling entirely.

Write a `fit_embeds(embeds) -> embeds` function that sums the six counted fields and truncates the
lowest-priority items until the total is under, say, **5500** (leave headroom). Assert on it in tests.

---

## 5. ANNOUNCEMENT CHANNELS AND CROSSPOSTING

### 5.1 How an Announcement channel works

- Channel type `GUILD_ANNOUNCEMENT` = **5**. Official description: *"a channel that users can follow
  and crosspost into their own server"* [OFFICIAL].
- Requires **Community enabled** on the server [SUPPORT].
- Messages posted there are ordinary messages until someone hits **Publish**. Publishing crossposts
  them into every server that **follows** the channel.
- Other servers follow via `POST /channels/{channel.id}/followers`, which requires
  **`MANAGE_WEBHOOKS` in the target channel** [OFFICIAL] — i.e. an admin of the *following* server
  sets it up. Following literally creates a **Channel Follower webhook** (webhook type **2**) in their
  channel.
- Edits propagate: editing the source message updates it in following servers. Deleting leaves an
  `[Original Message Deleted]` marker [SUPPORT].

### 5.2 The Publish / crosspost endpoint

```
POST /channels/{channel.id}/messages/{message.id}/crosspost
```

- Permissions: **`SEND_MESSAGES`** if the current user sent the message; **additionally
  `MANAGE_MESSAGES`** for messages sent by anyone else [OFFICIAL].
- Sets the **`CROSSPOSTED`** flag (`1 << 0`) on the source message. Messages arriving in follower
  servers carry **`IS_CROSSPOST`** (`1 << 1`) [OFFICIAL].
- **Rate limit: 10 publishes per hour** [SUPPORT]. Enforced identically in the UI and the API. I could
  **not** find this number in the official API reference — it is stated on Discord's Announcement
  Channel FAQ and corroborated by a Discord feature-request thread titled "Allow More than 10
  Announcements per Hour". **Treat as [SUPPORT], and handle the 429 rather than trusting the number.**
  I also could not determine with certainty whether the bucket is **per channel** or **per guild** —
  sources say both. Assume the stricter reading (per guild) if it matters.

### 5.3 Can a webhook message be crossposted?

**Yes — but not by the webhook.**

- The message itself is crosspostable regardless of who posted it.
- The crosspost call is on a **`/channels/...`** route. A webhook token authenticates **only**
  `/webhooks/{id}/{token}` routes, so it cannot make the call. Confirmed by the endpoint layout; also
  the long-standing consensus in the discord-api-docs issue tracker.
- A **bot** can crosspost a webhook's message, but because the bot did **not** send it, the bot needs
  **`MANAGE_MESSAGES`** in addition to `SEND_MESSAGES`.
- If the **bot** posts the message itself, it only needs `SEND_MESSAGES` — one fewer permission to
  grant. **Another argument for the bot-token approach (§2.6).**

To crosspost you need the message ID, which means `wait=true` on the webhook execute or reading the
`id` from the Create Message response.

### 5.4 Is it worth using for a single community server?

**No. Use a plain text channel.**

Crossposting exists so **other servers** can subscribe to your channel. Its entire value is
distribution to third-party guilds. For a brand-new single-community server:

- There are **zero followers**, so publishing does literally nothing.
- It adds a second API call per post, a new permission (`MANAGE_MESSAGES` if webhook-posted), a
  10/hour limit to respect, and a new failure mode.
- Announcement channels also require Community mode to be enabled.

**Does publishing trigger extra notifications for your own members?** For members of the **source**
server: **no** — the message already notified them when it was posted; publishing does not re-notify.
The notification effect is in **follower** servers, where the crossposted message arrives as a new
message. Confidence: **[SUPPORT / partially unverified]** — Discord's FAQ describes the follower-side
behaviour but does not explicitly state "publishing does not re-ping your own server". I could not
find an official sentence confirming the negative. It matches observed behaviour and the mechanics
(publishing does not create a new message locally), but **test it** before assuming, since a
double-ping would directly undermine the "we respect your notifications" promise.

**Recommendation:** make `#news` a **normal text channel** (type 0). Revisit Announcement channels only
if partner/affiliate RP servers ask to mirror your feed — that is the one scenario where it pays off,
and at that point it is a genuinely great feature.

---

## 6. MENTIONS SAFETY

Source: https://docs.discord.com/developers/resources/message [OFFICIAL]

### 6.1 The `allowed_mentions` object

```
parse?         array of allowed mention types
roles?         array of snowflakes   (max 100)
users?         array of snowflakes   (max 100)
replied_user?  boolean
```

`parse` accepts exactly three values [OFFICIAL]:

| Value | Controls |
|---|---|
| `"users"` | user mentions |
| `"roles"` | role mentions |
| `"everyone"` | `@everyone` **and** `@here` |

`replied_user` controls whether the author of a replied-to message is pinged (irrelevant here — the
bot never replies).

### 6.2 THE EXACT CONFIG: one role only, never @everyone

```json
{
  "content": "<@&123456789012345678> Rockstar just posted a new GTA 6 trailer.",
  "embeds": [ ... ],
  "allowed_mentions": {
    "parse": [],
    "roles": ["123456789012345678"],
    "users": [],
    "replied_user": false
  }
}
```

Why this is the right shape:

- **`"parse": []`** is the whitelist-from-nothing switch. Empty array = **suppress every category**:
  no `@everyone`, no `@here`, no roles, no users. Everything is off by default.
- **`"roles": ["<ROLE_ID>"]`** then re-enables **exactly that one role ID**. Any other role mentioned
  in the text renders as text and pings nobody.
- `"users": []` is explicit belt-and-braces.
- The role mention **must still literally appear in `content`** as `<@&ROLE_ID>` for a ping to happen.
  `allowed_mentions` only ever *permits*; it never *adds* a mention.
- Role mention syntax is `<@&ROLE_ID>` — note the **`&`**. `<@ID>` is a *user*. Getting this wrong is a
  common bug that produces a dead `@invalid-user` chip.

**Caveat on mixing `parse` and the arrays:** Discord's reference presents `roles`/`users` and the
corresponding `parse` values as mutually exclusive — do **not** put `"roles"` in `parse` *and* supply a
`roles` array; that combination is at best redundant and reportedly rejected. The config above sidesteps
the question entirely by keeping `parse` empty. **[Mutual exclusivity: not verbatim-verified — the
recommended config avoids depending on it.]**

Hard rule for the codebase: **build the payload through one function that always injects this
`allowed_mentions` block.** Never let a call site construct a raw payload. This is a one-line accident
otherwise.

### 6.3 Default behaviour if `allowed_mentions` is OMITTED — the accident case

Discord documents **two different defaults** [OFFICIAL], and the difference is the whole ballgame:

| Context | Default | Equivalent to |
|---|---|---|
| **Regular messages** (bot token, `POST /channels/{id}/messages`) | **ALL mention types are parsed** | `{"parse": ["users", "roles", "everyone"]}` |
| **Interactions and webhooks** | **only user mentions are parsed** | `{"parse": ["users"]}` |

Read that carefully, because it inverts the usual intuition:

- **Bot token + omitted `allowed_mentions` + the literal text `@everyone` in `content` = a real
  `@everyone` ping** (provided the bot has `MENTION_EVERYONE` in that channel). This is the accident.
  A scraped Rockstar headline or an article body containing the string `@everyone` — or `@here` — is
  enough. This is not hypothetical: news copy and social-media quotes contain `@` handles constantly.
- **Webhook + omitted `allowed_mentions` = safe by default.** Only user mentions parse; `@everyone`
  and role mentions are inert. So the webhook default is *safer* than the bot default.

This creates an important asymmetry for the recommendation in §2.6: **choosing the bot token means you
inherit the dangerous default**, so the "always inject `allowed_mentions`" rule is not optional
hygiene — it is a hard requirement. Enforce it in code and in a unit test that asserts the key is
present on every outbound payload.

Belt-and-braces beyond `allowed_mentions`:

- **Sanitise scraped text**: replace `@everyone` → `@​everyone` (zero-width space) and `@here`
  → `@​here` in all third-party-derived strings. Reads identically, cannot ping.
- **Put third-party text in embeds, not `content`.** Historically, mentions inside embed fields do not
  ping at all. Keep `content` reserved for your own controlled role-ping string and put every scraped
  headline in `description`/`field.value`. Two independent layers.
- **Deny `MENTION_EVERYONE` to the bot** in every channel except `#news` (§12).

### 6.4 Non-mentionable roles

Role settings have an "Allow anyone to @mention this role" toggle. Interaction with the API:

- If the role is **mentionable**, anyone with `SEND_MESSAGES` can ping it.
- If the role is **not mentionable**, a *bot* still needs **`MENTION_EVERYONE`** (`1 << 17`,
  value `131072`) in that channel to ping it. That permission is misleadingly named — it governs
  `@everyone`, `@here`, **and all roles**.
- `allowed_mentions` does not grant permission; it only filters. You need **both** the permission and
  the `allowed_mentions` entry.

**Recommended pattern — this is the good one:**

> Set `@GTA6 News` to **NOT mentionable**, and grant the **bot** `MENTION_EVERYONE` **only in
> `#news`**.

Result: the bot can ping the role in `#news`; **no member can ping it anywhere**, so the opt-in role
cannot be weaponised for spam pings in `#news-discussion`. The cost is that the bot technically also
gains `@everyone` capability in `#news` — mitigated by the always-injected `allowed_mentions`, and by
the fact that only the bot can post in `#news` at all.

### 6.5 Can webhooks mention roles at all?

**Yes.** A webhook can ping roles — including roles marked **not mentionable** — and `@everyone`,
provided the payload explicitly permits it via `allowed_mentions`. Because the webhook's default is
`{"parse":["users"]}`, a role ping from a webhook requires an **explicit**
`{"parse": [], "roles": ["..."]}` block. So the config in §6.2 is required for webhooks, not optional.

**Confidence note:** sources conflict on whether webhook `@everyone`/role mentions are
permission-gated. Some report Discord checks `MENTION_EVERYONE` on the webhook's channel; others report
webhooks have no permissions and can ping anything. I could **not** resolve this from official docs.
**Assume the pessimistic reading for security purposes: a leaked webhook URL can mass-ping**, and do
not rely on channel permission overwrites to prevent it (§2.5).

---

## 7. OPT-IN ROLE PATTERNS (2026)

### 7.1 The options

| Mechanism | Needs a bot token? | Maintenance | Notes |
|---|---|---|---|
| **Native Onboarding "Customize" questions** | **No — server config only** | **Zero** | Built into Discord. Answers map to `role_ids` and `channel_ids`. Members change answers any time in the **Channels & Roles** tab. |
| **Rules Screening** | No | Zero | Gates entry behind rules acceptance. **Not** a role picker — complementary, not an alternative. |
| **Carl-bot** | Third-party bot | Low | The reaction-role incumbent. Free tier covers reaction roles; Premium ~$7.99/mo, or a one-time $5–25 purchase. |
| **MEE6** | Third-party bot | Low | Premium ~$11.95/mo, and core features are paywalled more aggressively than competitors. Worst value here. |
| **Zira** | Third-party bot | Unknown | **Could not verify current status.** Searches returned nothing about Zira in 2026. Historically a reaction-role bot; treat as **possibly abandoned** and do not build on it without checking it is still online. |
| **Dyno** | Third-party bot | Low | Premium ~$4.99/mo single-server. Cheapest paid option. |
| **Custom bot, button/select component** | **Yes** | Medium | You own it. Needs an application, `MANAGE_ROLES`, an interaction endpoint or gateway connection, and it must be **running** for the buttons to work. |

### 7.2 Key mechanics of native Onboarding

Source: https://docs.discord.com/developers/resources/guild [OFFICIAL] + [SUPPORT]

- Object: `guild_id`, `prompts[]`, `default_channel_ids[]`, `enabled`, `mode`.
- Prompt types: **`MULTIPLE_CHOICE` (0)** and **`DROPDOWN` (1)**.
- Each prompt option carries `role_ids[]`, `channel_ids[]`, `emoji`, `title`, `description`. So one
  answer can grant a role **and** reveal channels.
- Modes: `ONBOARDING_DEFAULT` (0) counts only default channels toward constraints;
  `ONBOARDING_ADVANCED` (1) counts default channels **and** questions.
- Prompts can be marked **not** "Ask members before join" — those appear in the **Channels & Roles**
  tab instead, which is exactly where a notification opt-in belongs.
- Requires **Community enabled**, and **≥7 default channels of which ≥5 let `@everyone` send messages**
  [SUPPORT]. **This is a real blocker for a brand-new locked-down server** — see §7.4.
- If Rules Screening is enabled, members complete **Onboarding first, then Rules Screening**. Discord
  explicitly advises **not** to put rules inside onboarding questions.
- Configurable via API (`Modify Guild Onboarding`) or entirely in the UI. I could not fetch the
  endpoint's exact permission requirement — the guild docs page truncated before it. Assume
  `MANAGE_GUILD` + `MANAGE_ROLES`. **[UNVERIFIED]**

### 7.3 RECOMMENDATION

**Use native Onboarding, in `ONBOARDING_DEFAULT` mode, with one multi-select prompt: "Which alerts do
you want?" → `@GTA6 News`. Configure it in the UI, not the API.**

Reasons:

1. **Zero maintenance and zero uptime dependency.** This is decisive for a bot on a home PC. If the
   PC is off, a reaction-role or button-role bot silently stops assigning roles and new members are
   stuck — with native Onboarding, role assignment is Discord's own infrastructure and always works.
2. **No extra bot token, no extra third-party bot in a server that is under legal scrutiny.** Adding
   Carl-bot or MEE6 means another application with `MANAGE_ROLES` reading your server. In the current
   Take-Two subpoena climate, minimising third-party data processors in the server is a genuine
   (if modest) benefit.
3. **Reversible by the member without asking staff** — the Channels & Roles tab makes opt-out
   self-service, which is what keeps ping-fatigue complaints out of the mod queue.
4. Discord's own guidance matches: keep notification prompts **multi-select** (members can hold
   several), and keep them in a separate prompt from cosmetic/colour roles.

**Do NOT build the custom button role-picker for v1.** It is the most work, adds an uptime requirement
to something that must never break, and buys nothing that Onboarding does not already do. Revisit only
if you need conditional logic Onboarding cannot express.

### 7.4 The catch, and the fallback

The **≥7 default channels / ≥5 writable by `@everyone`** prerequisite conflicts with a deliberately
minimal, locked-down launch server. You have three ways out:

1. **Build the channel list to satisfy it** — the layout in §12 already has enough channels; make sure
   at least five are member-writable (`#general`, `#news-discussion`, `#rp-lfg`, `#clips-and-screens`,
   `#off-topic` gets you there). This is the recommended path and it is a fine server anyway.
2. **Fallback if you launch smaller than that:** a single pinned message in `#roles` with
   **Carl-bot** reaction roles (free tier). Lowest-effort third-party option, and the one with the
   longest track record for exactly this job.
3. **Interim manual:** for the first weeks, staff hand out the role on request. Fine at <100 members,
   does not scale.

---

## 8. AUTOMOD — capabilities, limits, blind spots

Source: https://docs.discord.com/developers/resources/auto-moderation [OFFICIAL],
https://discord.com/safety/auto-moderation-in-discord [OFFICIAL]

### 8.1 Rule model

```
id, guild_id, name, creator_id,
event_type, trigger_type, trigger_metadata, actions[],
enabled, exempt_roles[] (max 20), exempt_channels[] (max 50)
```

**Trigger types and per-guild caps** [OFFICIAL]:

| Trigger | Value | Max/guild | Purpose |
|---|---|---|---|
| `KEYWORD` | 1 | **6** | user-defined keywords + regex |
| `SPAM` | 3 | 1 | generic spam detection |
| `KEYWORD_PRESET` | 4 | 1 | Discord's built-in wordlists |
| `MENTION_SPAM` | 5 | 1 | excessive @user/@role mentions |
| `MEMBER_PROFILE` | 6 | 1 | scans profile content |

> **Discrepancy flagged:** Discord's own *safety marketing page* says "up to **3** custom filters with
> 1,000 keywords each". The *API reference* says `KEYWORD` max **6** per guild, and independent 2026
> sources agree on 6. **The API reference is authoritative and newer; the safety page appears stale.**
> Design for 6 but **verify in your server's UI before committing to a 6-rule layout** — if the UI
> caps you at 3, the merge plan is in §11.6.

**Event types** [OFFICIAL]:

- `MESSAGE_SEND` (1) — *"Applies when members send **or edit** messages"*
- `MEMBER_UPDATE` (2) — applies when members edit their profile

### 8.2 Trigger metadata limits [OFFICIAL]

| Field | Applies to | Limit |
|---|---|---|
| `keyword_filter` | KEYWORD, MEMBER_PROFILE | **1000** entries, **60** chars each |
| `regex_patterns` | KEYWORD, MEMBER_PROFILE | **10** patterns, **260** chars each |
| `allow_list` | KEYWORD | **100** entries, 60 chars each |
| `allow_list` | KEYWORD_PRESET | **1000** entries |
| `allow_list` | MEMBER_PROFILE | **100** entries |
| `presets` | KEYWORD_PRESET | Discord's internal wordsets |
| `mention_total_limit` | MENTION_SPAM | max **50** |
| `mention_raid_protection_enabled` | MENTION_SPAM | boolean |

### 8.3 Wildcard syntax [OFFICIAL]

Case-insensitive throughout.

| Pattern | Matches | Example |
|---|---|---|
| `cat` | **whole word only**, surrounded by whitespace | "cat" but not "cats" |
| `cat*` | **prefix** | "catch", "catapult" |
| `*cat` | **suffix** | "wildcat", "copycat" |
| `*cat*` | **anywhere / substring** | "location", "education" |

The `*cat*` form is what you need for domains — `*mega.nz*` matches `https://mega.nz/file/abc`.

### 8.4 Regex support [OFFICIAL]

- **Rust regex only.** *"Only Rust flavored regex is currently supported, which can be tested in online
  editors such as Rustexp."*
- **No lookahead, no lookbehind, no backreferences.** Discord's stated reason: those require a
  backtracking engine, which enables regex denial-of-service. Write patterns that **match left to
  right**.
- **260 chars per pattern, 10 patterns per rule.** With 6 KEYWORD rules that is **60 regex patterns**
  total — plenty.
- Inline flags like `(?i)` work (Rust `regex` crate syntax). Character classes, alternation,
  quantifiers, `\b`, `\d`, `\w`, `\s`, non-capturing groups all fine.

### 8.5 Actions [OFFICIAL]

| Action | Value | Requires | Effect |
|---|---|---|---|
| `BLOCK_MESSAGE` | 1 | — | message never posts; optional `custom_message` (**150** chars) shown to the author |
| `SEND_ALERT_MESSAGE` | 2 | — | posts the flagged content to `channel_id` |
| `TIMEOUT` | 3 | `MODERATE_MEMBERS` | mutes the member, max **2,419,200 s** (4 weeks) |
| `BLOCK_MEMBER_INTERACTION` | 4 | — | restricts the member's text/voice access |

**`TIMEOUT` only works with `KEYWORD` and `MENTION_SPAM` triggers.** You can attach multiple actions to
one rule — block **and** alert **and** timeout simultaneously, which is the configuration you want for
the hard leak rules.

### 8.6 Can AutoMod block by DOMAIN or URL pattern?

**Yes — but only as text matching.** There is no first-class "URL/domain" rule type. You block domains
by treating them as substrings, either as `*domain.tld*` wildcards in `keyword_filter` or as a regex.
Both work well.

Discord separately ships a **preset "harmful links"** filter using its own list of known scam/malware
domains — useful, but it is Discord's list, not yours, and it will **not** contain file hosts or leak
mirrors. You must supply those yourself.

**Two strategies:**

1. **Denylist specific hosts** (§11.1). Precise, low false-positive, but you are always one new host
   behind. `gofile.io` gets blocked, attacker moves to `qiwi.gg`.
2. **Allowlist-only links** — regex-match *every* URL and put permitted domains in `allow_list`.
   Maximum strictness. **But there is a known allowlist-wildcard bypass**
   (discord-api-docs issue #7356): allowlist entries are keyword-style, so a URL that merely *contains*
   an allowed string can slip through — e.g. `https://evil.example/?ref=youtube.com` can satisfy an
   `*youtube.com*` allow entry. **Anchor allowlist entries as tightly as possible and do not treat
   allowlist-only mode as airtight.**

**Recommendation: run both.** Allowlist-only in `#news-discussion` and `#clips-and-screens` (the
high-risk channels), plus the explicit host denylist server-wide as defence in depth.

### 8.7 API vs UI

**Both.** Full CRUD over the API with a bot token:

```
GET    /guilds/{guild.id}/auto-moderation/rules
GET    /guilds/{guild.id}/auto-moderation/rules/{rule.id}
POST   /guilds/{guild.id}/auto-moderation/rules
PATCH  /guilds/{guild.id}/auto-moderation/rules/{rule.id}
DELETE /guilds/{guild.id}/auto-moderation/rules/{rule.id}
```

All require **`MANAGE_GUILD`**, plus the action-specific permission (`MODERATE_MEMBERS` for timeouts).
POST/PATCH/DELETE accept **`X-Audit-Log-Reason`** — always set it, so the audit log records *why* a rule
changed. All mutations fire gateway events.

**This is the strongest argument for keeping rules in version control.** Store the rule set as JSON in
the repo and have a small script PUT it. You get diffable, reviewable, restorable moderation config
instead of clicks in a UI that only the owner can audit — which matters a great deal if you ever have
to demonstrate good-faith enforcement.

### 8.8 BLIND SPOTS — where AutoMod will NOT save you

This is the most important subsection for this project. **AutoMod is a text filter. The threat is
video files.**

| Blind spot | Detail | Confidence |
|---|---|---|
| **Attachments / uploaded files** | AutoMod **cannot scan images, videos, or attachments**. A member uploading `gta6_leak.mp4` directly is **completely invisible** to AutoMod. | [OFFICIAL — safety page] |
| **Attachment filenames** | Whether the *filename* is matched as text is **unclear**; I found no official statement. **Assume it is NOT scanned.** | **[UNVERIFIED]** |
| **Image/video content** | No OCR, no perceptual hashing, no frame analysis. A screenshot of a leak, or a leak clip with a URL burned into the video, passes. | [OFFICIAL] |
| **Text inside embeds from other bots** | Bots and webhooks are **exempt** (below). | [SUPPORT] |
| **DMs** | AutoMod is guild-scoped. Members trading leaks by DM are untouchable. Server-wide DM restrictions and the "trade in DMs" keyword rule (§11.3) are your only levers. | [OFFICIAL by design] |
| **Edited messages** | **Covered.** `MESSAGE_SEND` is documented as applying when members *"send or edit messages"*. Post-clean, edit-to-dirty does **not** work. | [OFFICIAL] |
| **Voice channels** | No audio scanning. Voice channel *names* / status text are not covered by the message rules. | [OFFICIAL by design] |
| **Admins and moderators** | Users with **Administrator** or **Manage Server** are **always exempt**, automatically and unavoidably. | [SUPPORT] |
| **Bots and webhooks** | **Exempt by design** and it **cannot be turned on** (see discord-api-docs discussion #6330). | [SUPPORT] |
| **Custom emoji / sticker names, thread titles, forum post titles** | Coverage unclear. Threads, text-in-voice and forum channels *are* scanned for messages. | partially [OFFICIAL] |
| **Obfuscation** | `m e g a . n z`, `mega(dot)nz`, Cyrillic homoglyphs, zero-width joiners. Regex helps (§11.4) but this is an arms race you do not win outright. | — |

**Two consequences you must design around:**

1. **The bot/webhook exemption cuts both ways.** Your news bot's posts will never be blocked by your own
   AutoMod rules — convenient, no allowlisting needed. But it also means **any** bot in the server can
   post a leak link with impunity. **Vet every third-party bot you add**, and prefer adding none (§7.3).
2. **Attachments are the actual attack vector and AutoMod cannot see them.** Given the Take-Two
   §512(h) campaign — where a subpoena reportedly reached a server that hosted **no leaked clips**,
   merely discussion — the only reliable controls for media are **structural, not automated**:
   - **Deny `ATTACH_FILES` and `EMBED_LINKS` to `@everyone` in every channel by default**, granting them
     back only in one moderated `#clips-and-screens` channel.
   - Keep that channel on **slow mode** and staffed, or make it staff-post-only at launch.
   - Human moderators remain mandatory. Budget for them.

---

## 9. PYTHON LIBRARY CHOICE

Versions verified on PyPI, 2026-08-25.

| Library | Latest | Released | Python support | Status |
|---|---|---|---|---|
| **discord.py** | **2.7.1** | **2026-03-03** | `>=3.8`; classifiers list **3.8–3.12** | Active, Production/Stable. **Classifiers do not list 3.13/3.14** — see below. |
| **py-cord** | **2.8.1** | **2026-07-25** | **3.10–3.14** | Active, Production/Stable, 4 maintainers. |
| **disnake** | **2.12.1** | **2026-07-22** | `>=3.10`; classifiers **3.10–3.14** | Active, Production/Stable. |
| **hikari** | **2.6.0** | **2026-08-19** | **3.10–3.14** (`<3.15`) | **Most recently released.** Static-typed microframework; `GatewayBot` + `RESTBot`. |
| **nextcord** | 3.2.0 | **could not date reliably** | 3.0.0 required Python **3.12+** | **Slowing.** GitHub releases page did not yield reliable dates; release cadence appears to have dropped. Treat with caution. |

**Is any abandoned?** No — **none of the five is abandoned.** discord.py's 2022 discontinuation was
**reversed**; it is maintained and shipped in March 2026. The one to be wary of is **nextcord**
(cadence slowing, dates unverifiable from the releases page). **Zira** (a bot, not a library) is the
only thing here I would call likely-dead (§7.1).

**Python 3.12/3.13 note:** discord.py's classifiers stop at **3.12**. The user is on **3.12**, so this
is a non-issue today. But if you upgrade to 3.13+, discord.py is the one library here without a
declared classifier for it — py-cord, disnake and hikari all declare up to **3.14**. Worth knowing
before a future interpreter bump.

### 9.1 RECOMMENDATION

**Phase 1 (now) — plain `httpx`. Add no Discord library at all.**

The whole job is:

```python
POST https://discord.com/api/v10/channels/{channel_id}/messages
Authorization: Bot <token>
User-Agent: DiscordBot (<url>, <version>)
{ "content": ..., "embeds": [...], "allowed_mentions": {...} }
```

That is one function. `httpx` is already installed. A library would add a dependency, a gateway
connection you do not need, an event loop lifecycle, and an abstraction over the exact rate-limit
headers you want to handle explicitly. For **1 digest/day + a few alerts**, direct REST is simpler,
easier to debug, and has a smaller failure surface. **Bonus: you never connect to the gateway, so you
never touch intents, so the privileged-intent rules are irrelevant to you.**

**Phase 2 — AutoMod config: still plain `httpx`.** The AutoMod endpoints are five plain REST calls
(§8.7). Keep the rules as JSON in the repo and PUT them with a script. No library needed.

**Phase 3 — only if you add a button role picker: `discord.py` or `py-cord`.**

That is the one feature that genuinely needs a library, because handling component interactions means
either a persistent gateway connection or a public HTTPS interaction endpoint with Ed25519 signature
verification — neither of which you want to hand-roll. At that point:

- **`discord.py`** — largest ecosystem, most documentation and Stack Overflow answers, original
  upstream. Best default.
- **`py-cord`** — a fine alternative with broader declared Python support (3.14) and a slightly
  friendlier slash-command API.
- **`hikari`** — the most interesting technically (static typing, `RESTBot` mode fits interaction
  webhooks neatly, most recent release) but the smallest community. Choose only if you value the type
  safety more than the answer-availability.

**But per §7.3, you should not need Phase 3 at all** — native Onboarding replaces the button picker and
requires no code and no uptime.

---

## 10. DISCORD POLICY

### 10.1 Automated posting and self-bots

- **Bots and webhooks posting automatically is fully sanctioned** — that is what the API exists for.
  No approval needed to run a bot in your own server.
- **Self-bots (automating a normal user account) remain banned.** Discord explicitly prohibited them in
  2017 and the prohibition stands in 2026. Enforcement: warnings escalating to **permanent account
  termination**. Support article: *Automated User Accounts (Self-Bots)*.
- Practical read for 2026: no amount of delay-injection, human-like typing, captcha-solving or token
  rotation makes user-account automation compliant, and nothing about it is undetectable. **Never
  authenticate with a user token.** Use `Authorization: Bot <token>` only.
- Do not circumvent rate limits. Ignoring `Retry-After` in a loop is both a ToS problem and the fast
  route to a Cloudflare IP ban (§3.4).

I attempted to fetch the Developer ToS directly; `docs.discord.com/developers/policies-and-agreements/developer-terms-of-service`
**307-redirects to `support-dev.discord.com`, which returns 403 to automated fetchers.** The
self-bot facts above are therefore **[SUPPORT]** via search snippets. **Read the Developer ToS and
Developer Policy in a browser before launch** — they are short and they are the governing documents.

### 10.2 Does a webhook-based news bot need to be verified?

**No.**

- **Verification is triggered at 100 servers** [SUPPORT]. A single-community bot is nowhere near it.
- **A webhook needs no application at all**, so verification cannot apply.
- **2026 change worth knowing:** the **privileged intents** threshold moved from "100 servers" to
  **">10,000 unique users who can see your app"**. These are now **two independent thresholds** —
  verification is still 100 servers; privileged intents is the 10,000-user rule. A bot can need one
  without the other. **Irrelevant to you either way**, because a post-only REST bot uses **no intents**
  (intents only apply to gateway connections).

### 10.3 Posting third-party news content

There is no Discord rule against a bot posting news links. But keep it defensible:

- **Post headline + link + short excerpt, never the full article body.** Full-text reproduction is a
  copyright problem with the publisher, independent of Discord's rules. Headline + 1–2 sentences +
  attribution + link is standard practice and the safe shape.
- **Attribute the source** in `author.name` or `footer.text` on every embed. Cheap, and it makes the
  digest look professional.
- **Respect `robots.txt` / ToS of the sites you fetch.** This is a scraping question, not a Discord
  question, but it is the same risk register.
- **Images:** hotlinking a publisher's image via `embed.image.url` means Discord fetches and proxies
  it. Prefer official press assets, Rockstar's own CDN, and YouTube thumbnails (`i.ytimg.com`), which
  are intended for embedding.
- **Because the sources are first-party only** (Rockstar Newswire, Rockstar YouTube, Take-Two IR), you
  are in the best possible position: you are redistributing the rights-holder's own announcements,
  which is exactly what they want amplified. **Keep it that way — the moment the bot ingests
  aggregators or leak accounts, the whole risk profile changes.**

### 10.4 Copyrighted / leaked material — the rules that actually matter here

- **Community Guidelines** prohibit distributing or providing access to **stolen goods, pirated
  content, cracked or hacked material**.
- **Unauthorized Copyright Access Policy**: *"This policy forbids any activity that gives anyone
  unauthorized access to copyrighted material, including through live-streams, and prohibits
  coordinating such access."* Note **"coordinating"** — organising or signposting access is itself a
  violation, even without hosting the file. **"DM me for the link" is a violation.** Rule #11.3 exists
  for exactly this.
- Discord's response to the Pentagon leaks establishes the pattern: Trust & Safety **removes content
  and bans users involved in original distribution**.

### 10.5 DMCA and the repeat-infringer process

- Notices go to **copyright@discord.com**, subject line "DMCA Takedown Request", or by post to
  Discord, Attn: DMCA Takedown Request, 444 De Haro Street #200, San Francisco, CA 94107.
- Typical processing **24–48 hours**; valid requests get content removed/disabled and the account
  holder notified [third-party estimate, not an SLA].
- **Repeat-infringer policy:** Discord has *"adopted a policy of terminating, in appropriate
  circumstances and at the Company's sole discretion, users who are deemed to be repeat infringers."*
- **Servers can be banned outright** where they exist primarily to share infringing content, have
  multiple DMCA violations, or refuse to comply.
- Counter-notices exist; content may be restored in **10–14 business days** absent a court action.

### 10.6 The §512(h) subpoena context — why this is not theoretical

Verified 2026-08-25:

- Take-Two filed DMCA **§512(h)** subpoena applications in the **US District Court for the Southern
  District of New York on 2026-08-20**, granted **2026-08-21**, against **Microsoft and Discord**.
  Compliance deadline reported as **2026-09-04**.
- **§512(h) lets a copyright owner compel a service provider to identify an alleged infringer
  WITHOUT first filing a lawsuit.** No judge weighs the merits first. This is a low bar.
- Reported scope: **all identifying information for every account that communicated in named servers
  since 2026-06-01** — account data, registration and last-login IPs, phone numbers, linked Google/Xbox
  connections, and (from Microsoft) MachineGuid/MSA device identifiers and OneDrive contents.
- Named servers reportedly include **Ødyssey.gg** (`1517326120867991592`), **"! Odyssey"**
  (`1127436882800816149`), and **DarkViperAU** (`268280696601051136`). Take-Two has also reportedly
  extended the campaign with subpoenas to **X and YouTube**.
- **The DarkViperAU server is the load-bearing detail.** It is a commentator's community, not a leak
  hub. Its inclusion demonstrates that **communicating in a server connected to the leak discourse can
  be enough to have your identifying data demanded — hosting leaked media is not required.**

**Design consequences, stated plainly:**

1. **Prevention beats moderation.** A deleted message still existed, and server logs, audit logs and
   Discord's own retained data are what a subpoena reaches. `BLOCK_MESSAGE` — which prevents the
   message from ever being created — is materially better than deleting it afterwards. **Prefer
   blocking to logging.**
2. **Do not build a leak-content archive for moderation purposes.** A mod-log channel full of
   quoted leak URLs, or a database of blocked payloads, is itself a liability and is discoverable.
   Use `SEND_ALERT_MESSAGE` for *signal* ("rule X fired, user Y"), and keep retention short.
3. **The `#news`-is-first-party-only rule is the core safety feature of the product**, not an editorial
   preference. It is what keeps the server structurally uninteresting to a subpoena.
4. **Rules must be explicit and enforced visibly.** A documented, version-controlled AutoMod config
   (§8.7) plus a written rule against leaked media is the evidence of good-faith enforcement.
5. **This is not legal advice.** If the community grows or receives any contact from Take-Two,
   Rockstar, or Discord Trust & Safety, get a lawyer. See `research/legal-risk.md`.

---

## 11. COPY-PASTEABLE AUTOMOD RULES

Budget: **6 `KEYWORD` rules** + 1 each of SPAM / KEYWORD_PRESET / MENTION_SPAM / MEMBER_PROFILE.
The plan below uses **5 of the 6** KEYWORD slots, leaving one spare for incident response.

**Tiering principle:** file hosts and explicit trade solicitation are **hard-blocked**; ambiguous
leak *discussion* is **alert-only**. Blocking discussion outright drives it into DMs where you have
zero visibility, and generates false positives on legitimate news talk ("Rockstar addressed the
leak"). Block the *vector*, watch the *chatter*.

Every rule below should set:

```json
"exempt_roles":    ["<MOD_ROLE_ID>", "<ADMIN_ROLE_ID>"],
"exempt_channels": []
```

Leave `exempt_channels` **empty** — there is no channel where leak links are acceptable.
(Admins/Manage-Server holders are exempt automatically and unavoidably, §8.8.)

---

### 11.1 Rule 1 — "LEAK BLOCK: file hosts" (KEYWORD, hard block)

Paste into **Custom Keyword** → keywords, one per line. All use `*...*` (substring) form.

```
*mega.nz*
*mega.io*
*mega.co.nz*
*mediafire.com*
*gofile.io*
*pixeldrain.com*
*pixeldrain.net*
*catbox.moe*
*litterbox.catbox.moe*
*anonfiles.com*
*krakenfiles.com*
*1fichier.com*
*bunkr.si*
*bunkr.ru*
*bunkrr.su*
*cyberdrop.me*
*cyberfile.me*
*qiwi.gg*
*buzzheavier.com*
*send.now*
*sendspace.com*
*dropmefiles.com*
*wetransfer.com*
*we.tl*
*file.io*
*filebin.net*
*uploadhaven.com*
*workupload.com*
*zippyshare.day*
*rapidgator.net*
*turbobit.net*
*nitroflare.com*
*doods.pro*
*streamtape.com*
*mixdrop.co*
*terabox.com*
*teraboxapp.com*
*4funbox.com*
*gdriveplayer*
*anonymfile.com*
*pomf.lain.la*
*uguu.se*
*tmpfiles.org*
*0x0.st*
*transfer.sh*
*ufile.io*
*fileditch.com*
*litter.catbox.moe*
```

**Actions:** `BLOCK_MESSAGE` + `SEND_ALERT_MESSAGE` (→ `#mod-alerts`) + `TIMEOUT` **10 minutes**
(`600` s).

`custom_message` (must be ≤ **150** chars):

```
Blocked: file-host links are not allowed here. Sharing leaked GTA 6 media puts you and this server at legal risk. See #rules.
```

(That string is 127 chars — verified under the limit.)

> **Note:** `wetransfer.com`, `terabox`, `sendspace` and `we.tl` have legitimate uses. In a GTA news
> server the legitimate need is ~zero and the downside is high, so blocking is correct. Move any that
> generate real complaints into Rule 6 (alert-only) instead of deleting them.

---

### 11.2 Rule 2 — "LEAK BLOCK: video mirrors & reuploads" (KEYWORD, hard block)

```
*streamable.com*
*streamja.com*
*streamff.com*
*dubz.co*
*dubz.link*
*dubz.tv*
*gfycat.com*
*imgur.com/a/*
*justpaste.it*
*rentry.co*
*rentry.org*
*pastebin.com*
*paste.ee*
*controlc.com*
*telegra.ph*
*t.me/+*
*t.me/joinchat*
*bit.ly*
*tinyurl.com*
*is.gd*
*cutt.ly*
*rb.gy*
*shorturl.at*
*t.ly*
*rebrand.ly*
*shrtco.de*
*ouo.io*
*linkvertise.com*
*mboost.me*
*loot-link.com*
*lootlabs.gg*
*adfoc.us*
*ay.live*
*bc.vc*
```

**Actions:** `BLOCK_MESSAGE` + `SEND_ALERT_MESSAGE`.
No timeout — URL shorteners get used innocently, so a block plus a nudge is proportionate.

`custom_message`:

```
Blocked: link shorteners and clip mirrors are not allowed - they hide the destination. Post the original source link instead.
```

**Rationale:** shorteners and paste sites are the standard indirection layer for leak distribution —
they defeat any domain denylist by hiding the destination. Blocking the *indirection* is more durable
than chasing hosts. Note `*imgur.com/a/*` targets **albums** (a common multi-frame leak vector) while
leaving single-image `i.imgur.com` links usable.

---

### 11.3 Rule 3 — "LEAK BLOCK: trade solicitation" (KEYWORD, hard block)

This is the rule that maps directly onto Discord's *"prohibits coordinating such access"* language
(§10.4). Requesting or offering leaked media is itself the violation.

```
*dm for the link*
*dm for link*
*dm for links*
*dm me for the link*
*dm me for link*
*dm me the vid*
*dm me the video*
*dm me the clip*
*dm me the leak*
*dm for the vid*
*dm for the clip*
*dm for leak*
*dm for the leak*
*dms open for*
*check my dms*
*i have the leak*
*i got the leak*
*i have the clip*
*i got the clip*
*i have the footage*
*got the full video*
*got the full vid*
*who wants the link*
*who wants the clip*
*who wants the vid*
*link in bio*
*link in my bio*
*link in dm*
*link in dms*
*link in pfp*
*trade for the*
*selling the leak*
*selling leaks*
*paying for the leak*
*where can i watch the leak*
*where to watch the leak*
*someone send the leak*
*send me the leak*
*send the leak*
*send me the clip*
*anyone got the leak*
*anyone got the clip*
*anyone have the leak*
*drop the link*
*drop the clip*
*drop the vid*
```

**Actions:** `BLOCK_MESSAGE` + `SEND_ALERT_MESSAGE` + `TIMEOUT` **1 hour** (`3600` s).

`custom_message`:

```
Blocked: asking for or offering leaked GTA 6 media is not allowed, including via DM. This rule protects you legally. See #rules.
```

---

### 11.4 Rule 4 — "LEAK BLOCK: regex, obfuscated hosts" (KEYWORD, hard block)

**Rust regex. No lookahead/lookbehind/backreferences. 260 chars max per pattern, 10 patterns max.**
All patterns below are within limits.

**Pattern 1 — file hosts with obfuscated dots** (`mega(dot)nz`, `mega . nz`, `mega,nz`):

```
(?i)(mega|mediafire|gofile|pixeldrain|catbox|bunkr|cyberdrop|streamable|anonfiles|krakenfiles|qiwi|buzzheavier)\s*[\(\[\{<]?\s*(dot|d0t|\.|,|·|:)\s*[\)\]\}>]?\s*(nz|io|com|moe|me|si|su|gg|to|net|org|pro)
```

**Pattern 2 — spaced-out host names** (`m e g a . n z`):

```
(?i)m\W?e\W?g\W?a\W?\W?n\W?z|m\W?e\W?d\W?i\W?a\W?f\W?i\W?r\W?e|g\W?o\W?f\W?i\W?l\W?e|p\W?i\W?x\W?e\W?l\W?d\W?r\W?a\W?i\W?n
```

**Pattern 3 — leak-build / version signatures:**

```
(?i)(gta|grand\s*theft)\W*(6|vi)\W*(leak|leaked|build|dev\s*build|internal|alpha|beta|playtest|prerelease|pre-release|unreleased|nda)
```

**Pattern 4 — filename patterns for leaked media:**

```
(?i)\b(gta|gtavi|gta6)[\w\-\.]{0,20}\.(mp4|mkv|mov|avi|webm|zip|rar|7z|part\d{1,3})\b
```

**Pattern 5 — "watch before it's deleted" urgency framing:**

```
(?i)(before|b4)\s*(it|this|they)?\s*(gets?|is|get)?\s*(deleted|taken\s*down|removed|nuked|patched|dmca)
```

**Pattern 6 — magnet / torrent links:**

```
(?i)(magnet:\?xt=urn:btih:|\.torrent\b|1337x|thepiratebay|rarbg|nyaa\.si)
```

**Actions:** `BLOCK_MESSAGE` + `SEND_ALERT_MESSAGE` + `TIMEOUT` **10 minutes**.

`custom_message`:

```
Blocked by the leaked-media filter. If you think this was a mistake, contact a moderator - do not repost it.
```

> **Test every pattern at https://rustexp.lpil.uk/ before saving.** Discord validates syntax on save
> but will happily accept a pattern that matches far more than you intended. Pattern 2 in particular
> is deliberately aggressive (`\W?` between letters) and **will** false-positive on some ordinary text
> — start it as **alert-only**, watch `#mod-alerts` for a week, then promote to block if it is clean.

---

### 11.5 Rule 5 — "LEAK WATCH: chatter" (KEYWORD, ALERT-ONLY, no block)

**Deliberately does not block.** Its job is to tell moderators where attention is needed.

```
*gta 6 leak*
*gta6 leak*
*gta vi leak*
*gtavi leak*
*leaked gameplay*
*leaked footage*
*leaked build*
*leaked trailer*
*leaked map*
*early build*
*dev build*
*playtest build*
*internal build*
*source code leak*
*unreleased footage*
*nda footage*
*cyberleek*
*full leak*
*leak dump*
*megathread leak*
*mirror link*
*reupload*
*reuploaded*
*new leak just dropped*
*leak just dropped*
*insider footage*
```

**Actions:** `SEND_ALERT_MESSAGE` → `#mod-alerts` **only**. No block, no timeout.

**Why alert-only:** "Rockstar responded to the leaked footage" is a legitimate, newsworthy sentence
your members will absolutely write. Blocking it makes the server unusable and pushes real discussion
into DMs. Watching it tells you when a leak wave is hitting so a human can step in.

---

### 11.6 If your server only allows 3 custom keyword rules

Per §8.1 there is a documented discrepancy (API says 6, Discord's safety page says 3). If the UI caps
you at 3, merge as follows — the entry counts are nowhere near the **1000/rule** limit:

| Merged rule | Contents | Actions |
|---|---|---|
| **1. LEAK BLOCK — links** | 11.1 + 11.2 keyword lists combined (~80 entries) | block + alert + 10 min timeout |
| **2. LEAK BLOCK — intent & patterns** | 11.3 keywords + 11.4 regex patterns | block + alert + 1 h timeout |
| **3. LEAK WATCH** | 11.5 keywords | alert only |

---

### 11.7 The four non-KEYWORD rules (1 each, all free wins)

| Rule | Config | Actions |
|---|---|---|
| **`KEYWORD_PRESET`** | Enable **all three** presets: profanity, sexual content, slurs. Plus Discord's **harmful-links** preset if surfaced separately in the UI. Use `allow_list` for the handful of gaming terms it over-flags. | block + alert |
| **`MENTION_SPAM`** | `mention_total_limit: 5`, `mention_raid_protection_enabled: true` | block + alert + 10 min timeout |
| **`SPAM`** | Enable it. Zero config, catches widely-reported spam text. | block |
| **`MEMBER_PROFILE`** | `keyword_filter` = a trimmed copy of 11.1 + 11.3 (catches "DM me for GTA6 leak" in usernames/bios) | `BLOCK_MEMBER_INTERACTION` (type 4) + alert |

`MENTION_SPAM` at **5** is right for a news server: no legitimate member needs to ping six people at
once, and mass-mention is the standard payload of a compromised-account raid.

The **`MEMBER_PROFILE`** rule is genuinely valuable and widely skipped — leak sellers routinely
advertise in their **display name** or **bio** rather than in messages, which sidesteps every
message-based rule you just built.

---

### 11.8 Optional: allowlist-only links in the two risk channels

For `#news-discussion` and `#clips-and-screens`, consider the strict inverse: block **all** URLs, allow
a short list.

Use the spare 6th KEYWORD rule. Regex to match any URL:

```
(?i)\b(https?://|www\.)\S+
```

`allow_list` (remember: **100 entries max, 60 chars each**):

```
*rockstargames.com*
*rockstarnewswire.com*
*take2games.com*
*youtube.com/watch*
*youtu.be/*
*x.com/RockstarGames*
*twitter.com/RockstarGames*
*ign.com*
*gamespot.com*
*eurogamer.net*
*pcgamer.com*
*videogameschronicle.com*
*discord.com/channels*
*tenor.com*
*i.ytimg.com*
*i.imgur.com*
```

Set `exempt_channels` to **every channel except** those two — AutoMod has no channel-include list, only
`exempt_channels` (max **50**), so you enumerate the exemptions. This inverted configuration is fiddly
but it is the only way to scope a rule to specific channels.

**Known weakness (§8.6):** the allowlist-wildcard bypass — `https://evil.example/?x=youtube.com`
can satisfy `*youtube.com*`. Keep entries as anchored as possible and do **not** treat this as airtight.

---

### 11.9 What AutoMod will NOT catch — where humans are still required

Restating §8.8 as an operational checklist, because this is what the mod team must actually own:

1. **Direct file uploads.** `gta6_leak.mp4` attached to an empty message is **invisible** to AutoMod.
   → **Deny `ATTACH_FILES` to `@everyone` server-wide** (§12). This is the single most important
   control in this whole document, and it is a permission, not a rule.
2. **Screenshots and video with burned-in URLs.** No OCR. A human must see it.
3. **DMs.** Entirely out of scope. Rule 11.3 discourages solicitation *in channel*; it cannot follow
   members into DMs. Consider server-level DM restrictions for new members.
4. **New hosts.** Every denylist is one host behind. Review `#mod-alerts` weekly and add new domains.
5. **Novel obfuscation.** Homoglyphs (Cyrillic `а`), zero-width joiners, emoji-substituted letters,
   text-in-image links.
6. **Admins, moderators, bots and webhooks are exempt** and cannot be un-exempted. **Vet every bot you
   add and keep the mod team small.**
7. **Voice.** No audio scanning; leaks get described and coordinated in VC.
8. **Judgement calls.** "Is this official concept art or a leaked asset?" is not a regex.

---

## 12. RECOMMENDED CHANNEL & PERMISSION LAYOUT

### 12.1 The layout

```
INFORMATION
  #welcome              read-only. Onboarding default channel.
  #rules                read-only. MUST state the leaked-media rule explicitly.
  #roles                read-only. Points at Channels & Roles tab (or Carl-bot fallback).

NEWS
  #news                 BOT-ONLY. Locked. Digest 18:00 + instant alerts. Type 0 (text).
  #news-discussion      Members. Slow mode 30s. NO attach, NO embed links.
  #rumours-and-leaks    *** DO NOT CREATE THIS CHANNEL. See 12.5. ***

COMMUNITY
  #general              Members. Onboarding-writable.
  #rp-lfg               Members. Onboarding-writable.
  #clips-and-screens    Members. Slow mode 60s. THE ONLY channel with ATTACH_FILES.
  #off-topic            Members. Onboarding-writable.

STAFF (private)
  #mod-alerts           AutoMod SEND_ALERT_MESSAGE target. Staff only.
  #mod-chat             Staff only.
  #bot-logs             Bot errors / heartbeat. Staff only.
```

That is **10 member-visible channels**, of which **5 are `@everyone`-writable** (`#news-discussion`,
`#general`, `#rp-lfg`, `#clips-and-screens`, `#off-topic`) — which **satisfies the Onboarding
prerequisite** of ≥7 default channels with ≥5 writable (§7.2). The layout and the Onboarding
requirement were designed together; do not trim it below this without re-checking §7.4.

### 12.2 Making `#news` bot-post-only — exact permission overwrites

Channel permission overwrites use `allow` and `deny` bitfields. Precedence, per the official docs:

1. `@everyone` base guild permissions
2. role guild permissions (OR'd)
3. `@everyone` **channel deny**
4. `@everyone` **channel allow**
5. specific role **deny**
6. specific role **allow**
7. member **deny**
8. member **allow**

So a **role allow** beats an `@everyone` deny — which is exactly the mechanism that lets you deny
everyone and re-grant the bot.

**Overwrite A — `@everyone` role, in `#news`:**

| Permission | Bit | Value | Set |
|---|---|---|---|
| `VIEW_CHANNEL` | `1 << 10` | 1024 | **allow** |
| `READ_MESSAGE_HISTORY` | `1 << 16` | 65536 | **allow** |
| `SEND_MESSAGES` | `1 << 11` | 2048 | **deny** |
| `SEND_TTS_MESSAGES` | `1 << 12` | 4096 | **deny** |
| `ADD_REACTIONS` | `1 << 6` | 64 | **deny** |
| `EMBED_LINKS` | `1 << 14` | 16384 | **deny** |
| `ATTACH_FILES` | `1 << 15` | 32768 | **deny** |
| `MENTION_EVERYONE` | `1 << 17` | 131072 | **deny** |
| `CREATE_PUBLIC_THREADS` | `1 << 35` | 34359738368 | **deny** |
| `CREATE_PRIVATE_THREADS` | `1 << 36` | 68719476736 | **deny** |
| `SEND_MESSAGES_IN_THREADS` | `1 << 38` | 274877906944 | **deny** |

```json
{
  "id": "<GUILD_ID>",
  "type": 0,
  "allow": "66560",
  "deny": "377957308480"
}
```

(For the `@everyone` overwrite, `id` is the **guild ID** — the `@everyone` role always shares the
guild's snowflake. `type: 0` = role.)

**Overwrite B — the bot's role, in `#news`:**

| Permission | Bit | Value |
|---|---|---|
| `VIEW_CHANNEL` | `1 << 10` | 1024 |
| `SEND_MESSAGES` | `1 << 11` | 2048 |
| `EMBED_LINKS` | `1 << 14` | 16384 |
| `ATTACH_FILES` | `1 << 15` | 32768 |
| `READ_MESSAGE_HISTORY` | `1 << 16` | 65536 |
| `MENTION_EVERYONE` | `1 << 17` | 131072 |
| `MANAGE_MESSAGES` | `1 << 13` | 8192 |
| `ADD_REACTIONS` | `1 << 6` | 64 |
| `MANAGE_WEBHOOKS` | `1 << 29` | 536870912 |

```json
{
  "id": "<BOT_ROLE_ID>",
  "type": 0,
  "allow": "537128000",
  "deny": "0"
}
```

Both integers verified arithmetically:

```python
# @everyone deny
2048 + 4096 + 64 + 32768 + 16384 + 131072 \
  + 34359738368 + 68719476736 + 274877906944   # == 377957308480
# @everyone allow
1024 + 65536                                    # == 66560
# bot allow
1024 + 2048 + 16384 + 32768 + 65536 + 131072 + 8192 + 64 + 536870912  # == 537128000
```

**Why each bot permission is there:**

- `EMBED_LINKS` — **without it the bot's embeds silently do not render.** Classic, maddening bug.
- `MENTION_EVERYONE` — required to ping the **non-mentionable** `@GTA6 News` role (§6.4). Granted
  **only in `#news`**.
- `MANAGE_MESSAGES` — only needed if you later crosspost a *webhook's* message (§5.3), or want to pin
  the digest. Drop it if neither applies.
- `MANAGE_WEBHOOKS` — only if the bot manages its own webhook. Drop it otherwise.
- `ADD_REACTIONS` — optional; for seeding reactions on digest posts.
- `ATTACH_FILES` — for posting a chart/image directly rather than by URL. Drop if unused.

**Minimum viable bot allow** (no reactions, no webhook management, no pinning):
`1024 + 2048 + 16384 + 65536 + 131072 = 216064`.

### 12.3 Permissions elsewhere

**`@everyone` at the SERVER level — the highest-leverage control in this document:**

- **Deny `ATTACH_FILES`** (`1 << 15`). Then allow it back **only in `#clips-and-screens`**. Per §8.8,
  AutoMod cannot scan attachments at all, so this permission is your *only* control over uploaded leak
  video. **If you do one thing from this document, do this.**
- **Deny `EMBED_LINKS`** (`1 << 14`) for `@everyone` server-wide. Members can still *post* URLs (that
  is `SEND_MESSAGES`), but no auto-preview renders — so a leak link does not auto-play a thumbnail
  before a mod arrives. Meaningfully reduces harm from the seconds a bad link is up.
- **Deny `MENTION_EVERYONE`** for `@everyone` server-wide.
- **Deny `CREATE_PUBLIC_THREADS` / `CREATE_PRIVATE_THREADS`** at launch. Threads are unmoderated side
  rooms; enable later when you have staff coverage.

**`#news-discussion`:** allow `SEND_MESSAGES` + `ADD_REACTIONS`; keep `ATTACH_FILES` and `EMBED_LINKS`
denied; **slow mode 30 s**.

**`#clips-and-screens`:** the only channel allowing `ATTACH_FILES`. **Slow mode 60 s.** Consider making
it staff-post-only for the first weeks — this is the highest-risk channel in the server by a wide
margin.

**Slow mode reminder:** `rate_limit_per_user` range is **0–21600** s, and **bots are unaffected**
[OFFICIAL] — so slow mode on `#news` would never throttle your digest anyway. Set it on the human
channels.

### 12.4 Forum channel? Thread-per-story?

**No, not at launch.**

- **A Forum channel for `#news` is wrong.** A webhook can create forum threads via `thread_name`, and a
  bot can too — but a forum turns each story into a separate discussion room needing separate
  moderation. With a small mod team that is exactly how unmoderated leak-sharing corners appear. A
  forum also breaks the "scan the day's news in one glance" ergonomics that make a digest worth
  reading.
- **Thread-per-story is a good idea at the wrong time.** It is genuinely the best structure for big
  events (trailer drops) — but it requires the bot to create a thread per post and members to be able
  to talk in threads, which reopens the moderation surface you just closed. **Ship flat, add
  thread-per-story for major events once you have mod coverage.**
- **Where a forum IS right:** if you later add whitelist applications. The consistent advice from
  FiveM/RP community guides is that a flat application channel buries applications, and a **forum makes
  each applicant a trackable thread**. That is the one clear forum win for this genre.

### 12.5 "Official vs rumour" separation — the important call

**Do not create a `#rumours` or `#leaks` channel. This is the single highest-risk structural decision
available to you, and the answer is no.**

Given §10.6 — a §512(h) subpoena reportedly reached **DarkViperAU's server, which hosted no leaked
clips** — a channel *named* for rumours or leaks does two harmful things:

1. It **advertises** the server as a leak-adjacent venue, to both members and rights-holders.
2. It **invites** exactly the content you cannot afford, then makes "we prohibit leaks" incoherent.

Instead, express the official/unofficial distinction **inside `#news`, visually**, where the bot
controls everything:

- **Embed colour** as the signal: e.g. green = Rockstar first-party, blue = Take-Two IR,
  red = YouTube upload.
- **`author.name`** always names the source ("Rockstar Newswire", "Take-Two Investor Relations").
- **A `[Community]` / `[Unconfirmed]` prefix** in the title if you ever carry non-first-party items.
- Since the brief is **first-party only**, everything in `#news` is official by construction — which is
  the cleanest possible position. **Keep it.**

Put the community's speculation in **`#news-discussion`**, a neutrally-named channel where talk is fine
and links/attachments are denied.

### 12.6 What large GTA/FiveM RP Discords actually do

From FiveM/RP community setup guides (third-party, not Discord official):

- Standard skeleton: `#welcome`, `#rules`, `#announcements`, `#server-status`, `#support`,
  `#general`, plus department/faction channels (PD/EMS/DOJ) and voice rooms.
- **Announcements are always bot/staff-only and locked** — universal convention; matches §12.2.
- **Forums for whitelist applications**, not flat channels (§12.4).
- **A separate `#server-status`** channel is a cheap, well-liked pattern — a natural later home for
  this bot's own heartbeat.
- Consistent advice: pinned rules, daily staff presence, moderation bots for spam/reports.
- **Caveat:** these guides are commercial content-marketing from FiveM script/hosting vendors, not
  Discord documentation. Treat as convention, not authority.

---

## 13. SOURCES CONSULTED

**Official Discord API reference — `docs.discord.com` (primary, fetched 2026-08-25):**

- https://docs.discord.com/developers/resources/webhook
- https://docs.discord.com/developers/resources/webhook.md
- https://docs.discord.com/developers/topics/rate-limits
- https://docs.discord.com/developers/resources/message
- https://docs.discord.com/developers/resources/message.md
- https://docs.discord.com/developers/resources/auto-moderation
- https://docs.discord.com/developers/resources/channel
- https://docs.discord.com/developers/resources/guild
- https://docs.discord.com/developers/topics/permissions
- https://docs.discord.com/developers/topics/oauth2
- https://docs.discord.com/developers/reference
- https://docs.discord.com/developers/gateway/getting-started-with-privileged-intent-review
- https://docs.discord.com/llms.txt (doc index, referenced)
- https://discord.com/developers/docs/resources/webhook (301 → docs.discord.com)
- https://discord.com/developers/docs/topics/rate-limits (301 → docs.discord.com)

**Official Discord safety / policy:**

- https://discord.com/safety/auto-moderation-in-discord
- https://discord.com/safety/copyright-trademark-policy-explainer
- https://discord.com/safety/our-response-to-the-pentagon-leaks
- https://discord.com/terms/guidelines-march-2022
- https://discord.com/terms/terms-of-service-may-2020
- https://discord.com/community/developing-server-rules
- https://discord.com/blog/community-onboarding-welcome-your-new-members

**Discord support articles — HTTP 403 to automated fetchers; content via search snippets only:**

- https://support.discord.com/hc/en-us/articles/4421269296535-AutoMod-FAQ
- https://support.discord.com/hc/en-us/articles/360032008192-Announcement-Channel-FAQ
- https://support.discord.com/hc/en-us/articles/360028384531-Channel-Following-FAQ
- https://support.discord.com/hc/en-us/articles/11074987197975-Community-Onboarding-FAQ
- https://support.discord.com/hc/en-us/articles/10394859532823-Community-Onboarding-Examples
- https://support.discord.com/hc/en-us/articles/10069840290711-Filter-Messages-Using-Regular-Expressions-Regex
- https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots
- https://support.discord.com/hc/en-us/articles/4410339349655-Discord-s-Copyright-IP-Policy
- https://support.discord.com/hc/en-us/articles/360034632292-Sending-Messages
- https://support.discord.com/hc/en-us/community/posts/4417433663639-Allow-More-than-10-Announcements-per-Hour
- https://support-dev.discord.com/hc/articles/8562894815383-Discord-Developer-Terms-of-Service (307→403)
- https://support-dev.discord.com/hc/en-us/articles/40281523410967-Changes-to-Privileged-Intent-Access-for-Discord-Apps
- https://support-dev.discord.com/hc/en-us/articles/6205754771351-How-do-I-get-Privileged-Intents-for-my-bot
- https://support-dev.discord.com/hc/en-us/articles/6223003921559-My-Bot-is-Being-Rate-Limited

**Discord GitHub (official repo issues/discussions — behaviour clarifications):**

- https://github.com/discord/discord-api-docs/issues/4047 (6000 cap is per-message, not per-embed)
- https://github.com/discord/discord-api-docs/issues/7356 (AutoMod allowlist wildcard bypass)
- https://github.com/discord/discord-api-docs/discussions/6860 (no lookaround in AutoMod regex)
- https://github.com/discord/discord-api-docs/discussions/6330 (webhooks cannot opt into AutoMod)
- https://github.com/discord/discord-api-docs/issues/1161 (bot crosspost endpoint support)
- https://github.com/discord/discord-api-docs/issues/1510 (bots using /crosspost and /followers)
- https://github.com/discord/discord-api-docs/issues/2701 (follow-up endpoint rate limits)
- https://github.com/discord/discord-api-docs/issues/5288 (role mentions in interaction responses)
- https://github.com/discord/discord-api-docs/issues/7296 (onboarding default-channel behaviour)
- https://github.com/discordjs/discord.js/issues/4956 (crosspost rate-limit errors)
- https://github.com/discordjs/discord.js/issues/3882 (non-mentionable role mentions)

**Python library metadata (PyPI / GitHub):**

- https://pypi.org/project/discord.py/
- https://pypi.org/project/py-cord/
- https://pypi.org/project/disnake/
- https://pypi.org/project/hikari/
- https://pypi.org/project/nextcord/ (page failed to render metadata on fetch)
- https://github.com/nextcord/nextcord/releases
- https://docs.nextcord.dev/
- https://piptrends.com/compare/discord.py-vs-nextcord-vs-py-cord-vs-hikari

**Take-Two / GTA 6 subpoena reporting (§10.6):**

- https://torrentfreak.com/take-two-expands-gta-6-leak-hunt-with-dmca-subpoenas/
- https://www.pcgamer.com/games/grand-theft-auto/take-two-kicks-off-gta-6-leaker-hunt-with-subpoenas-demanding-records-from-microsoft-and-discord/
- https://www.tomshardware.com/video-games/console-gaming/take-two-subpoenas-microsoft-for-windows-device-ids-of-everyone-in-three-discord-servers-in-gta-6-leak-hunt
- https://variety.com/2026/gaming/news/gta-6-leaks-rockstar-subpoenas-microsoft-discord-1236840176/
- https://kotaku.com/take-two-subpoenas-microsoft-and-discord-records-related-to-spread-of-gta-6-leaks-2000726633
- https://dig.watch/updates/dmca-subpoenas-microsoft-discord-gta-leaks
- https://torrentfreak.com/riaa-uses-dmca-subpoena-to-go-after-discord-pirates-220508/

**Third-party / community references (corroboration only, explicitly NOT authoritative):**

- https://www.pythondiscord.com/pages/guides/python-guides/discord-embed-limits/
- https://discordjs.guide/legacy/popular-topics/embeds
- https://guide.disnake.dev/popular-topics/embeds
- https://docs.disnake.dev/en/v2.9.0/api/automod.html
- https://birdie0.github.io/discord-webhooks-guide/other/rate_limits.html
- https://birdie0.github.io/discord-webhooks-guide/structure/allowed_mentions.html
- https://docs.discord.food/topics/rate-limits (Userdoccers, community-reverse-engineered)
- https://docs.discord.food/resources/message
- https://treeben77.github.io/automod-regex-generator/regexes.html
- https://rustexp.lpil.uk/ (recommended by Discord for testing AutoMod regex)
- https://www.gitguardian.com/remediation/discord-webhook-url
- https://cybrancee.com/blog/discord-webhooks-explained-what-they-can-and-cant-do/
- https://carl.gg/
- https://peakbot.pro/ (several 2026 AutoMod/onboarding/bot-comparison articles)
- https://valt.gg/blog/discord-automod-setup-guide/
- https://blog.communityone.io/discord-automod-guide-regex-banned-words/
- https://www.vibebot.gg/server-templates/fivem
- https://www.vibebot.gg/blog/gta-6-discord-server-setup
- https://fivemania.com/blog/how-to-set-up-a-discord-server-for-fivem-roleplay
- https://www.keepgrid.net/blog/fivem-discord-setup-guide

---

## 14. EXPLICITLY UNVERIFIED — do not treat as fact

Collected in one place so nothing here silently becomes a constant:

| Claim | Status |
|---|---|
| Per-webhook rate limit **30 / 60 s** | **Not in official docs.** Community consensus. Read headers instead. |
| Per-channel message limit **5 / 5 s** | **Not in official docs.** Community consensus. |
| Crosspost limit **10 / hour** | [SUPPORT] via snippet; **not** in the API reference. Also **unclear whether per-channel or per-guild**. |
| Create Message `content` = **2000 vs 4000** | **Unresolved** (§4.1). Docs rendered 4000; could not quote verbatim; webhook route is definitively 2000. **Use 2000.** |
| Which embed fields render markdown / masked links | **Not officially documented.** Table in §4.3 is consensus + observed behaviour. **Test it.** |
| Publishing does **not** re-notify your own server's members | Inferred from mechanics + [SUPPORT] description of follower behaviour. **No official sentence confirms the negative. Test it.** |
| Whether webhook `@everyone` mentions are permission-gated | **Sources conflict; unresolved.** Assume the pessimistic case (§6.5). |
| `roles`/`users` arrays mutually exclusive with `parse` values | Described as mutually exclusive; **not verbatim-verified.** §6.2 config avoids depending on it. |
| AutoMod scans attachment **filenames** | **No official statement.** Assume **not** scanned. |
| AutoMod max KEYWORD rules: **6** (API) vs **3** (safety page) | **Documented conflict.** API reference is authoritative and newer; **verify in your server UI.** |
| Onboarding prerequisite **≥7 / ≥5** channels | [SUPPORT] via snippet; could not fetch the Modify Guild Onboarding endpoint's constraints. |
| Modify Guild Onboarding required permission | **Unverified**; assumed `MANAGE_GUILD` + `MANAGE_ROLES`. |
| nextcord latest version / release dates | **Could not verify.** PyPI page failed to render; GitHub releases gave no reliable dates. |
| Zira bot current status | **Could not verify at all.** Treat as possibly abandoned. |
| DMCA processing time 24–48 h | Third-party estimate, **not** a Discord SLA. |
