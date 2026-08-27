# Discord setup

Follow top to bottom. **Part A** gets the bot posting. **Parts B–D** are the
hardening that matters for a GTA 6 server specifically. Every number here was
verified against `docs.discord.com/developers` on 2026-08-26; the ones that
could not be verified are listed honestly in the last section.

Steps marked **UI ONLY** cannot be automated — Discord requires a human.

---

## Part A — get it posting (~10 minutes)

### A1. Create the application — **UI ONLY**

<https://discord.com/developers/applications> → New Application.

1. Copy the **Application ID** → this is your `DISCORD_CLIENT_ID` (not secret).
2. **Bot** tab → Reset Token → copy → `DISCORD_BOT_TOKEN` (secret, never commit).
3. Set the three privileged intents to **OFF**:
   - Presence Intent — OFF
   - Server Members Intent — OFF
   - Message Content Intent — OFF

Intents are only ever sent in a gateway IDENTIFY payload. This bot never opens a
websocket, so all three stay off **permanently**. Neither the 100-server
verification gate nor the 10,000-user intent-review gate applies to it.

### A2. Invite the bot — **UI ONLY** (a human must click Authorize)

```
python -m src.main invite-url --client-id YOUR_APPLICATION_ID
```

That prints the URL with the permission integer **19488**:

```
   1024   VIEW_CHANNEL     (1 << 10)
+  2048   SEND_MESSAGES    (1 << 11)
+ 16384   EMBED_LINKS      (1 << 14)   without this the embed is silently dropped
+    32   MANAGE_GUILD     (1 << 5)    AutoMod rules; no narrower bit exists
= 19488
```

**What is deliberately NOT in it:**

| Permission | Why not |
|---|---|
| `ADMINISTRATOR` (8) | Overrides every channel overwrite and defeats the whole design. Never. |
| `MENTION_EVERYONE` (131072) | Granted **per-channel** in step B3 instead, not guild-wide. |
| `MANAGE_MESSAGES` (8192) | Not needed to post, nor to publish your own message. |
| `MANAGE_WEBHOOKS` (536870912) | We use a bot token and the Create Message endpoint. |
| `ATTACH_FILES` (32768) | Embeds reference images by URL; the bot never uploads a file. |

One honest warning: **`MANAGE_GUILD` is guild-wide and cannot be narrowed by a
channel overwrite.** It also carries server settings, invites and integrations.
It is here only so the bot can manage AutoMod rules — there is no AutoMod-only
permission. If you would rather configure AutoMod by hand in the UI, use
`python -m src.main invite-url --no-automod` and the integer drops to **19456**.

### A3. Collect IDs — **UI ONLY**

User Settings → Advanced → **Developer Mode = ON**, then right-click to copy:

- the server → `GUILD_ID`
- `#news` → `DISCORD_NEWS_CHANNEL_ID`
- the bot in the member list → `BOT_USER_ID`
  *(copy it — do not assume it equals the Application ID; that was not
  documented either way)*

### A4. Fill in `.env` and verify

```ini
DISCORD_CLIENT_ID=...
DISCORD_BOT_TOKEN=...
DISCORD_NEWS_CHANNEL_ID=...
POSTING_ENABLED=false
```

```bash
python -m src.main discord-doctor
```

This asks Discord directly and names the exact missing permission. It computes
the bot's *effective* channel permissions using Discord's documented resolution
order, so it catches the most common failure: a correct invite integer defeated
by a channel overwrite.

Then, once it is clean:

```bash
python -m src.main post-test --yes
```

If that lands, set `POSTING_ENABLED=true` when you are ready to go live.

---

## Part B — the opt-in alert role

### B1. Create the role — **UI ONLY**

Server Settings → Roles → new role, e.g. `GTA6 Alerts`, with **zero
permissions**. Copy its ID into `DISCORD_NEWS_ROLE_ID`.

### B2. Leave it **NOT mentionable**

Do **not** enable "Allow anyone to @mention this role".

### B3. Allow the bot to mention it, in `#news` only

Channel `#news` → Permissions → add the **bot** (member, not role) and allow
`Mention @everyone, @here and All Roles`.

A channel overwrite can grant a permission the bot's role does not have, which
is the whole point: the role stays unmentionable by members *everywhere*, while
the bot can ping it in one channel. The alternative — making the role
mentionable so the bot needs no extra permission — works, but then any member
can ping every subscriber.

### B4. Fire exactly one real alert and check a second account

**Do not skip this.** If the role is non-mentionable and the bot lacks
`MENTION_EVERYONE`, the request **succeeds with HTTP 200**, the `<@&ID>` text
appears in the channel, and **nobody is notified**. No error, nothing in the
logs. `discord-doctor` checks for exactly this combination and will fail loudly:

```
FAIL ping role  @GTA6 Alerts is non-mentionable and the bot lacks
                MENTION_EVERYONE, so instant-alert pings will silently not notify
```

### B5. How members opt in

Use **Community Onboarding prompts** (Part D3). Discord's backend assigns the
role at join time, so it works while your PC is off.

Do **not** use a reaction-role bot. It needs a live gateway connection to
receive `MESSAGE_REACTION_ADD`; this bot has none, and any reaction added while
your PC is off is lost permanently with no backfill.

---

## Part C — lock down `#news`

Channel `#news` → Permissions.

**@everyone** — allow `66560`, deny `377957124096`:

| Allow | |
|---|---|
| View Channel | 1024 |
| Read Message History | 65536 |

| Deny | |
|---|---|
| Send Messages | 2048 |
| Create Public Threads | 34359738368 |
| Create Private Threads | 68719476736 |
| Send Messages in Threads | 274877906944 |

Denying Send Messages implicitly neutralises Embed Links, Attach Files and
Mention Everyone in that channel — but **`SEND_MESSAGES` is not inherited by
threads.** Without those three thread bits, a member can drop a leaked clip into
a thread hanging off the bot's own digest post.

**The bot** (member overwrite) — allow `216064`: View Channel, Send Messages,
Embed Links, Read Message History, Mention Everyone. A member overwrite is the
highest-precedence allow layer, so it survives any role deny and any position in
the role hierarchy.

> **Permission-sync footgun:** if `#news` has overwrites identical to its
> category it stays "synced", and a later category edit silently overwrites your
> lockdown. Applying the above de-syncs it — which is what you want — but note
> that editing the category afterwards will *not* re-lock `#news`, and any new
> channel created in a public category inherits that category's permissive
> overwrites.

---

## Part D — hardening that actually matters here

### D1. Deny media server-wide — the single most important control

**AutoMod cannot scan attachments, images, or video at all.** The real threat is
someone dragging in an `.mp4`, which is invisible to every keyword rule you can
write. So the highest-leverage control is a permission, not a rule.

Server Settings → Roles → **@everyone** → turn **off**:

- Embed Links (16384)
- Attach Files (32768)

What this costs normal members: no image/file/video uploads anywhere, and pasted
links render as bare text with no preview card. Custom emoji and GIF picker are
unaffected.

Re-grant it in exactly one moderated channel with a channel-level allow of
`49152`, or scope it to a trusted role.

### D2. AutoMod rules

You get **6 KEYWORD rules** per server, plus one each of Spam, Keyword Preset,
Mention Spam and Member Profile. Max **100 keywords per rule**; `custom_message`
max **150 characters**.

Ready-to-paste keyword lists are in
[`research/discord-delivery.md` §11](research/discord-delivery.md) — five rules
covering file hosts (~48 domains), video mirrors and link shorteners, trade
solicitation, obfuscation regexes, and one deliberately **alert-only** chatter
rule.

The tiering principle matters: **hard-block the vector, only alert on the
chatter.** "Rockstar responded to the leaked footage" is a sentence your members
will legitimately write — blocking it pushes real conversation into DMs where you
have zero visibility.

Two things to know:

- **Bots and webhooks are exempt from AutoMod and it cannot be turned on.** Your
  digest will never be filtered — but neither will any *other* bot's posts. Good
  argument for adding zero third-party bots.
- **`MEMBER_PROFILE` rules are widely skipped and genuinely useful here** — leak
  sellers advertise in display names and bios, which sidesteps every message rule.
- If a rule uses the **Timeout** action, the bot may additionally need
  `MODERATE_MEMBERS` (1099511627776). Not needed for block-and-alert rules.

### D3. Community Onboarding

Requires Community enabled first (**ADMINISTRATOR** — the bot cannot do this).
Desktop only; cannot be configured on mobile.

Hard requirements: **7 default channels, at least 5 of which let @everyone send
messages.** So exactly **2 read-only slots** — use them for `#news` and `#rules`.

The useful insight: **the quota only checks `SEND_MESSAGES`.** It does not care
about Attach Files or Embed Links. So you can satisfy onboarding with 5 chatty
channels while still denying media in all of them (per D1). A locked-down server
and onboarding are not in conflict.

Onboarding prompt options can assign your `GTA6 Alerts` role directly —
server-side, no bot involved.

### D4. Skip announcement channels for now

Keep `#news` a plain text channel.

Publishing exists only to push a message to *other servers that pressed Follow*.
With zero followers it is a no-op that burns one of your 10-per-hour publishes,
and **it does not re-notify members of your own server** — they already got the
message. Convert later only if other servers actually want to follow you.

Also: granting Send Messages in an announcement channel lets members publish
their own messages, and Manage Messages lets them publish *anyone's*.

### D5. Slow mode

**Slow mode does not apply to bots** — unconditionally exempt, no permission
needed. So it is pointless in `#news` (where nobody else can post anyway); put it
on the 5 writable onboarding channels instead. Range 0–21600 seconds.

---

## Verify yourself before relying on it

These could not be confirmed from primary docs. None block Part A.

1. **Whether a bot's user ID always equals its Application ID.** True in current
   practice but undocumented — copy the bot's user ID by right-clicking it.
2. **Scope of the "10 publishes per hour" limit** (per channel? per guild?).
   Discord's FAQ gives no scope and the API rate-limit page omits crossposting
   entirely. Moot if you follow D4.
3. **Whether slow mode can be set on an announcement channel.** The docs omit
   Announcement from that field's channel-type list while listing it for
   neighbouring fields — a strong hint, not a statement.
4. **Whether enabling Community automatically grants the `NEWS` feature.** They
   appear together everywhere but no doc says so explicitly.
5. **Whether announcement/forum/voice channels count as valid onboarding default
   channels.** Only plain text channels were confirmed.
6. **Whether AutoMod works on non-Community servers.** A support page says
   "available for all servers"; the developer docs never restate it.
7. **`USE_EXTERNAL_APPS` in a locked channel** — the docs say denying it makes
   user-installed app responses ephemeral rather than blocking them, so including
   it in a deny mask may not fully stop a member invoking their own app.

Two stale-advice warnings, both already in force:

- **`PIN_MESSAGES` (1 << 51) was split from `MANAGE_MESSAGES`**, effective
  2026-02-23. Every blog post saying "Manage Messages is enough to pin" is now
  wrong. Grant it explicitly if you want the bot to pin the digest.
- **`BYPASS_SLOWMODE` (1 << 52)** was likewise split out of `MANAGE_MESSAGES` /
  `MANAGE_CHANNEL` / `MANAGE_THREADS` on the same date.

And one dated change to keep in mind: **from 2026-11-16, channels will be
obfuscated from bots lacking `VIEW_CHANNEL`**, and omitted from Get Guild
Channels entirely. `VIEW_CHANNEL` is already in the invite integer, so you are
covered — but do not remove it.
