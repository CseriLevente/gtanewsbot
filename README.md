# gta6-news-bot

Posts a curated daily GTA 6 news digest to a Discord channel, plus instant alerts
for first-party Rockstar/Take-Two news. English only. Runs on Windows from Task
Scheduler.

Built for a GTA 5 → GTA 6 roleplay community. The editorial rule is deliberate
and enforced in code, not by discipline:

> We may describe what a leak **claims**, labelled as rumour. We never link to,
> embed, or reupload leaked material, and every claim is attributed to the
> journalism that reported it — never to the leak itself.

## Why that rule matters right now

As of August 2026 Take-Two is running a DMCA §512(h) subpoena campaign demanding
identifying data for **every account that communicated** in named Discord servers
connected to GTA 6 leaks — including at least one server that hosted no leaked
clips at all. No lawsuits: the goal is identification.

**Your exposure is driven by who joins your server and what they paste, not by
what this bot posts.** Server moderation matters more than anything in this repo.
See `research/legal-risk.md` and `research/discord-delivery.md` §AutoMod.

Hungarian copyright supports the rule directly — Szjt. Art. 1(5): copyright does
not extend to facts and daily news. Describing a leak reproduces no protected
expression.

## Status

Milestone 1 is complete: polling, dedup, credibility tiering, digest rendering,
scheduling, and a dry-run preview. **No LLM summarisation yet** — digest lines are
headline + source + link. Milestone 2 adds Claude summaries.

## Quick start

```bash
pip install -r requirements.txt          # feedparser is the only new dependency
cp .env.example .env                     # then edit it
python -m src.main init-db                # create the DB, register feeds
python -m src.main check-ready             # verify config; exits 1 on problems
python -m src.main run --dry-run           # poll + preview, posts nothing
```

Nothing is ever posted until you set `POSTING_ENABLED=true` in `.env`. Until
then every command behaves as a dry run, regardless of flags.

### Going live

Follow **[SETUP-DISCORD.md](SETUP-DISCORD.md)** — it has the verified permission
integer (`19488`), the channel overwrite masks, the AutoMod plan, and an honest
list of what could not be verified. Short version:

1. `python -m src.main invite-url --client-id YOUR_APP_ID` → open the URL.
2. Fill `DISCORD_BOT_TOKEN` and `DISCORD_NEWS_CHANNEL_ID` in `.env`.
3. `python -m src.main discord-doctor` → fix anything it reports.
4. `python -m src.main post-test --yes` → confirm a real message lands.
5. `python -m src.main run --dry-run` for a few days and read the output.
6. Set `POSTING_ENABLED=true`.

## Commands

| Command | What it does |
|---|---|
| `init-db` | Create the database and register feeds from config |
| `poll` | Fetch all feeds and ingest new items |
| `run` | Full cycle: poll → instant alerts → digest if due. **Task Scheduler entry point** |
| `run --dry-run` | Same, printing instead of posting |
| `digest --dry-run --no-poll` | Preview today's digest from stored items |
| `digest --force` | Post now, ignoring the hour and the once-a-day guard |
| `status` | Feed health, item counts, digest history, clock |
| `check-ready` | Verify configuration; non-zero exit on problems |
| `list-sources` | Show the source registry and tier map |
| `items --state new -v` | Inspect stored items and why they were tiered that way |
| `clear-kill-switch` | Re-enable posting after a Discord auth failure |
| `prune --dry-run` | Expire stale held/unsent items and delete old rows |
| `invite-url` | Show the least-privilege permission maths and the bot invite URL |
| `discord-doctor` | Ask Discord what is actually configured and name what is wrong |
| `post-test --yes` | Post one harmless test message to the news channel |

## How it decides what to post

```
feed → canonicalise URL → dedup → tier → leak check → decision
```

* **Tier 1** (Rockstar, Take-Two) → post as fact, may trigger an instant alert.
* **Tier 2** (VGC, PC Gamer, GameSpot, Kotaku, Bloomberg…) → post as a report.
* **Tier 3** (RockstarINTEL, GTABase…) → held until 1 tier-2 outlet confirms.
* **Tier 4** (unknown domains, social) → held until **2 independent** tier-2
  outlets confirm, then attributed to those outlets — never to the tier-4 origin.
* **Tier 5** (documented fabricators, parasite-SEO domains) → dropped outright.

Two hard rules on top:

* **Leak-derived content is capped at "Rumour" permanently**, at every tier
  including tier 1. Rockstar acknowledging that a leak exists does not confirm
  what the leak claims.
* Items contradicting established fact (a 2027 delay, a Switch 2 port, a
  confirmed PC version) are **dropped**, because those are the perennial fakes.
  The baseline lives in `config/sources.json` → `factual_baseline` and must be
  updated after each real announcement.

## Scheduling

Task Scheduler runs `run` every 15 minutes; the bot decides whether to post. All
timing lives in `src/clock.py`.

```bash
schtasks /create /tn "gta6-news-bot" /xml infra\gta6-news-bot-task.xml
```

Edit the `<Command>`, `<WorkingDirectory>` and `<UserId>` in that file first.

Three things that will otherwise cost you an evening:

* **Never use a One Time trigger.** Per MS KB 2437520, "run as soon as possible
  after a missed start" *"does not occur if the task is set to run One Time. This
  behavior is by design."* The XML uses Daily + `PT15M` repetition.
* **Enable Task Scheduler History** — it is off by default, and without it a
  failing task is invisible.
* `0x41301` means *running* and `0x41303` means *never run*. Neither is an error.

### Why 18:00, and why no tzdata

This machine has no `tzdata`, so `ZoneInfo("Europe/Budapest")` raises. The system
clock **is** Budapest, so plain `datetime.now()` is the single clock — the same
approach as tozsdeturbo-bot. Do not add tzdata.

Hungary's DST transitions happen between 02:00 and 03:00, so **18:00 local exists
exactly once on every day of the year**. "Post once per local date, at or after
18:00", backed by a `UNIQUE` constraint on the date, therefore cannot double-post
or skip a day. That argument is load-bearing, and `check-ready` rejects a
`DIGEST_HOUR` of 2 or 3 because it collapses there. `tests/test_clock.py` pins it
against the 2026-10-25 and 2027-03-28 transitions.

The real hazard is elsewhere: `utcoffset()` is +02:00 today and +01:00 from
2026-10-25. Never hardcode `timezone(timedelta(hours=2))`. Naive local time is
used *only* for the date key and the `hour >= N` test; everything else uses epoch
seconds.

## Known limitations

* **`rockstargames.com` cannot be polled.** Cloudflare decides the 403 from the
  TLS ClientHello fingerprint before headers are read, so no User-Agent fixes it
  (a Chrome UA makes it worse). `curl_cffi` would defeat it; we deliberately do
  not, because that circumvents an access control the owner enabled and
  Rockstar's ToS prohibits automated access. The feed is shipped disabled and a
  Google News `site:` query is used instead.
* Three feeds are marked `untested` in config — `check-ready` warns about them.
* LLM curation exists (`src/llm.py`) but is OFF by default and has never been
  called live — set `LLM_CURATION_ENABLED=true` and `ANTHROPIC_API_KEY`. Any
  failure falls back to heuristic clustering, so the digest still posts.
* No retraction-following yet (milestone 2). This matters: two outlets retracted
  GTA 6 claims in one week in August 2026.

## Layout

```
config/sources.json    feeds, domain tiers, blocklists, factual baseline
src/clock.py           the single clock + DST-safe digest decision
src/canonical.py       URL canonicalisation, redirect resolution, title hashing
src/credibility.py     tiering, relevance, the post/label/hold/drop decision
src/feeds.py           polling, conditional GETs, dead-feed detection
src/digest.py          embed rendering + hard limit enforcement
src/discord_client.py  REST posting, kill switch, dry-run preview
src/runner.py          orchestration + the instant/digest interlock
src/console.py         cp1250-safe console output
research/              ~6000 lines of source research (read legal-risk.md)
infra/                 Task Scheduler XML
```

## Tests

```bash
python -m pytest tests/ -q      # 205 tests
```

The ones worth knowing about:

* `test_clock.py` — DST safety across both 2026/2027 transitions.
* `test_credibility.py::test_leak_derived_is_capped_at_rumour_even_from_tier_1`
  — if this ever fails, the bot has started asserting leaks as fact.
* `test_digest.py` — the 6000-char budget and the `@everyone` guard. Bot messages
  (unlike webhooks) default to parsing **everything including @everyone**, so
  every payload must carry an explicit `allowed_mentions` block.
* `test_storage.py` — once-per-day idempotency and the instant/digest interlock.
