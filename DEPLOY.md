# Running this on a server

The bot is a **short-lived process run on a schedule**. There is no daemon, no
web server, no open port. Something wakes it every 15 minutes; it polls, decides
whether anything is due, posts, and exits. Every decision it makes lives in
SQLite, because nothing survives in memory between runs.

That design is what makes it portable: you need Python, a scheduler, and a
writable directory.

---

## The one thing that will catch you out

**The bot uses the server's local system time as its only clock.** There is no
timezone configuration, deliberately — see [`src/clock.py`](src/clock.py).

So `DIGEST_HOUR=18` means 18:00 *on the server*. A server sitting in UTC posts
your digest at 20:00 Budapest time in summer and 19:00 in winter.

Fix it at the machine level, not in the app:

```bash
sudo timedatectl set-timezone Europe/Budapest
timedatectl                      # confirm
```

On Windows Server, set the timezone in Settings and confirm with `tzutil /g`.

Why the app doesn't handle this: 18:00 local exists exactly once on every day of
the year in Hungary (DST shifts happen at 02:00–03:00), which is what makes
"post once per local date, at or after 18:00" provably safe against
double-posting and skipping. Introducing a second clock would give that up. If
your server genuinely must stay on UTC, set `DIGEST_HOUR` to the UTC hour you
want and accept that it drifts by an hour across DST.

---

## Linux (recommended)

### 1. Install

```bash
sudo apt install -y python3 python3-venv git
git clone <your-repo-url> gta6-news-bot
cd gta6-news-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
$EDITOR .env
```

Minimum to post: `DISCORD_BOT_TOKEN`, `DISCORD_NEWS_CHANNEL_ID`,
`POSTING_ENABLED=true`. Add `DISCORD_NEWS_ROLE_ID` for instant-alert pings.

```bash
chmod 600 .env        # it holds a live bot token
.venv/bin/python -m src.main check-ready
```

`check-ready` exits non-zero and tells you what is missing. Fix everything it
reports before enabling posting.

### 3. Initialise and rehearse

```bash
.venv/bin/python -m src.main init-db
.venv/bin/python -m src.main run --dry-run
```

Read that output. It prints what it *would* post. Leave
`POSTING_ENABLED=false` for a day or two first — every command behaves as a dry
run while it is false, regardless of flags.

### 4. Schedule it

systemd timer, in preference to cron, because the journal gives you the run
history that a home-grown cron redirect does not.

`/etc/systemd/system/gta6-news-bot.service`:

```ini
[Unit]
Description=GTA 6 news digest bot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=gta6
WorkingDirectory=/opt/gta6-news-bot
ExecStart=/opt/gta6-news-bot/.venv/bin/python -m src.main run
# The bot writes only to its state dir and its own logs.
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/gta6-news-bot/logs /home/gta6/.local/state
```

`/etc/systemd/system/gta6-news-bot.timer`:

```ini
[Unit]
Description=Run the GTA 6 news bot every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
# Catch up after downtime instead of silently skipping the window.
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gta6-news-bot.timer
systemctl list-timers gta6-news-bot.timer
journalctl -u gta6-news-bot -n 50 --no-pager
```

`Persistent=true` matters: if the server is down at 18:00, the timer fires on
the next boot and the bot's own catch-up logic posts the missed digest once —
not once per missed interval.

### Where state lives

`%LOCALAPPDATA%` on Windows, `$XDG_STATE_HOME` or `~/.local/state` on Linux —
so `/home/gta6/.local/state/gta6-news-bot/bot.db`. Override with `GTA6_DB_PATH`.

The database refuses to open inside a cloud-synced folder (OneDrive, Dropbox,
Google Drive). That is not paranoia: those tools sync `bot.db` and its journal
as independent files, and a restore that pairs a stale database with a newer
journal is corrupt by definition. Keep the DB off synced storage even if the
code lives there.

Back up `bot.db` if you care about the "already posted" history. Losing it does
not cause duplicate posts — the duplicate guards ask Discord, not the database —
but you lose the dedup window, so recently-seen stories can reappear once.

---

## Windows

```powershell
git clone <your-repo-url> gta6-news-bot
cd gta6-news-bot
pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m src.main check-ready
python -m src.main init-db
python -m src.main run --dry-run
```

Then generate and register the scheduled task:

```powershell
python -m src.main make-task
schtasks /create /tn "gta6-news-bot" /xml infra\gta6-news-bot-task.xml /f
```

`make-task` fills in this machine's Python path, account and project directory,
and writes the file as **UTF-16 with a BOM**. Both details are load-bearing:

- the committed template carries placeholders, because a real task file contains
  your hostname, username and absolute paths;
- the XML declares `encoding="UTF-16"` and Task Scheduler believes it. Saved as
  UTF-8, any non-ASCII character in your path is misdecoded, the task stores a
  working directory that does not exist, and every run dies instantly with
  `0x8007010B` — *"the directory name is invalid"*.

Run `schtasks` from **PowerShell, not Git Bash** — Bash rewrites `/tn` as a
filesystem path.

Checking it afterwards:

| Last Run Result | Meaning |
|---|---|
| `0` | success |
| `1` | ran, but reported problems — read `logs/bot.log` |
| `2` | crashed — the traceback is in `logs/bot.log` |
| `0x8007010B` | working directory is wrong; re-run `make-task` |
| `0x41301` | currently running (not an error) |
| `0x41303` | has never run (not an error) |

**Enable Task Scheduler History** — it is off by default, and without it a
failing task is invisible.

### A Windows caveat worth knowing

On the machine this was developed on, commits made by the Task Scheduler process
never reached the shared database, while identical code run from an interactive
shell persisted normally. The scheduled process could read back its own writes,
so it looked healthy from the inside. Root cause was never identified; an
endpoint-security write-shadow for non-interactive processes is the leading
suspect on managed Windows Enterprise machines.

The bot is built to survive it — both duplicate guards ask Discord rather than
trusting local state — but if you see `status` disagreeing with what is actually
in your channel, this is why. It has not been observed on Linux.

---

## Verifying a fresh install

```bash
python -m src.main check-ready       # config audit, non-zero exit on problems
python -m src.main discord-doctor    # asks Discord what is really configured
python -m src.main post-test --yes   # one harmless message
python -m pytest tests/ -q           # 221 tests, no network needed
```

`discord-doctor` is the one that catches the subtle mistakes: it computes the
bot's *effective* channel permissions using Discord's documented resolution
order, so it spots a correct invite integer defeated by a channel overwrite, and
it rejects a managed integration role being used as the ping target (Discord
auto-creates one named after your bot, humans cannot hold it, and pinging it
notifies nobody without raising an error).

## The web edition

The bot also publishes every story as a static page, not just the eight the
Discord embed has room for. That pairing is why the digest could drop its
"+N more not shown" line: nothing is hidden, it just lives on the page.

```bash
python -m src.main build-web            # regenerate web/index.html
python -m src.main build-web --deploy   # and publish it
```

`web/index.html` is one self-contained file (the only external request is Google
Fonts), so any static host serves it. The deploy step is config rather than
code -- set `WEB_DEPLOY_CMD` in `.env`:

```bash
# Both hosts at once -- what this deployment uses.
WEB_DEPLOY_CMD=python tools/publish_web.py

# ...or a single host:
WEB_DEPLOY_CMD=python tools/deploy_pages.py                    # GitHub Pages
WEB_DEPLOY_CMD=npx --yes wrangler@latest pages deploy web --project-name=gta6-news --commit-dirty=true
WEB_DEPLOY_CMD=rsync -az web/ user@host:/var/www/gta6/         # your own nginx
```

### Why two hosts

Live at both:

| Host | URL | Role |
|---|---|---|
| Cloudflare Pages | `https://gta6-news.pages.dev/` | linked by the digest |
| GitHub Pages | `https://cserilevente.github.io/gtanewsbot/` | standby |

`tools/publish_web.py` attempts every target independently and succeeds if **at
least one** published. Chaining the two in a shell with `&&` would get both of
those wrong: a failed first deploy would skip the second, and a failed standby
would fail the whole run.

The standby earns its keep because the Cloudflare credential is an OAuth token
on a machine nobody logs into. When it eventually expires, the nightly deploy
starts failing silently -- and without a second host, the URL posted to Discord
every evening would rot. A partial failure is reported on stderr naming the
target, so it shows up in `logs/bot.log` rather than being discovered months
later.

Note that `gta6-news.pages.dev` returns **403 to non-browser user agents**
(Cloudflare bot filtering). That is expected and affects nothing real, but a
health check written with `urllib` will look like an outage; send a browser
user agent.

Then set `DIGEST_WEB_URL` so the digest links to it -- but **only after opening
that URL in a logged-out browser**. A link your members cannot open is worse
than no link. This bit us once already: an earlier version pointed at a Claude
artifact URL, which is private and auth-gated, so the link simply did nothing
for everyone but the author.

### How the daily republish works

`run` refreshes the page **only after the digest has actually posted** -- once a
day, not on every 15-minute cycle. The page's own "compiled <time>" line is a
daily statement, and force-pushing a branch 96 times a day is noise in the repo
and in any CDN in front of it.

Publishing is wrapped so it can never fail the run. The digest is the product;
the page is a convenience. A deploy that dies because the network dropped
records `Web edition: not published - <reason>` in the log and the run still
counts as successful.

### About `tools/deploy_pages.py`

It builds the commit with git plumbing (`hash-object`, `mktree`, `commit-tree`)
and moves the ref directly, so nothing is ever checked out: the deploy cannot
disturb your working tree or current branch, and is safe to run mid-edit.

Each deploy is a fresh **orphan** commit that force-replaces `gh-pages`, so that
branch holds exactly one commit. Keeping history would add a ~170KB blob per day
to a repo otherwise under a megabyte, for old versions of a page nobody will
read. If the page is byte-identical to what is already published, it skips the
push entirely.

It sets `GIT_TERMINAL_PROMPT=0`, so expired credentials fail immediately with a
readable error instead of blocking forever on a prompt that, under Task
Scheduler, no one can see -- where a hung push is indistinguishable from a slow
one until the task time limit kills it.

Pushing a `gh-pages` branch to a public repo enabled Pages automatically here,
with no click in Settings. If that does not happen for you, set
**Settings -> Pages -> Source** to "Deploy from a branch", branch `gh-pages`,
folder `/ (root)`.

### A caveat about the links on that page

Most stories reach the bot through Google News, whose RSS links are opaque
redirects rather than publisher URLs -- and post-2024 they cannot be decoded
(measured: 0 of 8 sample URLs contain a recoverable address). Following the
redirect lands on `consent.google.com` from the EU, so a reader without Google
consent cookies hits a consent wall instead of the article.

Those chips are marked with an arrow and the footer says so. Only about 28% of
stories currently carry a link straight to the publisher.

The fix is more direct RSS feeds in `config/sources.json`, and the returns were
measured: **+10 feeds takes story-level link coverage from 28% to 68%**, +15
reaches 74%, and it flattens out around 86%. The tail is long -- 114 distinct
publishers -- so chasing the last 15% is not worth it. Highest-value feeds to
add, by volume: Mashable, Kotaku, IGN, TweakTown, Polygon, SVG, eGamers,
Notebookcheck, GTABoom, DualShockers.

## Upgrading

```bash
git pull
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.main check-ready
sudo systemctl restart gta6-news-bot.timer     # Linux
```

The schema is created with `CREATE TABLE IF NOT EXISTS` and new columns are
added idempotently, so an existing database is picked up as-is.

## If something goes wrong

```bash
python -m src.main status        # feeds, item states, digest history, clock
python -m src.main items -v      # what was ingested and why it was tiered so
tail -50 logs/bot.log
```

A Discord `401`/`403` latches a **persisted kill switch** and stops all posting
until you clear it deliberately:

```bash
python -m src.main clear-kill-switch
```

That is not over-caution. Retrying auth failures burns Discord's
invalid-request budget, and 10,000 in ten minutes earns a Cloudflare IP ban —
which on a shared connection takes everyone on it off Discord.
