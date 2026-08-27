# llm-dedup — LLM-assisted curation + deduplication for a daily GTA 6 news digest

Research date: **2026-08-24**. All Claude API figures verified against primary docs on
platform.claude.com on this date. Output language: **English only**.

> **STALENESS WARNING — READ THIS FIRST.** The `claude-api` skill bundled with the local
> Claude Code install has a model table cached **2026-06-04** that is now **out of date**.
> It lists Claude Opus 4.8 / Sonnet 4.6 as current. Live docs show **Claude Opus 5**
> (`claude-opus-5`) and **Claude Sonnet 5** (`claude-sonnet-5`) shipped, and Opus 4.8 /
> Sonnet 4.6 are now under the **"Legacy models"** accordion. Sonnet 5 is **cheaper**
> than Sonnet 4.6 ($2/$10 vs $3/$15). Do not design against the cached table.

---

## 1. Current model IDs and pricing (Claude API, first-party, USD per million tokens)

Source: <https://platform.claude.com/docs/en/about-claude/pricing> and
<https://platform.claude.com/docs/en/about-claude/models/overview>

| Model | API ID | Base input | 5m cache write | 1h cache write | Cache read | Output | Context | Max output |
|---|---|---|---|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | $10 | $12.50 | $20 | $1.00 | $50 | 1M | 128K |
| Claude Mythos 5 (Project Glasswing only) | `claude-mythos-5` | $10 | $12.50 | $20 | $1.00 | $50 | 1M | 128K |
| **Claude Opus 5** | `claude-opus-5` | **$5** | $6.25 | $10 | $0.50 | **$25** | 1M | 128K |
| Claude Opus 4.8 *(legacy)* | `claude-opus-4-8` | $5 | $6.25 | $10 | $0.50 | $25 | 1M | 128K |
| Claude Opus 4.7 *(legacy)* | `claude-opus-4-7` | $5 | $6.25 | $10 | $0.50 | $25 | 1M | 128K |
| Claude Opus 4.6 *(legacy)* | `claude-opus-4-6` | $5 | $6.25 | $10 | $0.50 | $25 | 1M | 128K |
| **Claude Sonnet 5** | `claude-sonnet-5` | **$2** | $2.50 | $4 | $0.20 | **$10** | 1M | 128K |
| Claude Sonnet 4.6 *(legacy)* | `claude-sonnet-4-6` | $3 | $3.75 | $6 | $0.30 | $15 | 1M | 128K |
| **Claude Haiku 4.5** | `claude-haiku-4-5` | **$1** | $1.25 | $2 | $0.10 | **$5** | 200K | 64K |

Notes verified on the pricing page:

- **Sonnet 5's $2/$10 is permanent.** It launched as "introductory pricing through
  2026-08-31" and the docs now carry an explicit note that the scheduled increase to
  $3/$15 on 2026-09-01 **will not occur**. Safe to build a budget on $2/$10.
- Every model ID is a **pinned snapshot**, including the dateless ones (4.6-generation
  onward). `claude-sonnet-5` is not an evergreen pointer.
- **Tokenizer change:** "Claude 4.7 and later models" use a newer tokenizer producing
  **~30% more tokens for the same text**. Sonnet 4.6 and earlier use the old one.
  Sonnet 5 / Opus 5 are on the new tokenizer → **inflate any char/4 token estimate by
  ~30%** when budgeting. Verify with `client.messages.count_tokens()`.
- Anthropic **does not sell an embeddings endpoint.** There is no Claude embedding model.
  Embeddings must come from a third party (Voyage) or run locally.

### Model tier recommendation for this bot

| Job | Model | Why |
|---|---|---|
| (a) real-news vs clickbait/rehash | **`claude-haiku-4-5`** | Pure classification against a fixed rubric. $1/$5. Cheapest tier that still reads nuance. Batch 20–30 items per request. |
| (b) cluster items reporting the same story | **`claude-sonnet-5`** | Needs semantic judgment across items; Haiku is measurably weaker at multi-item reasoning. At $2/$10 the price gap vs Haiku is only 2× and the volume here is tiny (post-heuristics). |
| (c) write the 2–3 sentence summary | **`claude-sonnet-5`** | This is the user-visible text. Haiku's prose is noticeably flatter. Only ~8 summaries/day — cost is negligible. |
| (d) pick the day's top items | **`claude-sonnet-5`** | One call/day over ~40 survivors. Ranking needs comparative judgment. |

**Do not use Opus 5 or Fable 5 for any of this.** A news-triage rubric is not an
intelligence-limited task; you'd pay 2.5–5× for no measurable digest-quality gain.
Consider Opus 5 only if Sonnet 5 demonstrably mis-ranks after prompt iteration.

### Haiku 4.5 footguns (contradicts the skill's blanket defaults)

The `claude-api` skill says "default to adaptive thinking." **That 400s on Haiku 4.5.**

- `thinking: {"type": "adaptive"}` → **400**. Haiku 4.5 supports only *extended* thinking
  (`{"type":"enabled","budget_tokens":N}`, N ≥ 1024, N < `max_tokens`).
  For classification you want **no thinking at all** — omit the param.
- **`output_config.effort` is not supported on Haiku 4.5 → 400.** Effort works on
  `claude-fable-5`, `claude-mythos-5`, `claude-opus-5`, `claude-opus-4-8/4-7/4-6`,
  `claude-sonnet-5`, `claude-sonnet-4-6`. Not Haiku.
- 200K context / 64K max output (all the Sonnet-5/Opus-5 tier are 1M / 128K).

---

## 2. Prompt caching

Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>

Multipliers relative to base input: **5m write = 1.25×**, **1h write = 2×**,
**read/refresh = 0.1×**. Break-even: 5m TTL pays off after **one** read; 1h TTL after
**two** reads. Multipliers **stack** with the Batch discount and data residency.

### Minimum cacheable prefix — the design-critical table

| Model | Minimum tokens to cache |
|---|---|
| Opus 5, Fable 5, Mythos 5 | **512** |
| Opus 4.8, **Sonnet 5**, Sonnet 4.6, Sonnet 4.5 | **1,024** |
| Opus 4.7, Mythos Preview | 2,048 |
| **Haiku 4.5**, Opus 4.6, Opus 4.5 | **4,096** |

**Gotcha that will bite this project:** a triage rubric of ~1,200–1,500 tokens **caches on
Sonnet 5** but **silently will not cache on Haiku 4.5** (needs 4,096). No error is
returned — `cache_creation_input_tokens` and `cache_read_input_tokens` both come back `0`.
Do **not** pad the prompt to 4,096 tokens to force a cache hit; padding costs more than
the cache saves at this volume. Just accept uncached input on the Haiku triage stage.

Other mechanics:

- Max **4** explicit `cache_control` breakpoints. **Automatic caching (top-level
  `cache_control`) consumes one of the 4** — 4 explicit + automatic = **400 error**.
- **TTL clock starts at the request start and includes generation time.** A 4-minute
  response leaves ~1 minute of a 5m cache.
- 20-block lookback window when searching for a prior cache entry.
- Invalidation hierarchy `tools` → `system` → `messages`. Changing tool definitions kills
  everything. `tool_choice` and images only invalidate the messages cache.
- **Any change to `output_config.format` invalidates the prompt cache.** Keep the JSON
  schema dict a byte-stable literal; never build it from a `set`, an unsorted
  `json.dumps`, or a dict comprehension with nondeterministic order.
- Verify: `usage.cache_creation_input_tokens` / `usage.cache_read_input_tokens`.
  `total_input = cache_read + cache_creation + input_tokens`.

**Honest verdict for this bot:** prompt caching is **near-worthless here**. The stable
prefix is a ~1.5K-token rubric; the volatile part is 5–7K tokens of article text per
request. Best case saving is ~$0.02/day. The real cost lever is **batching many items
into one request**, not caching. Implement caching only if the rubric grows past ~5K
tokens (e.g. few-shot examples of good/bad GTA 6 items).

---

## 3. Batch API

Source: <https://platform.claude.com/docs/en/build-with-claude/batch-processing>

- **50% off both input and output tokens.**
- Batch prices: Haiku 4.5 **$0.50/$2.50**; Sonnet 5 **$1/$5**; Sonnet 4.6 $1.50/$7.50;
  Opus 5 **$2.50/$12.50**; Fable 5 $5/$25.
- Limits: **≤100,000 requests or 256 MB** per batch, whichever hits first.
- Turnaround: most < 1 hour; **hard expiry at 24 hours**. Results retrievable when all
  requests finish *or* at 24h, whichever is first.
- **Expired requests are not billed.** Good failure mode.
- Results available **29 days** after creation, streamed as `.jsonl`.
- `custom_id`: 1–64 chars, `^[a-zA-Z0-9_-]{1,64}$`. Use it to carry your DB item id.
- Result types: `succeeded` / `errored` / `canceled` / `expired`.
- **`max_tokens` must be ≥ 1 inside a batch** — `max_tokens: 0` (cache pre-warming) is
  rejected, because an ephemeral cache entry would expire before the follow-up runs.
- Prompt caching **does** work inside batches, but the docs explicitly recommend the
  **1-hour TTL** for batches with shared context, since batches routinely exceed 5 min.
- Rate limits apply both to Batches HTTP calls and to the count of queued in-batch requests.
- Batch API **rejects the Fable 5 `fallbacks` parameter**.
- Beta `output-300k-2026-03-24` raises batch max output to 300K on Opus 5/4.8/4.7/4.6 and
  Sonnet 5/4.6. Irrelevant here.

**Recommendation: skip the Batch API for v1.** Reasons specific to this project:

1. Absolute saving is ~$2–4/month. Not worth a second state machine.
2. **Instant alerts must never go through batch** (24h worst case). So you'd need both
   paths anyway.
3. The 24h expiry interacts badly with the **PC-sleeps hazard**. A batch submitted at
   06:00 that expires unread because the machine slept 20 hours is a silently-lost day.
   The synchronous path fails loudly and retries on the next wake — much better fit for
   the catch-up design ("has today's digest posted? if not, post now").

Revisit Batch if candidate volume grows ~10× (3,000 items/day).

---

## 4. Realistic monthly cost estimate

Workload: **100–300 candidate items/day → 5–8 digest entries.**

Token assumptions (new tokenizer, +30% inflation already applied):

- Triage payload per item (title + source + date + ~500 chars of RSS description): **~250 tok**
- Triage rubric / system prompt: **~1,200 tok**
- Triage output per item (verdict enum + story_key + score + evidence span): **~40 tok**
- Summarize payload per survivor (fuller excerpt ~2,000 chars): **~600 tok**
- Summary output per digest entry: **~120 tok**

Pipeline: heuristics kill ~60% of items before any LLM call (see §5). 300 → ~120 for
triage is pessimistic; assume the **worst case of triaging all 300** so the number is safe.

### Stage B — triage, Haiku 4.5, 25 items per request

| | Worst case (300 items/day) | Typical (150 items/day) |
|---|---|---|
| Requests/day | 12 | 6 |
| Input tok/day | 12 × (1,200 + 25×250) = **89,400** | **44,700** |
| Output tok/day | 12 × 25 × 40 = **12,000** | **6,000** |
| Cost/day | 89,400×$1/1M + 12,000×$5/1M = **$0.149** | **$0.075** |
| **Cost/month** | **≈ $4.50** | **≈ $2.25** |

### Stage C+D — cluster + summarize + rank, Sonnet 5, ~40 survivors, 1–2 requests/day

| | Value |
|---|---|
| Input tok/day | 1,500 + 40×600 = **25,500** |
| Output tok/day | 8×120 + cluster labels ≈ **1,400** |
| Cost/day | 25,500×$2/1M + 1,400×$10/1M = **$0.065** |
| **Cost/month** | **≈ $1.95** |

### Totals

| Configuration | Worst case (300/day) | Typical (150/day) |
|---|---|---|
| **Recommended: Haiku 4.5 triage + Sonnet 5 cluster/summarize** | **≈ $6.50/mo** | **≈ $4.20/mo** |
| All Sonnet 5 | ≈ $11/mo | ≈ $6/mo |
| All Opus 5 | ≈ $27/mo | ≈ $15/mo |
| Recommended + Batch API on triage | ≈ $4.25/mo | ≈ $3.10/mo |

**Headline: $5–7/month at realistic volume, worst case ~$11/month if you run everything
on Sonnet 5.** This is small enough that model choice should be driven by digest quality,
not cost. Budget $15/month and stop optimizing.

Cost-blowup risks to guard in code:
- **One LLM call per item** instead of batching 25 → 12× more requests, and the 1,200-token
  rubric is re-sent 300× instead of 12× → ~$0.36/day extra on the rubric alone. Batch items.
- **O(n²) pairwise LLM clustering** on 300 items = 44,850 calls/day ≈ **$450/day**. Never
  do this; cluster with heuristics + one LLM pass over cluster candidates (§5.7).
- Feeding full article bodies (not excerpts) into triage → 5–10× input tokens.
- A retry loop with no cap after a schema-validation failure.

---

## 5. Non-LLM dedup — where cheap heuristics beat an LLM call

The correct architecture is a **funnel**: each stage is orders of magnitude cheaper than
the next, so put the cheapest discriminator first. An LLM should only ever see items that
survived every free filter.

```
300 raw items
  → §5.1 URL canonicalisation      (free, deterministic)   → ~240
  → §5.2 title normalisation hash  (free, deterministic)   → ~190
  → §5.3 SimHash near-dup          (free, ~50 LOC)         → ~140
  → §5.4 TF-IDF cosine clustering  (free / sklearn)        → ~120 items in ~45 clusters
  → §5.6 embeddings (OPTIONAL)     (~$0/mo, free tier)     → tighter clusters
  → LLM triage (Haiku)             (~$0.15/day)            → ~40 substantive
  → LLM summarise + rank (Sonnet 5)(~$0.07/day)            → 5–8 digest lines
```

### 5.1 URL canonicalisation — pure win, never use an LLM

Deterministic, free, and an LLM would be *less* reliable. Steps:

1. **Resolve redirect chains.** Feeds are full of wrappers: `t.co`, `feedproxy.google.com`,
   `news.google.com/rss/articles/...`, Reddit `out.reddit.com`, Discord `l.discord.com`.
   Follow 301/302/303/307/308 with `httpx` (already installed) —
   `httpx.head(url, follow_redirects=True)`, fall back to `GET` with a byte cap for
   servers that reject HEAD. Cap the chain at ~5 hops; cache resolutions in SQLite so you
   resolve each wrapper once, ever.
2. **Strip tracking params:** `utm_*`, `fbclid`, `gclid`, `dclid`, `msclkid`, `mc_cid`,
   `mc_eid`, `igshid`, `ref`, `ref_src`, `source`, `cmpid`, `at_medium`, `_hsenc`, `yclid`,
   `twclid`, `s`, `sh`. Whitelist-by-exclusion is safer than a blacklist for query params
   you don't recognise — but beware: some sites put the article id in the query
   (`?id=12345`, `?p=987`, `?story=`). Keep unknown params, drop known-tracking ones.
3. **De-AMP:** `cdn.ampproject.org/c/s/<real-host>/<path>` → `https://<real-host>/<path>`;
   strip trailing `/amp`, `/amp/`, `.amp`; drop `?amp=1`, `?outputType=amp`; rewrite
   `amp.<host>` → `<host>`.
4. **Normalise:** lowercase scheme+host, force `https`, strip `www.`, drop the `#fragment`,
   collapse `//`, strip the trailing slash, sort remaining query params, percent-decode
   unreserved chars.
5. Store `url_canonical` **with a UNIQUE index** — that index alone is your exact-dup guard,
   and it survives restarts (which an in-memory set does not).

Libraries if you'd rather not hand-roll: `urlcanon` (browser-parity canonicalisation
ruleset, Python+Java), `urlclean` (`weedparams()` + `httpresolve()`), `url-sanitize`
(ClearURLs-compatible, daily-synced rule catalog across four upstream sources).
**Recommendation: hand-roll ~50 lines using `urllib.parse` + `httpx`.** The user's repo
convention favours a lean dependency set, all three libs add a dep for logic you can read
in one screen, and the tracking-param list needs project-specific tuning anyway.

### 5.2 Title normalisation — free, catches literal reposts

`unicodedata.normalize("NFKD", t)` → casefold → strip publisher suffix
(`" - IGN"`, `" | Eurogamer"`, `" — VGC"`, `" :: Rockstar Newswire"`) → strip clickbait
prefixes (`BREAKING:`, `RUMOR:`, `REPORT:`, `LEAK:`, `UPDATE:`) → collapse all non-alnum
runs to single spaces → strip. Hash it (`blake2b(digest_size=16)`), UNIQUE index.

Catches the same headline arriving via 3 feeds with different formatting. **An LLM call
here would cost money to do worse.**

### 5.3 SimHash — free, best tool for "same text, lightly edited"

64-bit SimHash over word 3-shingles; **Hamming distance ≤ 3 → near-duplicate**. This is
the right detector for syndicated wire copy and aggregator rewrites that keep most of the
original sentences.

At 300 items/day, **all-pairs comparison is 44,850 XOR+popcount operations on 64-bit ints
— microseconds.** Do NOT build an LSH banding index; that machinery exists for millions of
documents. ~50 lines of pure Python, zero dependencies.

### 5.4 TF-IDF cosine — the workhorse for "same story, different words"

Thresholds from the literature and from what this corpus needs:

| Goal | Cosine threshold |
|---|---|
| Near-duplicate (same text) | **≥ 0.90** (standard in the dedup literature: ≥0.9 and <1.0 = near-dup) |
| **Same story, different outlet** (what you actually need) | **~0.45–0.60** — 8 outlets covering one Rockstar announcement share entities, not phrasing |

**The single biggest practical gotcha:** fit the IDF on a **rolling 30-day window**, not on
today's items. On a single-day, single-topic corpus, "GTA", "Rockstar", "Take-Two" appear
in nearly every document, so IDF crushes them to ~0 — and then the only surviving signal is
random filler words, and *everything* looks either identical or unrelated. Persist the
document-frequency counts in SQLite and update them daily.

Vectorise on **title + first ~2 sentences**, not the full body — boilerplate ("Follow us on
X", "Read more", cookie notices) dominates full-body TF-IDF and creates false clusters.

Implementation: `sklearn.feature_extraction.text.TfidfVectorizer` is the obvious choice but
pulls in scipy+numpy. At 300 docs/day a hand-rolled `collections.Counter` + cosine over
dicts is ~60 lines and fast enough. Either is defensible; sklearn is the lower-risk choice
if numpy is acceptable.

### 5.5 MinHash + LSH — probably skip

`datasketch.MinHashLSH(threshold=0.8, num_perm=128)` (default threshold is 0.8) over
k-shingles. Better recall than SimHash on longer documents with reordered content. The
2025 ACM paper *"Benchmarking Near-Duplicate Detection in the era of Pay-walled News"*
(WWW '25 companion, DOI 10.1145/3701716.3715303, introduces the NDD-NS dataset) benchmarks
exactly MinHash-LSH vs SimHash vs sentence-transformer approaches on news snippets — worth
reading if you want a rigorous choice, though the full text is paywalled (403 on fetch).

**Verdict: not for v1.** LSH is an indexing optimisation for corpora too large to
all-pairs; you have 300 items. Adds a dependency to solve a scale problem you don't have.
Add it only if SimHash recall measurably disappoints.

### 5.6 Embeddings — optional, and effectively free if you want them

Needed only when wording diverges completely: *"Rockstar delays GTA 6"* vs *"Next Grand
Theft Auto slips to 2027"* share almost no lexical overlap, so TF-IDF can miss the pair.

Since **Anthropic sells no embeddings endpoint**, options:

| Option | Price | Notes |
|---|---|---|
| **Voyage `voyage-4-lite`** | **$0.02/MTok, 200M free tokens** | Best fit. 300 items × 300 tok = 90K tok/day = **2.7M tok/month → permanently inside the free tier**. Even paid: ~$0.05/month. |
| Voyage `voyage-4` | $0.06/MTok (200M free) | Better quality, still free at this volume. |
| Voyage `voyage-4-large` / `voyage-context-4` / `voyage-code-4` | $0.12/MTok (200M free) | Overkill. |
| Voyage `voyage-3.5-lite` / `voyage-3.5` | $0.02 / $0.06 per MTok | **No free tier** on the older generation. Prefer `voyage-4-lite`. |
| Local `sentence-transformers` (all-MiniLM-L6-v2) | $0 | Drags in torch (~2 GB) onto a Windows PC bot. **Bad fit** for this project's lean-dependency shape. |

Voyage caveat: **free token credits do not apply to their Batch API** (which is separately
33% off). Use the sync endpoint.

**Verdict: don't add embeddings in v1.** GTA 6 news has a narrow, entity-heavy vocabulary
where TF-IDF on a rolling IDF performs well. Add `voyage-4-lite` only after you measure
cross-outlet clustering misses on real data. It's one `httpx` POST and costs nothing, so
it's a cheap v2 upgrade — just don't pay the complexity up front.

### 5.7 Cross-outlet story clustering when 8 sites cover one story

This is precisely the case where **pairwise LLM comparison is the wrong answer** —
O(n²) = 44,850 calls/day ≈ $450/day. Correct design:

1. **Block by time.** Candidates only cluster within a **±36h** window. Stories don't
   cluster across weeks, and blocking collapses the comparison space.
2. **Build a similarity graph** over the block. Add an edge when *any* of:
   - identical `url_canonical` (§5.1), or
   - identical normalised-title hash (§5.2), or
   - SimHash Hamming ≤ 3 (§5.3), or
   - TF-IDF cosine ≥ ~0.55 (§5.4), or
   - embedding cosine ≥ ~0.80 (§5.6, if enabled).
3. **Connected components (union-find) = story clusters.** Single-link/connected-components
   is correct for near-dup, but it *over-merges* for topical similarity — so keep the
   cosine threshold high and tune on real data. If chaining becomes a problem, switch to
   agglomerative clustering with **complete or average linkage**, cutting the dendrogram at
   a fixed cosine height (news-clustering literature uses λ ≈ 0.60 cosine distance as the
   minimum before spawning a new cluster).
4. **Pick the cluster representative by source authority, then recency:**
   `first-party (Rockstar Newswire, rockstargames.com, @RockstarGames, Take-Two IR)`
   → `tier-1 outlet (IGN, Eurogamer, VGC, GameSpot)` → `aggregator/blog`; tie-break on
   earliest `published_at`. **This same first-party check is your INSTANT-alert trigger** —
   build it once, use it for both paths.
5. **Only now spend an LLM call** — one call per *cluster*, not per pair, asking it to
   confirm the cluster is one story and write the summary. Typically ~45 clusters/day.

---

## 6. Reliable structured-output / tool-use JSON pattern

Source: <https://platform.claude.com/docs/en/build-with-claude/structured-outputs>

**Supported models** (verified list): `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`,
`claude-opus-4-6`, `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-sonnet-4-5-20250929`,
`claude-opus-4-5-20251101`, `claude-haiku-4-5-20251001`. **Both models this bot needs
(Haiku 4.5 and Sonnet 5) support it.**

### Request shape

```python
output_config={
    "format": {
        "type": "json_schema",
        "schema": { ... }          # additionalProperties MUST be False
    }
}
```

- The old top-level **`output_format` is deprecated**; Python SDK v1.0+ rejects it on
  `client.beta.messages.create()`. Use `output_config.format`.
- Constrained decoding means **no retry loop is needed** for schema violations.
- **Grammar is compiled and cached 24h from last use.** First request with a new schema pays
  extra latency. Changing only `name`/`description` does *not* invalidate; changing structure
  does. Changing the tool set also invalidates when combining with tool use.
- **Any change to `output_config.format` invalidates the prompt cache.** Keep the schema a
  module-level literal constant.

### Supported vs unsupported JSON Schema

**Supported:** `object`/`array`/`string`/`integer`/`number`/`boolean`/`null`; `enum`
(scalars only); `const`; `anyOf`, `allOf` (not `allOf` with `$ref`); internal `$ref`/`$defs`;
`required`; `additionalProperties: false` (**mandatory**); string `format` (`date-time`,
`time`, `date`, `duration`, `email`, `hostname`, `uri`, `ipv4`, `ipv6`, `uuid`); array
`minItems` **only values 0 or 1**; `default`.

**Not supported:** recursive schemas; complex types in `enum`; external `$ref` (HTTP URLs);
`minimum`/`maximum`/`multipleOf`; `minLength`/`maxLength`; `pattern` regex; custom
extensions. The Python/TS/Ruby/PHP SDKs auto-strip unsupported constraints, fold them into
descriptions, and validate locally against your original schema.

→ Practical consequence: **you cannot enforce "summary ≤ 400 chars" or "score 0–10" in the
schema.** Use an `enum` for bounded integers and validate lengths in Python.

### The pattern to use in this bot

```python
# Batch N items per request. Top-level MUST be an object, never a bare array.
TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id":         {"type": "string"},   # ECHOED BACK, used to re-join
                    "verdict":         {"type": "string",
                                        "enum": ["official", "substantive", "rumor",
                                                 "rehash", "clickbait", "offtopic"]},
                    "newsworthiness":  {"type": "integer", "enum": [0,1,2,3,4,5]},
                    "story_key":       {"type": "string"},   # same string = same story
                    "insufficient_text": {"type": "boolean"},
                    "evidence_quote":  {"type": "string"},   # verbatim span, validated in Python
                },
                "required": ["item_id", "verdict", "newsworthiness", "story_key",
                             "insufficient_text", "evidence_quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}
```

Key decisions:

- **Top-level object wrapping an array**, never a bare top-level array.
- **`item_id` echo** so you can re-join to your SQLite rows — and so the model never has to
  emit a URL (see §7).
- **Enums for every judgment field.** Constrained decoding then *guarantees* a valid value;
  no `.lower()` normalisation, no unknown-label branch.
- Prefer **`output_config.format` over strict tool use** for this fixed-shape extraction.
  Tool use adds the tool-use system prompt overhead (Sonnet 5: 354 tok for `auto`/`none`,
  474 for `any`/`tool`; Haiku 4.5: 496/588) for no benefit when there's exactly one output
  shape. Use `strict: True` on a tool only when the model should *decide* whether to emit.
- `max_tokens`: 25 items × ~60 tok ≈ 1,500 → set **4000**. Under the ~16K non-streaming
  guidance, so no streaming needed.

### SDK note for this environment

`anthropic` is **not installed** (verified: only `aiosqlite`, `httpx`, `python-dotenv`).
`pip install anthropic`, then use `AsyncAnthropic` to match the repo's async shape:

```python
from anthropic import AsyncAnthropic
client = AsyncAnthropic()          # reads ANTHROPIC_API_KEY from .env

resp = await client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=4000,
    system=TRIAGE_RUBRIC,
    messages=[{"role": "user", "content": payload}],
    output_config={"format": {"type": "json_schema", "schema": TRIAGE_SCHEMA}},
    # NO thinking=..., NO output_config["effort"] — both 400 on Haiku 4.5
)
text = next(b.text for b in resp.content if b.type == "text")
data = TriageBatch.model_validate_json(text)   # Pydantic, second line of defence
```

The sync SDK offers `client.messages.parse(..., output_format=PydanticModel)` →
`response.parsed_output`, which validates for you. **I could not verify from the docs that
`parse()` exists on `AsyncAnthropic`** — treat that as unconfirmed and use the explicit
`output_config` + `model_validate_json` form above, which works either way and keeps the
API-key handling inside the SDK (so the repo's `RedactingFilter` still governs logging).

---

## 7. Hallucination control — the bot must never invent news

Layered, cheapest-and-most-deterministic first. Prompting alone is **not** sufficient.

### 7.1 Structural: the model never emits a URL (most important rule)

Carry an opaque `item_id` into the prompt; the model echoes `item_id` back; **your Python
code looks up `source_url` from SQLite and renders the digest line.** A model cannot
hallucinate a link it is never asked to produce. This removes the highest-embarrassment
failure mode (a plausible-looking dead IGN link) by construction, not by hope.

Corollary: never ask the model for dates either. Pass an ISO date in, render the date from
the DB out. No date arithmetic, ever — "yesterday" is a hallucination generator.

### 7.2 Give refusal a legitimate slot

`insufficient_text: boolean` + `summary: string`, with the prompt instructing: *if the
provided text is too thin, set `insufficient_text=true` and leave `summary` empty.*
Models fabricate hardest when refusal is not an available action; the RAG-grounding
literature classifies "over-responsiveness" (answering when it should abstain) as a
distinct hallucination category alongside inaccurate answers and improper citation.

### 7.3 Quote-grounding with a Python assertion (the highest-value check)

Require `evidence_quote` — a **verbatim span copied from the provided text** that supports
the summary. Then validate deterministically:

```python
def grounded(quote: str, source_text: str) -> bool:
    norm = lambda s: " ".join(s.split()).casefold()
    return len(quote) >= 25 and norm(quote) in norm(source_text)
```

If it fails, **drop the item from the digest** and log it. This converts an unverifiable
generative claim into a string-containment test. It is the practical form of the
"force grounding by requiring citations" pattern, and it costs ~40 output tokens per item.

### 7.4 Numeric and date post-check

Regex every number, date, price, platform name, and version string out of the generated
summary and assert each appears in the source text. For a GTA 6 channel the
highest-stakes hallucination is an **invented release date** — this catches it. Reject the
line and fall back to a bare title + link if the check fails.

### 7.5 Prompt clauses (the last layer, not the first)

```
Summarise ONLY from the text inside <article>...</article>.
Do NOT use prior knowledge about GTA 6, Rockstar Games, or Take-Two Interactive.
Do NOT infer or state release dates, prices, platforms, map details, or features
  that are not literally written in the provided text.
If the article reports a rumour, leak, or unconfirmed claim, your summary MUST label
  it as such and MUST name who claimed it.
Every factual clause in your summary must be supported by the span you return in
  evidence_quote.
If the provided text contains fewer than ~40 words of substance, set
  insufficient_text=true and leave summary empty. Do not guess.
Write in English. 2-3 sentences maximum.
```

Notes: extractive-leaning summarisation is materially less hallucination-prone than free
abstractive summarisation, so pushing the model toward "compress these sentences" rather
than "tell me about this" is itself a mitigation.

### 7.6 Refusal / stop-reason handling

Check `resp.stop_reason` **before** reading `resp.content` — with structured outputs, a
safety refusal means **the output may not match your schema**. On Fable 5 specifically a
refusal returns HTTP 200 with `stop_reason: "refusal"` and an empty `content` array, so
`resp.content[0]` raises IndexError. Sonnet 5 / Haiku 4.5 are far less likely to refuse
game-news triage, but the guard is two lines and prevents a crash loop inside the daily job.

---

## 8. All URLs found

Primary (Anthropic / vendor docs):

- <https://platform.claude.com/docs/en/about-claude/pricing> — authoritative pricing table, cache multipliers, batch prices, tool-use token overhead
- <https://platform.claude.com/docs/en/about-claude/models/overview> — current model IDs, context/output limits, legacy-model accordion
- <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> — min cacheable prefix per model, invalidation hierarchy, TTL semantics
- <https://platform.claude.com/docs/en/build-with-claude/batch-processing> — limits, 24h expiry, custom_id rules, caching-in-batch guidance
- <https://platform.claude.com/docs/en/build-with-claude/structured-outputs> — supported models, schema feature matrix, grammar caching
- <https://platform.claude.com/docs/en/build-with-claude/effort> — effort-parameter model support
- <https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking> — adaptive-thinking model support
- <https://platform.claude.com/docs/en/build-with-claude/extended-thinking> — Haiku 4.5 extended-thinking path
- <https://platform.claude.com/docs/en/build-with-claude/token-counting> — count_tokens for re-baselining under the new tokenizer
- <https://platform.claude.com/docs/en/api/models/list> — programmatic capability discovery
- <https://platform.claude.com/docs/en/about-claude/model-deprecations> — retirement schedule
- <https://claude.com/pricing> — public pricing page
- <https://www.anthropic.com/news/claude-haiku-4-5> — Haiku 4.5 launch post
- <https://docs.voyageai.com/docs/pricing> — Voyage embedding pricing + free-tier allowances

Dedup / clustering literature and tools:

- <https://dl.acm.org/doi/10.1145/3701716.3715303> — *Benchmarking Near-Duplicate Detection in the era of Pay-walled News* (WWW '25 companion); NDD-NS dataset; MinHash-LSH vs SimHash vs sentence-transformers. **403 on fetch — abstract only via search**
- <https://arxiv.org/pdf/1407.4416> — *In Defense of MinHash Over SimHash*
- <https://arxiv.org/html/2506.00277v1> — Hierarchical level-wise news clustering via multilingual Matryoshka embeddings (event vs topic vs theme dimensions)
- <https://arxiv.org/pdf/2007.10399> — *Automatic Story Construction from News Articles in an Online Fashion* (online threshold clustering, λ ≈ 0.60)
- <https://arxiv.org/pdf/2006.01117> — NSTM: real-time query-driven news overview composition at Bloomberg
- <https://arxiv.org/pdf/2409.11242> — *Measuring and Enhancing Trustworthiness of LLMs in RAG through Grounded Attributions and Learning to Refuse* — hallucination taxonomy incl. over-responsiveness / improper citation
- <https://arxiv.org/pdf/2311.17264> — RETSim: resilient and efficient text similarity
- <https://www.newscatcherapi.com/docs/news-api/guides-and-concepts/clustering-news-articles> — practical similarity-graph + threshold clustering writeup
- <https://yorko.github.io/2023/practical-near-dup-detection/> — practical datasketch MinHashLSH walkthrough
- <https://sumonbis.github.io/academic-project/simhash/> and <https://github.com/sumonbis/NearDuplicateDetection> — SimHash near-dup reference implementation
- <https://spotintelligence.com/2023/01/02/simhash/> — SimHash in Python tutorial
- <https://snyk.io/advisor/python/datasketch/functions/datasketch.MinHashLSH> — MinHashLSH API/defaults
- <https://pypi.org/project/urlcanon> — URL canonicalisation library (Python + Java)
- <https://pypi.org/project/urlclean> — `weedparams()` / `httpresolve()` tracking-param + redirect cleanup
- <https://github.com/antonio-orionus/url-sanitize> — ClearURLs-compatible tracking-param and redirect-wrapper stripper
- <https://en.wikipedia.org/wiki/UTM_parameters> — canonical UTM parameter list

---

## 9. Caveats and unverified points

1. **The bundled `claude-api` skill's model table (cached 2026-06-04) is stale** — it omits
   Opus 5 and Sonnet 5 and presents Opus 4.8 / Sonnet 4.6 as current. Everything in §1 of
   this file comes from a live fetch of platform.claude.com on 2026-08-24. If any future
   session quotes Opus 4.8 as "latest", re-verify.
2. **One web-search result was wrong.** A search summary claimed Opus 5 = $2.50/$12.50 —
   that is the **Batch** price, not the standard price. The docs table says $5/$25 standard.
   Trust the fetched pricing table, not search snippets.
3. **`AsyncAnthropic.messages.parse()` is unverified.** The docs show `messages.parse()` on
   the sync client. Use `output_config` + explicit Pydantic validation (§6) which is
   confirmed for both clients.
4. **Structured outputs × Batch API compatibility is not explicitly documented.** The
   structured-outputs page does not state it either way. Since I recommend skipping Batch
   for v1, this is moot — but test it before combining them.
5. **Refusal behaviour under structured outputs is under-documented.** The docs note a
   refusal "may not match your schema" but don't specify the payload shape on Sonnet 5 /
   Haiku 4.5. Guard on `stop_reason` defensively.
6. **All cost figures are estimates built on assumed token counts** (250 tok/item triage,
   600 tok/item summarise). Real RSS descriptions vary 5× in length. Re-baseline with
   `client.messages.count_tokens()` against `claude-haiku-4-5` and `claude-sonnet-5` on a
   week of real feed data before trusting the monthly number. The new-tokenizer +30%
   inflation is applied but is content-dependent.
7. **Cosine thresholds (0.55 for same-story, 0.90 for near-dup) and SimHash Hamming ≤ 3 are
   starting points from the literature, not tuned for GTA 6 news.** They must be calibrated
   against a hand-labelled sample of ~100 real item pairs. Log every clustering decision
   with its score from day one so you can tune retroactively.
8. **The "heuristics kill ~60% of items" figure is an estimate**, not measured. It drives
   the survivor counts in the cost model. If heuristics only kill 30%, triage cost roughly
   doubles (still under $10/month).
9. **The ACM near-duplicate news benchmark paper is paywalled** (403). Its method
   comparison is reported here from the search abstract only; I did not read the results
   tables or reproduce its precision/recall numbers.
10. **Voyage pricing was read from `docs.voyageai.com`** on 2026-08-24; the `voyage-4`
    generation carries a 200M free-token allowance while the `voyage-3.x` generation does
    not. Third-party price pages disagreed with each other — the vendor docs page is the
    one cited here.
