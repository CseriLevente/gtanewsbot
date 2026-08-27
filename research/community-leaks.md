# GTA 6 News Bot — Source Credibility Tier List & Fabrication Detection

**Compiled:** 2026-08-25
**Purpose:** config input for a Discord daily-digest bot serving a GTA roleplay community.
**Editorial rule this document serves:** leaks may be described as *rumour*, attributed to the journalism that reported them. Never link, embed, or reupload leaked material.

> **Confidence labels used throughout:** `[HIGH]` = multiple independent reputable outlets or a first-party document. `[MED]` = one reputable outlet, or several low-tier outlets agreeing. `[LOW]` = single low-tier source, or inference. `[UNVERIFIED]` = could not confirm; do not act on. Entities I could not evidence are marked **unrated** rather than guessed.

---

## 1. FACTUAL BASELINE (as of 2026-08-25)

This is the bot's ground truth. Any claim contradicting the "TRUE" block from a non-Tier-1 source should be auto-dropped.

### 1.1 Confirmed true

| Fact | Detail | Confidence |
|---|---|---|
| Release date | **Thursday, 19 November 2026** | `[HIGH]` |
| Announced by | Rockstar Newswire, 6 Nov 2025 (second delay) | `[HIGH]` |
| Launch platforms | **PlayStation 5 and Xbox Series X\|S only** | `[HIGH]` |
| Setting | State of **Leonida**; **Vice City** | `[HIGH]` |
| Protagonists | **Jason** and **Lucia** (dual protagonists) | `[HIGH]` |
| Official framing | Marketed as "**a single player experience**" in Rockstar Newswire copy and PS/Xbox store listings | `[MED]` |
| Pre-orders | Opened **25 June 2026** (PlayStation Store, Microsoft Store, Rockstar Store, retail) | `[MED]` |
| Pricing (US) | $79.99 Standard / $99.99 Ultimate | `[MED]` |
| Preload | From local midnight **12 Nov 2026** for eligible digital pre-orders | `[LOW]` — aggregator-sourced, verify against Newswire |
| Unlock time | 12:00 AM local time, 19 Nov 2026 | `[LOW]` — aggregator-sourced |
| **"GTA VI: An Extended Look"** | Netflix **27 Aug 2026, 3:00 PM ET**; then Rockstar YouTube + official GTA VI site **9:00 PM ET** same day | `[HIGH]` |
| Extended Look runtime | **NOT announced.** BBC's "30-minute special" claim was walked back | `[HIGH]` |
| Delay history | Announced for 2025 → 2 May 2025 delayed to 26 May 2026 → 6 Nov 2025 delayed to 19 Nov 2026. **Two official delays, both announced by Rockstar itself.** | `[HIGH]` |
| Press access | Rockstar had shown **no gameplay to press and run no preview events** as of 25 Aug 2026 | `[MED]` — Game File |
| Rockstar owns Cfx.re | Rockstar owns Cfx.re (FiveM / RedM) | `[HIGH]` |

### 1.2 NOT announced / currently FALSE — the contradiction blocklist

Any item asserting one of these as fact, from a non-Tier-1 source, is a **hard drop**.

| Claim | Reality | Confidence |
|---|---|---|
| "GTA 6 delayed to 2027" / "February 2027" | **FALSE.** Originated on 4chan, zero corroboration. Take-Two FY2027 net-bookings guidance and Zelnick's repeated public reaffirmations contradict it. | `[HIGH]` |
| "GTA 6 on Nintendo Switch 2" | **NEVER ANNOUNCED.** Viral claim traced to a satire mashup by **@DiscussingFish**; a separate source-claim attributed to **KiwiTalkz** was publicly disowned by KiwiTalkz himself. | `[HIGH]` |
| "GTA 6 PC confirmed" / "PC release date" | **NOT ANNOUNCED.** No date, no storefront, no system requirements. Any specific PC date (2027, 2028) is speculation. | `[HIGH]` |
| "GTA 6 Online / GTA Online 2 confirmed" | **NOT ANNOUNCED.** No mode, no date, no business model, no roadmap. | `[MED]` |
| "FiveM / RP / mod support confirmed for GTA 6" | **NOT ANNOUNCED.** Rockstar owning Cfx.re is *not* an announcement about GTA 6. Server frameworks require PC, which is also unannounced. **Directly relevant to this community — expect this fake constantly.** | `[HIGH]` |
| "Voice cast confirmed" | **NOT ANNOUNCED.** Manni L. Perez (Lucia) and Dylan Rourke (Jason) are *rumoured*. Roger Craig Smith and Troy Baker both publicly denied being Jason. Rockstar historically withholds cast until launch day (GTA V precedent). | `[HIGH]` |
| "CyberLeek dead man's switch / will drop full playable build" | **FABRICATED.** Built on a fake image. Insider Gaming published a full retraction. | `[HIGH]` |
| "Physical release delayed to 2027 to stop leaks" | **DENIED** by Take-Two. | `[MED]` |
| "No review copies confirmed" | Insider **claim** only, not confirmed. | `[LOW]` |
| Six-star wanted level, focus meter, morality system, etc. | **LEAK-DERIVED ONLY.** Rumour tier regardless of how many outlets describe it. | n/a |
| Leaked footage age | CyberLeek claims a **2023 build**; Nate the Hate claims **>1 year old**. Rockstar/Take-Two **declined to comment** on age or authenticity. Unresolved. | `[MED]` |

### 1.3 The three separate incidents — do not conflate

The bot will see these mixed together constantly. They are distinct events:

| Event | Date | What actually happened |
|---|---|---|
| **Lapsus$ / Kurtaj hack** | 18 Sep 2022 | "teapotuberhacker" posted **90+ files/videos** of in-development GTA 6 footage to **GTAForums**. Social-engineering of an employee Slack. Arion Kurtaj (Lapsus$) convicted Aug 2023, indefinite hospital order. As of 2026 he is out of hospital, in prison **awaiting retrial** (reported for November). This is the **only** GTA 6 leak with de-facto official verification. |
| **ShinyHunters breach** | Apr 2026 | Supply-chain attack: stolen **Anodot** auth tokens → Rockstar's **Snowflake** warehouse. Extortion listing 11 Apr, data published 14–15 Apr. Rockstar **confirmed a third-party data breach**. **No GTA 6 gameplay or source code confirmed stolen.** Zero Rockstar employees socially engineered, no creative content. `[HIGH]` on the breach; `[LOW]` on the "25 files / 7.54 GB" figure. |
| **CyberLeek wave** | 18 Aug 2026 → ongoing | 10+ gameplay clips + a full Leonida map screenshot, released daily. Watermarked with a manifesto **and memecoin solicitations**. Stated demands: offline modes, no fake single-player DLC, no pre-orders before independent review; protest framing around digital-only/code-in-box distribution. Rockstar issued DMCA takedowns and temporarily restricted its own official Discord. |

### 1.4 The legal exposure — why the editorial rule matters operationally

Take-Two sought DMCA **§512(h)** subpoenas (clerk-issued, no merits ruling required):

| Target | Scope | Firm |
|---|---|---|
| **Discord** | Identifying info for **every account that was a member of or communicated with three servers** — reported as `Ødyssey.gg`, `! Odyssey`, and `DarkViperAU` — from **1 Jun 2026 to present** `[MED]` on server names | Kirkland & Ellis |
| **Microsoft** | Windows **device IDs**, IP logs, OneDrive content | Kirkland & Ellis |
| **X Corp.** | `@cyberleek_ar_io`, `@cyberleekario`, `@MrCyberLeek` — account IDs, registration emails, IP logs, phone numbers, device identifiers. All three now suspended. **The GTA community had flagged all three as impostors before the filing.** | Ruttenberg IP Law |
| **Google / YouTube** | Channels `CyberLeeks`, `Surfer24k`, `Cyberleek_ar_io`; video reference `UNAUTH_2026AUG_VIDEO2` | Ruttenberg IP Law |

Judges signed orders directing the clerk to issue; issuance was still pending at time of reporting.

**Two operational consequences for this bot:**

1. The Discord subpoena swept in **everyone who was merely a member** of the named servers — not just uploaders. A Discord community whose bot reposts leaked media is squarely in that blast radius. The editorial rule is not just ethics, it is risk management.
2. **Take-Two sent a cease-and-desist over AI *recreations*.** The fan account **GTASixJoker** publicly apologised on **24 April 2026** after Take-Two lawyers argued its AI images were derivative works built on copyrighted Rockstar training material — and that they "risked confusing fans with real leaks." So even non-authentic imagery carries exposure. `[HIGH]`

**A vital nuance for tiering:** the three subpoenaed X handles were **impostors**, per community consensus reported by TorrentFreak. Even the apparent "primary source" handles in this wave were largely impersonators. There is no such thing as a trustworthy leaker handle here.

---

## 2. THE TIER LIST

### Tier 1 — First-party / official (post as FACT, no corroboration needed)

| Entity | Domain / handle | Justification |
|---|---|---|
| Rockstar Newswire | `rockstargames.com/newswire` | Sole authoritative channel. Both official delays (2 May 2025, 6 Nov 2025) and the Extended Look announcement originated here. |
| Rockstar Games site / GTA VI page | `rockstargames.com` | Official product facts, editions, platforms. |
| Rockstar Games on X | `@RockstarGames` | Verified first-party; posted the Extended Look announcement. |
| Rockstar Games YouTube | `youtube.com/@RockstarGames` | Official trailer/Extended Look distribution (9 PM ET, 27 Aug). |
| Rockstar Support | `support.rockstargames.com` | Authoritative on preload/unlock/technical. |
| Take-Two Interactive IR | `take2games.com` | Earnings releases, guidance. |
| Take-Two SEC filings | `sec.gov` (EDGAR, TTWO) | 10-K/10-Q list the release date. Strongest possible anti-delay-rumour evidence. |
| PlayStation Store / Microsoft Store listings | `store.playstation.com`, `xbox.com` | First-party retail metadata — the "single player experience" wording lives here. |
| Netflix Tudum (scoped) | `netflix.com/tudum` | Official distribution partner **for the Extended Look only**. Not Tier 1 for anything else. |

> Note: I could not verify Take-Two's current official X handle in this research — **left out rather than guessed.**

---

### Tier 2 — Reputable press with real editorial standards (post as FACT per corroboration rule)

| Outlet | Domain | Rockstar/GTA track record | Notable misses / caveats |
|---|---|---|---|
| **Bloomberg — Jason Schreier** | `bloomberg.com` | **Best in class.** Reported the 2026 delay and that Rockstar staff were not informed in advance. His earlier reporting (dual protagonists, Vice City setting) was corroborated years later by the Aug 2026 leak footage. Reportedly assesses the current leak as real. | **Split his output:** written Bloomberg articles = Tier 2. His **podcast/verbal remarks are routinely laundered into false headlines** — his "not content complete" comments were misconstrued into a delay story, which he publicly rejected as "a complete misunderstanding of what I said." Treat podcast quotes as Tier 3 and never as a delay signal. |
| **Game File — Stephen Totilo** | `gamefile.news` | Strong. "GTA VI's week of leaks" describes leaks **without linking**, reports the subpoena timeline accurately, notes Rockstar/Take-Two "did not reply to requests for comment." Landed a Zelnick interview. Ex-Kotaku EIC, ex-Axios. | Newsletter, partly paywalled — fetching may be limited. Small outlet, low volume. |
| **VGC** | `videogameschronicle.com` | Solid. Framed the Aug 2026 leak carefully as "allegedly leaks." Reported the 2022 Take-Two forum/subreddit cleanup. Real masthead. | No documented GTA-specific miss found in this research. |
| **PC Gamer** | `pcgamer.com` | Good. Published a 15-detail **analysis** of the Aug 2026 leak without hosting media; reported the Kurtaj retrial development; sourced a named former-Rockstar-dev quote on leak impact. | Analysis-of-leak pieces are still leak-derived — those specific *claims* stay rumour-tier even though the outlet is Tier 2. |
| **GameSpot** | `gamespot.com` | Good, with a **documented debunking record**: actively shot down the laundered Schreier delay rumour, reported the Microsoft/Discord subpoenas, and covered the 2022 GTAForums takedowns. | Fetch returns 403 — plan for RSS/search-based ingestion. |
| **Kotaku** | `kotaku.com` | Good on the **meta-story**: published "Real GTA 6 Leaks Are Hard To Spot In 2026 Due To All The AI Fakes" and the subpoena coverage; framed leaks as "seemingly"/"alleged." | Ownership/staffing has changed hands in recent years; fetch returns 403. Rate Tier 2 but re-check periodically. |
| **Engadget** | `engadget.com` | Good, and **the model citizen on handling**: explicitly refused to share or point to the material (see §6). Correctly hedged that clips "may not be entirely legitimate." | General-tech, not a GTA scoop source. |
| **Tom's Hardware** | `tomshardware.com` | Good on the legal/technical angle — reported the Microsoft device-ID subpoena accurately. | Not a games-news source; scope to hardware/legal. Fetch is JS-heavy. |
| **TorrentFreak** *(scoped)* | `torrentfreak.com` | **Excellent, and the single best source on this wave's legal dimension.** Primary-document reporting: named the exact handles, channels, servers, date ranges, and both law firms, and correctly noted the subpoenas were signed-but-not-yet-issued. | **Scope strictly to copyright/legal/DMCA.** Not a games-news outlet. |
| **Digital Foundry** *(scoped)* | `eurogamer.net/digitalfoundry`, `youtube.com/@DigitalFoundry` | Authoritative on **technical analysis only**: Trailer 2 breakdown (≈2560×1152 upscaled to 4K, 30fps), Linneman on hair-strand rendering and ray-traced GI. | Their **performance predictions** (720p on Series S, 30fps cap even on PS5 Pro) are informed speculation, not facts — Tier 3 for anything forward-looking. |
| **Eurogamer** | `eurogamer.net` | Tier 2 on general editorial standards. | **No GTA-specific scoop or miss found in this research.** Rated on standards, not on a GTA track record. Stated explicitly rather than implied. |
| **IGN** | `ign.com` | Tier 2 for news. Notably, IGN's pre-order article was the *real* source the @DiscussingFish Switch 2 satire cited to look credible — i.e. it is the thing fakes borrow authority from. | **Split by content type:** news = Tier 2; "everything we know" / hub / guide pages = Tier 3 evergreen SEO, not news. High volume — will flood a digest. |
| **Polygon** | `polygon.com` | **No GTA-specific track record found in this research, positive or negative.** | Rated **Tier 2-provisional on general standards only.** Ownership/staffing changed recently. Verify before promoting. |
| **GamesRadar+** | `gamesradar.com` | Reasonable. Published on GTA 6 leaks as an AI-disinformation story; reported the 2022 GTAForums cleanup. | Could not fetch the AI-disinfo piece (truncated). Mid-Tier-2. |
| **Game Informer** | `gameinformer.com` | Real masthead; reported the Extended Look announcement straight. | Low GTA-specific evidence. |
| **Variety / Deadline / ESPN / CNBC / Fortune / Computer Weekly** | `variety.com`, `deadline.com`, `espn.com`, `cnbc.com`, `fortune.com`, `computerweekly.com` | **Tier 2 scoped to corporate/business facts** — official delays, pricing, earnings, breach. Variety broke the price/single-player detail; CNBC ran the Zelnick interview; Computer Weekly covered the breach. | Not sources for gameplay/feature claims. `fortune.com` — see Tier 5B warning about a hijacked subdomain. |
| **BBC** | `bbc.com` | Tier 2 general news, **but with a documented GTA-specific miss:** reported the Netflix reveal as "a 30-minute special" with **no official source at all**, based only on circulating rumour, and had to walk it back (Aug 2026). | **Require corroboration for GTA product specifics** (runtimes, features, dates). Do not treat BBC as authoritative on Rockstar minutiae. |

**Demoted from the Tier 2 shortlist:**

| Outlet | Domain | Why demoted |
|---|---|---|
| **Insider Gaming (Tom Henderson)** | `insider-gaming.com` | **Tier 3, not Tier 2.** On 22 Aug 2026 it ran the CyberLeek "dead man's switch" story and **fully retracted it** — the piece "was based on an image and discourse that have since been proven false, manufactured and circulated online." Author Grant Taylor-Hill took personal responsibility. **Credit where due: the retraction was fast, explicit, and signed** — better behaviour than most. But the failure mode is exactly the one this bot must avoid: publishing a fabricated image as sourced fact. See §3 for Henderson's individual record. |
| **TechRadar / Tom's Guide** | `techradar.com`, `tomsguide.com` | **Tier 3.** Heavy "reportedly/rumoured" aggregation and SEO-driven rumour churn on GTA 6 specifically, including delay-speculation pieces. Fine for official-announcement echo, unreliable as a rumour filter. |
| **Notebookcheck** | `notebookcheck.net` | **Tier 3.** Aggregation-heavy. Credit: it did correctly report the Zap Actu GTA6 AI hoax and the fake bridge leak debunk. Useful as a *debunk* feed, weak as a news source. |
| **Dexerto** | `dexerto.com` | **Tier 3.** Fast, broadly accurate on the factual spine of the leak wave and reported Take-Two's denial of the physical-delay story, but volume-driven and rumour-forward. |
| **Push Square / The Gamer / Gameranx / NME / PlayStation Universe / Hot Hardware / SVG / Screen Rant / The Direct / Glitched / TweakTown / GamingBolt / Beebom / TheGamer** | various | **Tier 3.** Legitimate outlets, but on GTA 6 they mostly aggregate. TheGamer's leak-age piece uncritically labelled Nate the Hate "reliable" without evidence. TweakTown's "no review copies" story is an unverified insider claim. Push Square and The Gamer both correctly avoided linking footage — good behaviour, still Tier 3 sourcing. |
| **IBTimes UK** | `ibtimes.co.uk` | **Tier 4 — documented claim-laundering.** Ran "GTA 6 Delayed to February 2027? 4chan Leak Hints at New Release Date" — a question headline promoting an anonymous 4chan post with no corroborating documentation. To its partial credit it later published a "truth behind the rumours" follow-up, but the original is exactly the pattern the bot must catch. `inkl.com` syndicates it. |

---

### Tier 3 — GTA specialist / aggregator sites

**Key structural finding:** essentially **none of these do original reporting on GTA 6.** They aggregate Tier 2 reporting, republish insider claims, and do datamining/artifact research. Several are genuinely valuable — but as *debunk* and *artifact* feeds, not as sources of record.

| Entity | Domain | Original reporting? | Assessment |
|---|---|---|---|
| **RockstarINTEL** | `rockstarintel.com` | **Mostly no.** Aggregation + datamine coverage. | Tier 3. **Credit:** states it is "extremely rare" for it to report GTA 6 rumours "due to the fact that almost all of them have no sort of credibility" — a real editorial filter. **But** its own reliability is *derivative*: it explicitly leans on Tom Henderson and MP1ST as its credibility anchors, and it uses claim-laundering headlines ("GTA 6 Previews Are Happening Right Now, It's Claimed"). It also treats Take-Two copyright strikes as authenticity evidence — reasonable, but inferential. Acquired Rockstar Universe. Useful as a *tracking* feed. |
| **GTA BOOM** | `gtaboom.com` | No — aggregation. | Tier 3, **but the single most useful debunk feed found.** Documented wins: traced the Switch 2 rumour to @DiscussingFish satire and the KiwiTalkz walk-back; documented both the Insider Gaming and BBC retractions; debunked "delayed to 2027"; debunked "Schreier said GTA 6 is 90% finished." **Caveat:** clickbait-style slugs, and it editorialises beyond the record — it wrote "with PC coming later," which is **not** official. Ingest as debunks; do not treat its framing as fact. |
| **GTAForums** | `gtaforums.com` | Individual members do **artifact research** (domain registrations, datamines). | Tier 3 **as a signal source only; individual posts are unrated.** Also the **editorial precedent-setter**: in 2022 it complied with Take-Two's takedown ("we will be complying and this topic will be re-opened in due course"), stripped all links, and then **allowed discussion to continue without any footage or links**. That is precisely this community's rule, four years earlier. |
| **GTABase** | `gtabase.com` | **No news scoops found.** Database/guides/media reference. | Tier 3 **as a reference database**; **unrated for breaking news.** Self-describes as the largest GTA site; the team also ships mods (Los Santos HEISTS). Collaborates with RockstarINTEL — so treat the two as **correlated, not independent** corroboration. |
| **Rockstar Universe** | `rockstaruniverse.com` | Unknown. | **Unrated.** Owned by RockstarINTEL but "kept as a completely separate site." No independent track record found. Because of common ownership, **never count it as independent corroboration of RockstarINTEL.** |
| **Rockstar Mag — Chris Klippel** | `rockstarmag.fr` / `@Chris_Klippel` | Fan media; some access. | Tier 3. **Behaves responsibly:** on the Aug 2026 wave he said some details are real, some fake, and he has no information on others; he deliberately avoided deep-diving to dodge spoilers and advised followers to stick to Rockstar's official communications. He also made the sharp point that leaks show an unfinished, unoptimised build and exist to harm, not to promote. **No documented independent scoop verified in this research** — reputation is largely community-conferred. Tier 3, honest, not a primary source. |
| **GTANet** | — | n/a | **Unrated.** Network/organisation behind GTAForums rather than a publishing outlet. Not enough direct evidence to tier. |
| **GTA Wiki (Fandom) / WikiGTAVI** | `gta.fandom.com`, `wikigtavi.com` | User-generated. | **Tier 4.** Unmoderated sourcing; wikigtavi.com observed in SERPs only, not fetched. Useful for orientation, never as a citation. |
| **Sportskeeda (GTA vertical)** | `sportskeeda.com/gta` | No — very high-volume aggregation. | **Tier 4.** Rumour-forward, "fans react" churn, aggregates raw X posts. I searched specifically for documented criticism of its standards and **found none** — so: **no documented fabrication, tiered 4 on structure (volume + rumour-forward aggregation), not on proven inaccuracy.** |
| **MP1ST** | `mp1st.com` | Unknown for GTA. | **Unrated for GTA.** Called "extremely credible" by RockstarINTEL — but that is a second-hand reputation claim, which is exactly the reputation-inflation this document is meant to resist. No direct GTA evidence found. |

---

### Tier 4 — Unverified rumour surface (never post directly; corroboration required)

#### Subreddits

| Community | Handle | Assessment |
|---|---|---|
| **r/GTA6** | `reddit.com/r/GTA6` | Tier 4 for claims, **but editorially aligned**: strictly prohibits posting leaked content, including links to sources of leaks — a policy hardened after the March 2023 incident, and the sub was locked at one point under a flood of copyright takedowns. Safe to *monitor* for what the community is discussing; never a citation. |
| **r/GTA6Unmoderated** | `reddit.com/r/GTA6Unmoderated` | **HARD BLOCK.** Hosts leaked video and images; became the largest GTA 6 sub (~1M weekly visits) and was **formally warned by Reddit** for allowing GTA 6 leak media. Also where the fake-bridge hoaxer ran his reveal AMA. **Editorially incompatible with this community's rule and a legal-exposure vector.** |
| r/GamingLeaksAndRumours | `reddit.com/r/GamingLeaksAndRumours` | Tier 4. Structurally a rumour aggregator. Unrated for accuracy. |
| r/GrandTheftAutoV, r/gtaonline | — | Tier 4. Community discussion, not news. |
| **4chan /v/, /vg/** | `boards.4chan.org` | **HARD BLOCK.** Documented origin of the "GTA 6 delayed to February 2027" fabrication, which produced zero supporting documents, emails, or corroborating sources — and got laundered into IBTimes UK. Also the venue of anonymous "Rockstar developer AMA" claims. |

#### X accounts — aggregators with mixed records

| Handle | Assessment |
|---|---|
| `@GTAVI_Countdown` | Tier 4 aggregator. Reposted leaked clips explicitly framed as "the GTA 6 leak we got today **without context**." Not a fabricator; a laundering surface. Reposts infringing media → block for media, monitor only. |
| `@GTAVInewz` | Tier 4 aggregator. Self-describes as covering official news plus "speculations and rumors," explicitly not affiliated with Rockstar. Has been hit with DMCA issues. |
| `@GTA6_HQ` | Tier 4 aggregator. Reported the r/GTA6Unmoderated Reddit warning accurately — decent signal, no editorial standard. |
| `@GTAVIES` | Tier 4 aggregator (Spanish-language). Unrated for accuracy. |
| **`@DiscussingFish`** | **HARD BLOCK — special case.** A **self-described satire account.** Its GTA-6-on-Switch-2 mashup (official cover art + fake Nintendo branding, citing a real IGN pre-order article for plausibility) went massively viral as if genuine. **Satire, not disinformation — but identical downstream effect.** A bot cannot detect intent; block the domain of claims. |

#### CyberLeek-associated accounts — HARD BLOCK, all of them

`@cyberleek_ar_io`, `@cyberleekario`, `@MrCyberLeek`, YouTube `CyberLeeks`, `Surfer24k`, `Cyberleek_ar_io`.

All suspended and/or subpoenaed. **Critically: the three X handles were flagged by the GTA community as impostors *before* Take-Two's filing.** Plus the watermarks carried **memecoin solicitations** — a financial-scam vector, not journalism. Never ingest, never cite, never repost. Where the leak's *content* is discussed, attribute to the Tier 2 outlet that described it.

#### Named in filings but not news sources

**DarkViperAU** — a GTA V streamer whose Discord server was named in the Take-Two subpoena. He is a commentator, **not** a news source. Tier 4 for opinion; do not treat as reporting. Noted here only because his name will appear in legal coverage and shouldn't be mistaken for a source.

---

### Tier 4 — Individual insiders (see §3 for full assessment)

| Person | Handle | GTA-specific tier | Why |
|---|---|---|---|
| **Tez2** | GTAForums | **Tier 3 for artifacts / Tier 4 for hearsay** | Split by claim type — see §3. |
| **Nate the Hate** | `@NateTheHate2` | **Tier 4 for GTA** | Domain of accuracy is Nintendo, not Rockstar. |
| **KiwiTalkz** | `@KiwiTalkz` | **Tier 4** | Honest actor, unreliable claim — see §3. |
| **Jeff Grubb** | `@JeffGrubb` | **UNRATED for GTA** | No GTA-specific evidence found. |
| **Liam Robertson** | `@Doctor_Cupcake` `[UNVERIFIED handle]` | **UNRATED for GTA** | No GTA-specific evidence found. |
| **"Videotech"** | `[UNVERIFIED]` | **UNRATED** | Could not confirm this entity exists as a GTA source at all. |

---

### Tier 5 — Known fake / clickbait / hard-block

I have split this into three sub-tiers because the **evidentiary basis differs**, and conflating them would be exactly the reputation-by-vibes failure this document is supposed to prevent.

#### 5A — Documented fabrication (specific, evidenced incidents)

| Entity | Handle / identifier | Evidence |
|---|---|---|
| **Zap Actu GTA6** | X: `Zap Actu GTA6` / `zapactugta6` | **Nov 2025.** Posted AI-generated fake GTA 6 "gameplay" that hit **8M+ views in 24 hours** before removal. The account holder admitted the deception, framing it as a "social experiment"/"huge joke," and deleted the related posts after backlash. Skepticism about that explanation was widespread — the account had posted GTA content for years and likely met X monetisation thresholds. **HARD BLOCK.** |
| **GTASixJoker** | X: `GTASixJoker` | **Apr 2026.** Spent months posting AI images deliberately made to look like leaked GTA 6 screenshots. Received a **Take-Two cease-and-desist**; issued a public apology **24 Apr 2026** conceding the images "risked confusing fans with real leaks." **HARD BLOCK.** |
| **u/elefelelen ("tenshi")** | Reddit `u/elefelelen` | **Mar 2026.** Built the viral "Vice City bridge" fake **from scratch over several months** using external tools, mimicking Rockstar's lighting, UI and debug overlays, and seeded it via a burner Instagram account as footage from a "former Rockstar employee." Self-debunked in a YouTube video titled *"I Tricked the Internet with a Fake GTA 6 Leak."* Ran the reveal AMA on r/GTA6unmoderated. **HARD BLOCK.** |
| **The "dead man's switch" image forger** | unattributed impostor | **Aug 2026.** Fabricated an image of a CyberLeek ultimatum. Caused Insider Gaming's full retraction. Origin never identified — **block the claim pattern, since the actor is unnamed.** |
| **The Feb 2026 "TV screen recording" hoax** | creator **not identified** | Clip of Jason entering a house + character switch + map menu; 500k+ views. **Debunked by two tells:** the map was stitched together from official Rockstar promotional images, and it contained the typo **"poin of interest."** Creator unknown — **do not guess a name.** |
| **The "elaborate GTA 6 fake announcement" YouTuber** | **name not established** | TechRadar covered a YouTuber who staged an elaborate fake GTA 6 announcement. **I could not establish the channel name — deliberately left unnamed rather than guessed.** |

#### 5B — Parasite SEO / hijacked subdomains → HARD BLOCK, and the single best programmatic signal found

During this research, GTA 6 "leak" spam appeared repeatedly in search results on **otherwise-legitimate institutional and corporate domains**, under near-identical templated headlines:

- `widescope.stanford.edu` — "GTA 6: The Leaked Secrets Unveiled", "GTA 6 Map Leak: Official News"
- `smi.engin.umich.edu` — "GTA 6: The Leaked Secrets Unveiled", "Leaked! GTA 6 Gameplay Secrets Unveiled"
- `commons.open.uci.edu` — "gta 6 leaks"
- `cuentame.coe.arizona.edu` — "Leaked! GTA 6 Gameplay Secrets Unveiled"
- `ftp.dia.ucla.edu` — "Leaked! GTA 6 Gameplay Secrets Unveiled"
- `eduadmin.fortune.com` — "GTA 6: The Leaked Secrets Unveiled"
- `smallbiz.monster.com` — "GTA 6: The Leaked Secrets Unveiled", "GTA 6 Map Leak: Official News"

This is **subdomain hijacking / parasite SEO**: spam hosted on high-authority domains to inherit their ranking. Three of these are `.edu`; two are major commercial brands (Fortune, Monster).

**This yields a near-zero-false-positive rule.** A `.edu`, `.gov`, or `.ac.*` host — or an unrelated corporate brand subdomain — publishing GTA 6 leak clickbait is **always** compromised. Stanford does not report on GTA 6 map leaks.

```
if (host matches *.edu|*.gov|*.ac.* OR host is a subdomain of a non-gaming corporate brand)
   AND (title matches GTA-leak clickbait pattern):
       DROP with reason "parasite_seo"  # confidence: effectively 100%
```

Also note the **duplicate-title signal**: the identical string "GTA 6: The Leaked Secrets Unveiled" appearing on four unrelated domains is a syndicated-spam fingerprint. Hash normalised titles; ≥3 unrelated hosts sharing one → drop the whole cluster.

#### 5C — SEO content farms → block by default, on STRUCTURAL grounds

**Important framing, stated plainly:** for the domains below I found **no evidence of deliberate fabrication.** They are blocked because they exhibit **structural markers of non-journalism** — no masthead or named editorial staff, no original reporting, affiliate/key-reseller or pure-adtech business models, evergreen "everything we know" templates, and (observed in SERP titles) a habit of asserting "Confirmed" for things that are not confirmed. **This is a block-by-default list, not an accusation.**

Observed asserting unconfirmed things as confirmed:
- `gtanerd.com`, `gta6tricks.com`, `gtavispot.com`, `gtaboss.gg`, `gtasixguide.com`, `gta6index.com`, `gta6monitor.com`, `gta6post.com`, `gta6realm.com`, `6charts.com`, `ilovegta6.com`, `gtagenius.com`, `gtavicentral.com`, `gta6-rp-servers.com`
- `tech-insider.org` (SERP title: "Zelnick Confirms No Delay" — Zelnick confirmed the date, not a "no delay" statement), `thepcenthusiast.com`, `pcgamecheck.com`, `techwiser.com`, `technwz.com`, `nerdyinfo.com`, `expertgamereviews.com`, `bitsfrombytes.com`, `jeu.video`, `sixhype.com`, `timesaver.gg` ("What Rockstar Confirmed About Multiplayer & GTA Online 2" — Rockstar confirmed nothing), `howtoplayhub.com`, `games.gg`, `gamingpromax.com`, `gfinityesports.com`
- `gamermarkt.com` ("Full Confirmed Cast List (2026)" — **no cast is confirmed**), `sundayguardianlive.com` ("Voice Actors Confirmed?" — question-mark-plus-Confirmed, the canonical tell), `driffle.com`, `eneba.com/hub`, `drawpie.com`, `var-fivem.com`, `gamelistzone.com`, `glitched.online`
- `shattered.io`, `ar-pay.com`, `vpesports.com`, `egw.news`, `thepakistanconnect.com`, `thenews.com.pk`, `cosmicbook.news`, `esquireindia.co.in`, `shanethegamer.com`, `theshortcut.com`, `studioglobal.ai`, `explainx.ai`, `drezzed.clownfishtv.com`
- Wiki/mirror/syndication surfaces: `baike.baidu.com`, `en.namu.wiki`, `ifann.net`, `imdb.com/news`, `inkl.com`, `gamegpu.com`, `tech4gamers.com`, `nsaneforums.com`, `bluntmag.com.au`, `spieltimes.io`, `0xspectrum.substack.com`

> **Caveat, honestly stated:** several of these were only observed in search-result titles and **were not fetched**. A few produced genuinely useful content — `driffle.com` carried a serviceable 2026 hoax compilation, and `notebookcheck.net` (Tier 3, not blocked) correctly reported two debunks. Blocking is a *precision* decision for an automated digest, not a judgement on every article. Keep 5C in a separate config key from 5A so it can be relaxed independently.

---

## 3. INDIVIDUAL JOURNALISTS AND INSIDERS

**Reputation inflation is the dominant failure mode in this space.** Two patterns recur: (a) an insider accurate in *one* domain is described as "reliable" in *all* domains; (b) "reliable insider" is asserted by outlets that never cite a single verified hit. Both appear in the sources below.

### Jason Schreier — Bloomberg — **Tier 2 (written) / Tier 3 (verbal)**

**Documented hits:** reported both GTA 6 delays; reported that Rockstar staff were not informed of the 2026 delay in advance; his earlier reporting on **dual protagonists and the Vice City setting** was corroborated years later by the Aug 2026 leak footage. He reportedly assesses the current leak as genuine.

**Documented misses:** **none found on GTA specifically.** What exists instead is a *laundering* problem, which matters more for the bot:

- His remark that GTA 6 was "still not content complete" was spun into delay headlines. He responded that this was **"a complete misunderstanding of what I said,"** noting he "wouldn't be shocked if GTA 6 *does* come out this fall," on the RDR2 pattern. GameSpot and TheGamer both reported the correction; GTA BOOM separately had to debunk a claim that he'd said GTA 6 was "90 percent finished" — **a thing he never said.**

**Bot rule:** Bloomberg bylined articles → Tier 2, post as fact. Podcast/Twitch/verbal remarks relayed by third parties → **Tier 3, and never sufficient for a delay story.** Add a specific guard: any delay item whose ultimate source is a Schreier verbal remark gets auto-flagged for the misconstruction pattern.

### Stephen Totilo — Game File — **Tier 2**

**Documented strengths:** described the Aug 2026 leaks without linking to them; accurately reported the subpoena timeline (filed Thursday, approved by Friday); explicitly noted that **"Rockstar and Take Two reps did not reply to requests for comment"** on the footage's age and authenticity — i.e. he sought comment and disclosed the non-response, which is the actual marker of a real reporting process. Correctly reported that Take-Two ran trailers and opened pre-orders **without showing gameplay or previewing to press.** Landed a Zelnick interview. Ex-Kotaku EIC, ex-Axios, ex-MTV News. Covered the 2022 leak contemporaneously.

**Documented misses on GTA:** none found.

**Bot rule:** Tier 2. Low volume, high signal. Note the paywall — may need description-only ingestion.

### Tom Henderson — Insider Gaming — **Tier 3 for GTA (NOT Tier 2)**

This is the assessment most at odds with his general reputation, so the evidence:

**Documented misses, Rockstar-specific:**
- Promoted a **full remaster of Red Dead Redemption**; Rockstar instead shipped a standard last-gen port.
- Floated a **Bully revival**; years later, no announcement.
- His outlet's **22 Aug 2026 "dead man's switch" story was fully retracted** as founded on a fabricated image. (Authored by Grant Taylor-Hill, not Henderson — but it is the outlet's output.)
- Community skepticism specifically about his GTA 6 marketing-campaign claims, with users cataloguing prior errors.

**Documented strengths:** genuinely strong on **Battlefield and Call of Duty**. His "content-ready / no further delay" GTA 6 read has so far held up — but note he did not claim a source for it, and it is a prediction rather than a scoop.

**Assessment:** classic domain-transfer inflation. Accurate on shooters ≠ accurate on Rockstar. **Tier 3.** Requires Tier 2 corroboration before posting even as rumour.

**Credit where due:** the retraction was fast (same weekend), explicit, and personally signed — *"The original report should not be considered a failing of Insider Gaming, but rather of myself."* That is better conduct than most, and is why this is Tier 3 rather than Tier 5.

### Tez2 — GTAForums — **Tier 3 for verifiable artifacts / Tier 4 for hearsay**

**Documented hit:** spotted a batch of domains registered **27 May 2025** under Take-Two's nameservers and posted them to GTAForums in early Sept 2025 — apparent placeholder in-game websites. **The strongest credibility marker:** one of them, `what-up.app`, corroborated a detail first visible in the **2022** leaked footage — two independent artifacts agreeing across three years.

**Why the split tiering matters:** the domain find is **registrar-record research** — independently checkable by anyone, provable, falsifiable. That is a genuinely different epistemic class from "my source says." Claims of the first kind are Tier 3; claims of the second are Tier 4.

**Documented misses:** none found — **but note I found no systematic audit of his record**, and "past records put some weight on their leaks" is the kind of vague reputation claim this document distrusts. Confidence: `[MED]`.

**Bot rule:** if the claim rests on a checkable artifact (WHOIS, datamine, store metadata, certificate, filing) → Tier 3, verify the artifact directly and post as fact if it verifies. If it rests on unnamed sourcing → Tier 4.

### Chris Klippel — Rockstar Magazine — **Tier 3**

**Behaviour is exemplary; track record is unproven.** On the Aug 2026 wave he stated plainly that some details are real, some are fake, and on some points **he has no information** — an unusually honest position. He deliberately limited his own exposure to avoid spoilers and told followers to rely on Rockstar's official communications. He also made the analytically sharp point that leaks show an unfinished, unoptimised build and exist to *harm* rather than promote.

**No documented independent scoop verified in this research.** His standing appears to be community-conferred plus longevity, not a catalogue of hits. **Tier 3, and safe to quote as informed commentary — but not a source of fact.**

### Nate the Hate — **Tier 4 for GTA**

**The Aug 2026 claim:** the leaked footage is **over a year old** and not from the rumoured preview programme. This *partially aligns* with CyberLeek's own claim of a **2023 build**, and TheGamer noted the footage "does look a little bit janky and dated."

**But:** "aligns with the leaker's own claim" is not independent verification — it may simply be repetition. Rockstar and Take-Two **declined to comment** on the footage's age, so the claim is **unresolved, not confirmed.** TheGamer and Notebookcheck both labelled him "reliable" **without citing a single verified GTA hit** — textbook reputation inflation. His actual domain of accuracy is **Nintendo**.

**Tier 4 for GTA.** Requires 2 Tier-2 outlets.

### KiwiTalkz — **Tier 4 (honest actor, unreliable claim)**

Named as the origin of a GTA-6-on-Switch-2 source claim. **He publicly clarified he never said GTA 6 was coming to Switch 2 at launch** — he was relaying a source claim **he has openly doubted for months and still doubts**, and he does not believe a Switch 2 edition exists at all.

**Two lessons for the bot:** (1) the *relay* got stripped of its hedging as it propagated — the bot must preserve hedges or drop the item; (2) a source can behave honestly and still be an unreliable *node*. Tier 4.

### Jeff Grubb — **UNRATED for GTA**

Searched specifically. **No GTA-6-specific evidence found, positive or negative.** He has an industry-wide reputation, but I will not transfer it. Treat as Tier 4 by default; do not assign Tier 2 or 3 without GTA-specific evidence.

### Liam Robertson — **UNRATED for GTA**

Searched specifically. **No GTA-6-specific evidence found.** His documented specialism is unreleased-game history and documentary research — a genuinely valuable but different beat, with no bearing on live GTA 6 news accuracy. Handle unverified. Tier 4 by default.

### "Videotech" — **UNRATED / EXISTENCE NOT ESTABLISHED**

Searched specifically. **I could not confirm this entity exists as a GTA 6 source at all.** No handle, channel, or claim located. **Do not add to config in any tier.** If the user has a specific account in mind, it needs identifying before it can be rated.

### Digital Foundry (Battaglia / Mackenzie / Linneman) — **Tier 2 scoped, technical only**

Verified analysis: Trailer 2 gameplay running at ≈**2560×1152 upscaled to 4K at 30fps**; Linneman on hair-strand simulation (Lucia's hair) and ray-traced global illumination. **Predictions** — 720p on Series S, 30fps cap even on PS5 Pro — are informed speculation, **Tier 3.** Note that low-tier sites reprint DF predictions as "analyst confirms," so the bot should catch DF-derived claims that have lost their hedge.

---

## 4. PROGRAMMATIC FABRICATION DETECTION

### 4.1 Hard gates — evaluated BEFORE scoring, any hit = immediate DROP

Order matters; these are cheap and decisive.

| # | Gate | Rule | Reason code |
|---|---|---|---|
| G1 | Tier 5A/5B blocklist | host or handle in blocklist | `blocked_source` |
| G2 | **Parasite SEO** | host matches `*.edu`/`*.gov`/`*.ac.*`, or is a subdomain of a non-gaming corporate brand, **AND** title matches GTA-leak clickbait | `parasite_seo` |
| G3 | **Leaked-media carrier** | item embeds/links leaked video or images; or contains `mega.nz`, `mediafire`, `magnet:`, `anonfiles`, `pixeldrain`, `catbox.moe`, `streamable`, or phrases like "watch the full clip", "download here", "link in bio", "mirror" | `hosts_leak` |
| G4 | **Baseline contradiction** | asserts anything in §1.2 as fact **and** source tier > 1 | `contradicts_baseline` |
| G5 | **Scam / financial** | mentions memecoin, crypto, token, giveaway, "free download", "beta key", "early access code", referral | `scam` |
| G6 | **Leaker-origin** | source is CyberLeek-associated, an impostor handle, r/GTA6Unmoderated, or 4chan | `leaker_origin` |
| G7 | **Satire** | host/handle on the satire list (`@DiscussingFish`, known satire domains) | `satire` |
| G8 | Duplicate-title cluster | normalised title hash shared by ≥3 unrelated hosts | `syndicated_spam` |

> G3 has an important refinement: a **Tier 2 article that only *describes*** the leak passes G3. A Tier 2 article that **embeds** it fails G3 — but you may still post the *claim* by citing the outlet while stripping the media. Implement G3 on the **bot's outgoing embed**, not only on the inbound URL. Discord auto-unfurls: **explicitly suppress embeds** (`suppress_embeds` / `<url>` bracket syntax) or post no URL at all for leak-derived items.

### 4.2 Scoring model

**Base score from source tier:**

| Tier | Base |
|---|---|
| 1 | **+100** |
| 2 | **+60** |
| 3 | **+25** |
| 4 | **0** |
| unrated / unknown domain | **−30** |
| 5 | drop (gate G1) |

**Additive signals — credibility positive:**

| Signal | Weight |
|---|---|
| Each additional **independent** Tier-2 outlet reporting the same claim | **+25** (cap +50) |
| Links to a Tier-1 primary document (Newswire, SEC, store listing) | **+30** |
| Named byline present | **+10** |
| Explicit attribution chain ("according to *named* outlet/journalist") | **+10** |
| Article explicitly declines to link leaked material | **+10** |
| Direct quote with named speaker + venue (earnings call, interview) | **+15** |
| Claim rests on an independently checkable artifact (WHOIS, datamine, filing, store metadata) **and the bot verified it** | **+35** |
| Outlet published a correction/retraction on this specific claim | **+20** (rewards self-correction; the item itself becomes a *correction* post) |

**Additive signals — credibility negative:**

| Signal | Weight | Evidence basis |
|---|---|---|
| Hype-certainty token in headline (`CONFIRMED`, `OFFICIAL`, `FINALLY`, `BREAKING`, `SHOCKING`, `INSANE`, `HUGE`) **without** a Tier-1 link | **−25** | `gamermarkt.com` "Full Confirmed Cast List"; `timesaver.gg` "What Rockstar Confirmed About Multiplayer"; `tech-insider.org` "Zelnick Confirms No Delay" — all assert confirmation that does not exist |
| **Question-mark headline** | **−20** | IBTimes UK "GTA 6 Delayed to February 2027?"; `sundayguardianlive.com` "Voice Actors Confirmed?" — question headlines launder unsourced claims |
| ALL-CAPS token ≥4 chars, excluding an acronym allowlist (`GTA`, `VI`, `PS5`, `DLC`, `NPC`, `RP`, `AI`, `PC`, `FPS`, `CEO`, `DMCA`, `IGN`, `VGC`, `RDR2`, `SEC`, `FY`) | **−15** | generic clickbait marker |
| Evergreen-SEO template (`everything we know`, `all we know`, `what we know so far`, `complete guide`, `explained`, `here's why`) | **−25** | not news; will flood a daily digest |
| `LEAK`/`LEAKED` in headline | **−10** and **forces rumour label** | |
| Domain age **< 180 days** | **−40** | |
| Domain age **180–365 days** | **−25** | |
| No masthead / no named editorial staff page | **−25** | primary 5C structural marker |
| Affiliate or key-reseller business model | **−20** | `driffle.com`, `eneba.com`, `gamermarkt.com` |
| Single-source, unnamed sourcing ("sources tell us", "it's claimed") | **−20** | RockstarINTEL "It's Claimed" pattern |
| Ultimate origin is 4chan / anonymous forum / anonymous AMA | **−60** | the 2027 delay fabrication; the "Rockstar developer AMA" claims |
| Claim relayed with its hedge removed vs. the original | **−30** | KiwiTalkz Switch 2; Schreier "content complete"; DF predictions → "analyst confirms" |
| Reupload of a claim >7 days old presented as new | **−20** | |
| Domain had a GTA retraction in the last 30 days | **−20** | Insider Gaming, BBC — both in one week of Aug 2026 |
| Correlated-ownership corroboration counted as independent | **−25** (and don't count it) | RockstarINTEL ↔ Rockstar Universe; RockstarINTEL ↔ GTABase collaboration; IBTimes ↔ inkl |

**Media-authenticity signals (apply when the item carries an image/video claimed to be a leak):**

| Signal | Weight | Evidence basis |
|---|---|---|
| **"Too polished" inversion** — clean UI, no debug overlay, no placeholder assets, stable framerate | **−35** | The single best AI tell found. The authentic 2022 leak "featured debug menus and unfinished models"; the Zap Actu AI fake was "so polished and technically refined that they immediately raised doubts." **Real in-development footage looks worse than the trailers, not better.** |
| Text rendering errors inside the image (OCR the frame) | **−45** | The Feb 2026 hoax was caught by **"poin of interest"** instead of "point of interest" |
| Reverse-image match to official promotional art / trailer frames | **−50** | The Feb 2026 hoax map was "official Rockstar promotional images stitched together" |
| HUD/map inconsistency vs. known-good reference | **−30** | The bridge fake was flagged for "inconsistencies in the debug UI, map accuracy, and asset placement" before the creator confessed |
| Provenance is a burner/new account, or no frame history | **−30** | Bridge fake seeded via a burner Instagram account |
| Claimed as from a "former Rockstar employee" with no name | **−35** | Bridge fake's cover story; also the anonymous AMA pattern |
| Watermark containing a manifesto, crypto, or handle | **−1000** (gate G5) | CyberLeek watermarks carried memecoin solicitations |
| **No DMCA takedown observed after 48h of virality** | **−20** | Inferential but useful: Rockstar DMCA'd the CyberLeek material within days. Genuinely infringing material gets struck; AI fakes usually don't. **`[LOW]` confidence — use as a weak tiebreaker only, and note Take-Two *did* C&D the GTASixJoker AI images, so absence of a strike is not proof of fakery.** |

### 4.3 Thresholds

| Score | Action |
|---|---|
| **≥ 80** | **POST AS FACT** — reachable only by Tier 1, or Tier 2 + primary-document link, or Tier 2 + one independent Tier 2 |
| **40–79** | **POST AS RUMOUR** — labelled, attributed to the reporting outlet, media stripped |
| **0–39** | **HOLD** in a corroboration queue, TTL 48h |
| **< 0** | **DROP** |

Additionally: **any leak-derived claim is capped at "RUMOUR" regardless of score.** A Tier-2 outlet accurately describing a leak makes the *reporting* reliable, not the *claim* true. This is the rule that implements the community's editorial decision — and it is what would have saved Insider Gaming.

### 4.4 THE CORROBORATION RULE

```
TIER 1                          -> POST AS FACT immediately.

TIER 2, cites a Tier-1 document -> POST AS FACT immediately.

TIER 2, named/on-record source  -> POST AS FACT immediately, attributed.

TIER 2, unnamed sourcing        -> POST AS REPORT ("<Outlet> reports...") immediately,
                                   flagged single-source.
                                   Promote to FACT if a second INDEPENDENT Tier 2
                                   corroborates within 24h.

TIER 3                          -> HOLD. Post as RUMOUR only once >=1 Tier-2 outlet
                                   reports it within 24h. Attribute to the TIER 2 OUTLET,
                                   never to the Tier 3 origin.

TIER 4                          -> HOLD. Post as RUMOUR only once >=2 INDEPENDENT Tier-2
                                   outlets report it within 48h. Attribute to the
                                   Tier 2 outlets. NEVER name the Tier 4 origin as
                                   the authority.

TIER 5                          -> NEVER. Not even as "a fake is circulating", unless a
                                   Tier 2 outlet has published a debunk — then post the
                                   DEBUNK, citing the Tier 2 outlet.

LEAK-DERIVED                    -> Max label RUMOUR, always. Media always stripped.
```

**Definition of "independent" — this is the part that is usually got wrong:**

Two outlets are independent **only if all** hold:
1. Different parent company (maintain an ownership map — Eurogamer/Digital Foundry/IGN sit under one umbrella; RockstarINTEL owns Rockstar Universe; inkl syndicates IBTimes).
2. Neither article cites the other as its sole source. **Build a citation graph:** if B links to A and has no other sourcing, B is an echo, not corroboration.
3. Neither traces to the same single upstream origin. Five outlets reporting one 4chan post is **one** source. This is the mechanism by which the 2027 delay fake spread.
4. Publication times differ by > 20 minutes (near-simultaneous = coordinated wire/embargo, i.e. one source).

**Retraction watch — mandatory, and the highest-value single feature:**

Re-check every posted item at **+6h, +24h, +72h**. If the originating outlet retracts, edits, or 404s the piece, the bot must post a **correction in the same channel**, strike the original digest entry, and log the domain's retraction (feeding the −20 penalty).

Justification: in **one week** of Aug 2026, two outlets — **Insider Gaming** (dead man's switch, retracted within a day) and the **BBC** (30-minute runtime) — both walked back GTA 6 claims. A bot without retraction-following would still be asserting both.

---

## 5. THE PERENNIAL FAKE STORIES

Ten recurring themes, each with why it recurs and the machine-checkable tell.

### 5.1 Fake delays ("GTA 6 delayed to 2027")

**Why it recurs:** Rockstar has *actually* delayed twice, so the claim is plausible; and delay stories are the highest-engagement GTA topic in existence. There is also a real financial audience (TTWO traders) that rewards them.

**How to spot it:**
- Origin is 4chan, an anonymous post, or a "leaked internal email" with no document.
- Uses a *specific new date* (February 2027) — fabrications over-specify to seem credible.
- No corroboration from Take-Two guidance or SEC filings. **The killer check: Take-Two's FY2027 net-bookings guidance and 10-K both encode 19 Nov 2026.** A real delay moves guidance.
- **Real delays are announced by Rockstar first**, on Newswire — both actual delays were. A delay reaching you via a leaker before Newswire is fake.

**Bot rule:** any delay claim not on `rockstargames.com/newswire` or a Take-Two filing → drop.

### 5.2 Fake platform announcements (Switch 2, PC)

**Why it recurs:** two enormous frustrated audiences. PC players have no date; Switch 2 owners want parity. Wishcasting plus a genuine information vacuum.

**How to spot it:**
- **Switch 2:** traced to `@DiscussingFish` **satire** — official cover art + fake Nintendo branding, and it cited a *real IGN pre-order article* to borrow credibility. A separate strand attributed to **KiwiTalkz**, who disowned it. Also technically implausible on hardware grounds.
- **PC:** the tell is a **specific date or storefront**. Since Rockstar has published no date, no storefront and no system requirements, *any* specific PC claim is fabricated or speculative. Watch for "2027" and "2028" presented as fact — those are extrapolations from GTA V's history.
- **Detection:** platform claims must appear on the Rockstar site or a first-party store listing. Nowhere else counts.

### 5.3 Fake map leaks

**Why it recurs:** the map is the most speculated-about asset, it is easy to fake (any Florida-shaped landmass looks plausible), and it is highly shareable as a single image.

**How to spot it:**
- Reverse-image search against official promo art — the Feb 2026 hoax map was **stitched from official Rockstar images**.
- **OCR the image for typos** — that hoax was killed by **"poin of interest."** Rockstar does not ship typos in shipped UI.
- Compare against the known-genuine Aug 2026 leaked map's described geography (compact distorted south Florida; large eastern city; greenspace west/north; Keys-like island chain south) — but *never* republish the image.

### 5.4 Fake gameplay footage (AI era)

**Why it recurs:** generative video became good enough in 2025–26 that fakes reach millions before debunking. Zap Actu GTA6 got **8M+ views in 24 hours**. There is direct monetisation via X payouts and YouTube ads.

**How to spot it — the inversion is the key insight:**
- **Real leaks look WORSE than trailers.** Authentic 2022 footage had **debug menus and unfinished models**. AI fakes are suspiciously polished — that is literally what triggered doubt about the Zap Actu clip.
- Handmade fakes (the bridge clip) *simulate* debug overlays — so also check overlay **internal consistency** against known-good references, which is how the community caught it pre-confession.
- Blurry/short + "from a former Rockstar employee" + burner account = the bridge-fake template exactly.
- Kotaku's framing is worth encoding: **most GTA channels covering the leaks used AI clips as B-roll, and not all labelled them.** So an AI frame in a video does not prove the *claim* is fake — but it disqualifies the video as evidence.

### 5.5 Fake character / actor reveals

**Why it recurs:** Rockstar withholds cast until launch (GTA V confirmed Ogg/Luke/Fonteno only in launch-day interviews), creating a years-long vacuum. Voice-matching is subjective, so "fan detective work" generates endless confident wrong answers.

**How to spot it:**
- **Two actors have publicly denied** being Jason: **Roger Craig Smith** ("Not me. Just to clarify" / "LITERALLY attempting to clarify that it is NOT my voice in that trailer") and **Troy Baker**. Any item naming either is stale-false.
- Manni L. Perez (Lucia) and Dylan Rourke (Jason) are the current *rumours*. Headlines calling them "confirmed" are false by definition.
- Tell: "Confirmed" + a question mark in the same headline (`sundayguardianlive.com`); or "Full Confirmed Cast List" (`gamermarkt.com`) when zero cast is confirmed.

### 5.6 Fake "Rockstar employee" AMAs / dev leaks

**Why it recurs:** unfalsifiable and free to produce. Anonymity is pre-excused ("protecting my career"), which conveniently removes all accountability.

**How to spot it:**
- Anonymous by construction — and, as reported, the anonymity itself "greatly damages the credibility."
- Moderators remove the thread, but screenshots survive and get laundered into articles. **The claim outlives its deletion** — so track claim text, not URLs.
- Content pattern: a *long list* of granular narrative features (chapter systems, a linear Liberty City visit, a Cuban island chapter, "more emotional tone"). Real leaks are narrow; fakes are comprehensive, because breadth is what impresses.
- The bridge hoaxer also used a "former Rockstar employee" cover story. Treat that phrase as a red flag, not a credential.

**Bot rule:** anonymous-AMA-origin → −60 and Tier-4 handling. Never post even as rumour without 2 independent Tier 2.

### 5.7 Fake GTA 6 Online / GTA Online 2 details

**Why it recurs:** GTA Online was GTA V's decade-long revenue engine, so its absence from GTA 6 marketing is conspicuous. Nature abhors the vacuum.

**How to spot it:**
- **Baseline: nothing announced.** No mode, no date, no monetisation model, no roadmap, no confirmation GTA Online 2 is even in development. Rockstar has published no dedicated announcement either way; the "single player experience" framing comes from pre-order marketing and store listings.
- Therefore any "GTA 6 Online confirmed/detailed/dated" item is fabricated or speculative.
- Watch the specific conflation: Take-Two saying **GTA Online (V) updates continue** post-launch is *not* a GTA 6 Online announcement. Expect that misreading constantly.

### 5.8 Fake mod / RP / FiveM support — **highest priority for this community**

**Why it recurs:** this server's members want it most, and there is a genuinely confusing true fact underneath: **Rockstar really does own Cfx.re** (FiveM/RedM). That true premise makes false conclusions feel earned.

**How to spot it:**
- **Baseline: no GTA 6 RP/FiveM support has been announced.** No official GTA 6 RP servers exist. Rockstar has not said FiveM will support GTA VI.
- Structural impossibility check: **server frameworks run on PC**, and PC is unannounced. So any "GTA 6 RP servers at launch" claim is incoherent on its face — a cheap, reliable auto-check.
- `[LOW]` confidence claim to watch: that a "Cfx Marketplace" went live in Jan 2026. Sourced only to SEO-farm domains in this research — **do not treat as baseline.**
- Whole domains exist to farm this (`gta6-rp-servers.com`, `var-fivem.com`, `ilovegta6.com`) — all 5C.

### 5.9 Fabricated / distorted executive quotes

**Honest finding, stated plainly:** I searched specifically for a **fabricated** Strauss Zelnick quote and **found no documented instance.** The user's brief anticipated one; the evidence does not support it.

**What the evidence *does* support is a different and more common mechanism: distortion of real quotes.** Documented cases:
- **Jason Schreier's** "not content complete" remark → spun into a delay story. He called it "a complete misunderstanding of what I said."
- **Schreier** falsely credited with saying GTA 6 was **"90 percent finished"** — GTA BOOM had to publish a debunk of a thing he never said.
- **KiwiTalkz** → hedged relay stripped of its hedge.
- **Digital Foundry** predictions → reprinted as "analyst confirms."
- `tech-insider.org` "Zelnick Confirms No Delay" — Zelnick reaffirmed the date; "confirms no delay" is an editorial upgrade.

**So the bot should not hunt for fake quotes. It should hunt for hedge-stripping**, which is measurable: compare the claim's modality ("confirms", "says") against the original's ("wouldn't be shocked", "the last I heard", "expects"). Mismatch → −30.

Real Zelnick quotes to anchor against: "Rockstar got it right" on Standard/Ultimate pricing (7 Aug earnings call); "I believe we will exceed expectations"; "most-anticipated entertainment property of all time"; and he found the 2022 leak "disappointing."

### 5.10 Fake trailer / reveal specifics

**Why it recurs:** a dated event with an unknown payload — the perfect fabrication substrate. Runtime, content, and "what will be shown" are all guessable and unfalsifiable until the event.

**How to spot it:**
- **The BBC's "30-minute special" is the case study:** a specific runtime with **no official source at all**, based purely on circulating rumour, from a Tier-2 outlet. Walked back. Even good outlets fail here.
- Officially known: Netflix 27 Aug 3 PM ET, Rockstar YouTube + GTA VI site 9 PM ET. **Runtime and contents are not announced.**
- Tell: any specific number (minutes, number of trailers, number of missions shown) attached to an unreleased event.

**Bot rule:** for scheduled-event items, allow only date/time/venue from Tier 1. Any *content or runtime* claim → rumour at best, regardless of outlet tier.

---

## 6. RESPONSIBLE HANDLING OF LEAKS — THE NORM, AND WHAT THE BOT SHOULD IMITATE

### 6.1 What credible outlets actually did in Aug 2026

I checked handling directly rather than assuming. The norm is remarkably consistent: **describe, never distribute.**

| Outlet | Handling | Evidence |
|---|---|---|
| **Engadget** | **Refused outright, and said so.** | *"While we can't share the materials here or tell you where to find them, you're a citizen of the internet."* Also hedged that the clips "may not be entirely legitimate" and that their age is unknown. **The single cleanest model.** |
| **Game File** | Described the clips; pointed to the existence of "lengthy descriptions" elsewhere rather than to footage; **no links**. Sought comment from Rockstar/Take-Two and **disclosed the non-response**. | |
| **PC Gamer** | Published a 15-detail **analysis** of what the footage shows without hosting media. Framed features (morality system, stamina meter) as "possible." | |
| **The Gamer** | Described contents; **no links to footage** at all. | |
| **Kotaku** | Covered the **meta-story** — how AI fakes make real leaks unidentifiable — rather than trafficking the material. Consistently used "seemingly"/"alleged." | |
| **VGC** | Headline hedged to *"allegedly leaks."* Reported Rockstar's DMCA response and Discord restriction. | |
| **TorrentFreak** | Reported the **legal documents**, naming handles and firms — journalism *about* the leak's enforcement, containing none of the leaked content. | |
| **Counter-example: r/GTA6Unmoderated** | **Hosted** the media → formally warned by Reddit; became a subpoena-adjacent liability. | |

### 6.2 The 2022 precedent — which is exactly this community's rule

**GTAForums** in Sept 2022, after Take-Two contacted them:

> *"We have been contacted by Take-Two Interactive to take down copyrighted material from GTAForums. As usual with previous games, we will be complying and this topic will be re-opened in due course."*

The thread returned **locked, with all links to the leak removed** — and critically:

> **Discussion around the leaked footage is still allowed as long as it doesn't include any actual footage or links to footage.**

That is the community's editorial rule, articulated by the biggest GTA forum four years ago and validated since. **r/GTA6** adopted the stricter version: no leaked content, including links to sources of leaks.

### 6.3 The norm, distilled — and the bot's implementation

**The norm:**
1. **Describe, never distribute.** The claim is reportable; the file is not.
2. **Attribute to the journalism, not the leak.** "As reported by VGC" — not "as seen in the leak."
3. **Label unverified as unverified**, every time, and preserve hedges verbatim.
4. **Report the enforcement context** (DMCA, subpoenas) — it is the legitimate news story.
5. **Seek comment and disclose non-response.**
6. **Retract fast, loudly, and signed.** Insider Gaming's same-weekend retraction is the standard.
7. **Do not launder the leaker's message.** CyberLeek's clips carried a manifesto and **memecoin solicitations**; repeating the demands as news does the leaker's marketing.

**Bot implementation checklist:**

- [ ] Never post a URL that resolves to leaked media. Strip and re-host nothing.
- [ ] **Suppress Discord embeds** on all leak-derived items (`<url>` or `suppress_embeds`) — auto-unfurl can pull a leaked thumbnail even from a responsible article.
- [ ] Never attach images to leak items. Text only.
- [ ] Mandatory prefix: `🟡 RUMOUR —` and mandatory attribution: `Reported by <Tier 2 outlet>.`
- [ ] Mandatory footer on leak-derived items: *"Describes claims reported by the press. This server does not link to or host leaked material. Unverified; Rockstar has not commented."*
- [ ] Never name the leaker's handles or channels. Say "a leaker" — naming them aids discovery and, given that the subpoenaed handles were **impostors**, may misattribute.
- [ ] Never repeat memecoin/crypto/manifesto content in any form.
- [ ] Cap leak-derived items at RUMOUR permanently, even if 10 Tier-2 outlets describe them.
- [ ] Run the retraction watch (§4.4) and post corrections in-channel.
- [ ] Prefer the **enforcement story** (DMCA, §512(h) subpoenas, Reddit warnings) over the leak contents — it is Tier-2-sourceable, legally safe, and genuinely more newsworthy.

### 6.4 A direct warning for this server

The Discord subpoena sought identifying information for **every account that was a member of, or communicated with, three named servers between 1 June 2026 and the present** — not only uploaders. Combined with the Microsoft subpoena for **Windows device IDs and OneDrive content**, and the fact that Take-Two issued a **cease-and-desist over AI *recreations*** (GTASixJoker), the exposure surface for a GTA Discord that reposts this material is real and current.

**The community's editorial rule is the correct one, and it is also the cheapest available insurance.** The bot should enforce it mechanically rather than relying on moderator judgement.

---

## 7. GAPS AND UNRESOLVED ITEMS

Stated explicitly so nothing here reads as more certain than it is.

| Item | Status |
|---|---|
| "Videotech" as a GTA source | **Existence not established.** Not in config. |
| Jeff Grubb, Liam Robertson — GTA record | **No GTA-specific evidence found.** Tier 4 default, not Tier 2/3. |
| Fabricated Zelnick quote | **No documented instance found.** The real pattern is hedge-stripping (§5.9). |
| Polygon, Eurogamer — GTA track record | **None found.** Rated on general standards only; Polygon is provisional. |
| GTABase, Rockstar Universe, GTANet, MP1ST — reporting record | **None found.** Unrated for breaking news. |
| Take-Two official X handle | **Not verified.** Omitted from Tier 1 rather than guessed. |
| Discord server names in the subpoena | `[MED]` — from search summaries; the fetched TorrentFreak text did not enumerate them. Verify before publishing. |
| Preload/unlock times, "25 files / 7.54 GB" breach figure, "Cfx Marketplace Jan 2026" | `[LOW]` — aggregator-sourced. Verify against first-party before using as baseline. |
| Feb 2026 hoax creator; the fake-announcement YouTuber | **Names not established.** Left unnamed. |
| Tez2's record | No systematic audit exists; one strong verifiable hit. `[MED]`. |
| Kotaku, GameSpot, Tom's Hardware, VGC, Push Square, dotesports, godisageek, PC Gamer analysis, Netflix Tudum | Returned **403 or truncated** on fetch — assessed via search summaries plus successfully fetched adjacent coverage. Plan RSS/API ingestion; several of these will block a naive scraper. |

---

## 8. SOURCES CONSULTED

**Fetched in full:**
- https://torrentfreak.com/take-two-expands-gta-6-leak-hunt-with-dmca-subpoenas/
- https://www.gtaboom.com/two-outlets-just-walked-back-on-their-gta-6-claims-c2b8
- https://www.gtaboom.com/no-gta-6-is-still-not-coming-to-the-nintendo-switch-2-503a
- https://www.engadget.com/2239548/gta-6-gameplay-leak-august-2026/
- https://insider-gaming.com/redacted-gta-6-leaker-report-build-release/
- https://www.gamefile.news/p/gta-vi-week-of-leaks
- https://www.notebookcheck.net/GTA-6-Alleged-gameplay-leaks-turn-out-to-be-an-AI-hoax.1173045.0.html
- https://www.notebookcheck.net/GTA-6-Vice-City-bridge-leak-confirmed-fake-as-creator-reveals-how-it-was-made.1252353.0.html
- https://www.thegamer.com/gta-6-leaks-years-old/
- https://driffle.com/blog/gta-6-leaks/

**Fetch attempted, blocked (403) or truncated:**
- https://kotaku.com/real-gta-6-leaks-are-hard-to-spot-in-2026-due-to-all-the-ai-fakes-2000726212
- https://www.gamespot.com/articles/microsoft-and-discord-subpoenaed-in-gta-6-leak-case/
- https://www.videogameschronicle.com/news/gta-6-gameplay-allegedly-leaks-ahead-of-planned-netflix-reveal/
- https://www.pcgamer.com/games/grand-theft-auto/gta-6-video-leak-analysis-august-2026/
- https://www.tomshardware.com/video-games/console-gaming/take-two-subpoenas-microsoft-for-windows-device-ids-of-everyone-in-three-discord-servers-in-gta-6-leak-hunt
- https://www.gamesradar.com/games/grand-theft-auto/gta-6s-leaks-prove-ai-disinformation-is-more-rampant-than-you-think/
- https://www.rockstargames.com/newswire/article/9k2kaa1o3297k9/grand-theft-auto-vi-an-extended-look
- https://www.netflix.com/tudum/articles/grand-theft-auto-6-extended-first-look
- https://www.pushsquare.com/news/2026/08/gta-6-gameplay-leaks-continue-as-group-makes-demands-of-rockstar
- https://dotesports.com/gta/news/gta-6-leak-gameplay-jason-footage-driving-rockstar
- https://godisageek.com/2026/08/gta-6-leak-leonida-map-cyberleek/

**Referenced via search results (leak wave, Aug 2026):**
- https://www.dexerto.com/gta/gta-6-gameplay-and-map-seemingly-leaked-ahead-of-netflix-extended-look-3399751/
- https://kotaku.com/gta-6-gameplay-and-a-full-map-have-seemingly-leaked-ahead-of-the-big-netflix-reveal-2000725468
- https://kotaku.com/fans-debate-whether-gta-6-looks-mid-in-new-alleged-leak-as-insider-claims-its-from-more-than-a-year-ago-2000725804
- https://kotaku.com/take-two-subpoenas-microsoft-and-discord-records-related-to-spread-of-gta-6-leaks-2000726633
- https://rockstarintel.com/grand-theft-auto-vi-entire-map-gameplay-leaked/
- https://rockstarintel.com/news-9th-leaked-gameplay-video-shows-us-the-wasted-screen/
- https://hothardware.com/news/gta-6-leaker-defies-take-two-with-even-more-secret-gameplay-footage
- https://www.pcgamer.com/games/grand-theft-auto/former-rockstar-dev-says-the-gta-6-leaks-are-a-nothing-burger-there-wont-be-much-damage/
- https://www.nme.com/news/gaming-news/grand-theft-auto-6-leaks-tiny-blip-former-rockstar-developer-3964585
- https://www.notebookcheck.net/Recent-GTA-6-leaked-footage-is-reportedly-over-a-year-old-claims-insider.1372180.0.html
- https://sportskeeda.com/gta/news-take-two-issuing-dmca-notices-youtube-gta-6-leak-videos
- https://x.com/GTA6_HQ/status/2090587114551366028

**Release date, platforms, delays, official announcements:**
- https://www.rockstargames.com/newswire/article/9k2kaa1o3297k9/grand-theft-auto-vi-an-extended-look
- https://x.com/RockstarGames/status/2085335127287030232
- https://www.netflix.com/title/83035795
- https://gameinformer.com/2026/08/06/grand-theft-auto-vi-is-getting-an-extended-look-on-netflix-august-27
- https://gamedaily.com/games/how-to-watch-gta-6-extended-look-netflix
- https://www.pushsquare.com/guides/gta-6-netflix-extended-look-when-and-how-to-watch
- https://variety.com/2025/gaming/news/gta-6-release-delayed-november-2026-1236571679/
- https://deadline.com/2025/11/grand-theft-auto-6-release-delayed-2026-1236383846/
- https://www.espn.com/gaming/story/_/id/46874180/grand-theft-auto-6-vi-release-date-delay
- https://variety.com/2026/gaming/news/gta-6-price-single-player-pre-orders-1236789407/
- https://www.cnbc.com/video/2026/08/10/take-two-ceo-strauss-zelnick-on-gta-6-i-believe-we-will-exceed-expectations.html
- https://www.psu.com/news/gta-vi-pre-order-details/
- https://www.techradar.com/gaming/take-two-ceo-is-pleased-the-gta-6-trailer-broke-the-internet-but-found-the-leak-disappointing

**2022 hack / Kurtaj:**
- https://www.pcgamer.com/games/grand-theft-auto/grand-theft-auto-6-leaker-who-was-given-an-indefinite-sentence-in-2023-because-he-wouldnt-stop-hacking-is-now-out-of-hospital-and-awaiting-retrial/
- https://www.cbsnews.com/news/grand-theft-auto-leak-teen-hacker-hospitalized/
- https://www.siliconrepublic.com/enterprise/gta-6-hacker-life-hospital-prison-lapsu-arion-kurtaj
- https://www.techradar.com/gaming/teenager-involved-with-hack-which-led-to-gta-6-leak-court-finds
- https://www.gamespot.com/articles/gta-forums-remove-gta-6-leak-posts-to-avoid-being-obliterated-by-take-two/1100-6507636/
- https://www.gamesradar.com/gta-6-forums-clean-house-of-massive-leak-to-avoid-being-obliterated-by-rockstar/
- https://www.videogameschronicle.com/news/take-two-clears-out-gta-6-forum-and-subreddit-following-leak/

**April 2026 ShinyHunters breach:**
- https://www.engadget.com/cybersecurity/rockstar-games-has-confirmed-it-was-hit-by-third-party-data-breach-175112621.html
- https://www.gamespot.com/articles/ahead-of-gta-6-rockstar-hacked-by-ransomware-group-again/1100-6539360/
- https://www.computerweekly.com/news/366641486/Grand-Theft-Auto-publisher-Rockstar-hit-by-hackers-again
- https://kotaku.com/rockstar-games-reportedly-hacked-massive-data-leak-ransom-gta-6-shinyhunters-2000686858

**Journalists / insiders:**
- https://en.wikipedia.org/wiki/Jason_Schreier
- https://muckrack.com/jasonschreier
- https://www.gamespot.com/articles/new-gta-6-delay-rumor-shot-down-by-reporter-says-statement-was-misconstrued/1100-6537283/
- https://www.thegamer.com/gta-6-delay-rumours-jason-schreier-says-misleading/
- https://www.gtaboom.com/no-jason-schreier-did-not-say-gta-6-is-almost-complete-5bd4
- https://www.tweaktown.com/news/109641/jason-schreier-on-gta-6-the-last-i-heard-it-was-still-not-content-complete/index.html
- https://www.gamefile.news/archive
- https://www.gamefile.news/p/my-visits-to-rockstar-games
- https://en.gamegpu.com/news/igry/fanaty-usomnilis-v-dostovernosti-insajdov-toma-khendersona-o-grand-theft-auto-vi
- https://gamingbolt.com/gta-6-content-ready-claims-insider-tom-henderson
- https://www.notebookcheck.net/Insider-claims-GTA-6-is-content-ready-and-doesn-t-expect-another-release-date-delay.1158411.0.html
- https://x.com/Chris_Klippel/status/2091144380610498817
- https://x.com/Chris_Klippel/status/2042907298222256261
- https://rockstarintel.com/digital-foundry-reacts-to-gta-6-trailer-astonishing-detail-but-60fps-mode-unlikely/
- https://www.gtaboom.com/digital-foundry-expresses-confidence-in-gta-6-peformance-on-ps5-pro-cfb6
- https://www.sportskeeda.com/gta/news-gta-6-hit-720p-xbox-series-s-per-popular-analyst
- https://www.gtaboom.com/a-gta-6-dev-told-schreier-to-stay-away-and-then-vanished-57b7
- https://www.tweaktown.com/news/111646/rockstar-games-will-not-send-gta-6-review-copies-to-journalists-and-media-claims-insider/index.html

**Specialist / aggregator sites assessed:**
- https://rockstarintel.com/ , https://rockstarintel.com/rockstarintel-acquires-rockstar-universe/
- https://rockstarintel.com/gta-6-previews-are-happening-right-now-its-claimed/
- https://rockstarintel.com/gta-6-missed-release-date-targets-new-report-online-mode/
- https://rockstarintel.com/text-chat-will-return-in-gta-v-enhanced-datamine-reveals/
- https://www.gtabase.com/ , https://x.com/GTABase/status/1811038719652045166
- https://gta.fandom.com/wiki/Grand_Theft_Auto_VI/Leaks
- https://www.sportskeeda.com/gta , https://www.sportskeeda.com/gta/gta-6-leaks

**Fakes, hoaxes, AI disinformation:**
- https://www.pushsquare.com/news/2025/11/gta-6-gameplay-leaks-are-ai-generated-nonsense-creator-owns-up-after-backlash
- https://www.dexerto.com/gaming/creator-of-viral-ai-made-gta-6-gameplay-speaks-up-amid-backlash-3287538/
- https://www.gtaboom.com/the-gta-6-ai-fake-problem-just-got-its-latest-legal-takedown-779e
- https://www.sportskeeda.com/gta/take-two-sends-cease-desist-fan-spreading-gta-6-ai-content
- https://www.gtaboom.com/report-alleged-gta-6-developer-may-have-leaked-a-ton-of-details-87b9
- https://www.techradar.com/news/how-this-youtuber-pulled-off-the-elaborate-gta-6-fake-announcement
- https://www.techradar.com/news/gta-6-florida-and-cuba-setting-rumor-has-been-debunked
- https://sportskeeda.com/gta/news-fake-gta-6-leak-surfaces-online-turns-something-else
- https://x.com/Patrick21611/status/2066792797286355300

**Switch 2 / PC / Online / RP baseline:**
- https://www.gtaboom.com/the-gta-6-switch-2-rumor-just-fell-apart-1968
- https://www.gtaboom.com/gta-6-on-switch-2-never-why-3c5c
- https://gameranx.com/updates/id/561923/article/heres-what-the-original-sources-are-saying-about-the-gta-6-switch-2-rumor/
- https://www.vice.com/en/article/gta-6-switch-2-edition-reportedly-leaked-but-fans-are-skeptical/
- https://www.gtaboom.com/no-gta-6-has-not-been-delayed-to-2027
- https://www.ibtimes.co.uk/gta-6-release-date-rumours-2027-delay-1798040
- https://www.ibtimes.co.uk/rockstar-vs-4chan-truth-behind-2027-gta-6-delay-rumours-trashing-fan-forums-1798145
- https://www.threads.com/@dexerto/post/DUUAQ4SlYyz/
- https://www.msn.com/en-us/news/other/gta-rp-servers-are-evolving-with-official-partnerships-racing-trends-and-creative-in-game-events/gm-GM7056C2AE

**Casting rumours:**
- https://www.nme.com/news/gaming-news/grand-theft-auto-6-voice-actors-jason-lucia-3861439
- https://screenrant.com/gta-6-jason-voice-actor-speculation/
- https://www.techradar.com/gaming/consoles-pc/voice-actor-troy-baker-may-have-shot-down-rumors-of-gta-6-involvement-but-fans-may-have-uncovered-the-true-identity-of-the-protagonist
- https://thedirect.com/article/gta-6-cast-characters-voice-actors-leaks-rumors

**Parasite-SEO / content-farm examples (documented as blocklist evidence — do NOT ingest):**
- https://widescope.stanford.edu/gta-6-leaked , https://widescope.stanford.edu/gta-6-map-leak
- https://smi.engin.umich.edu/gta-6-leaked , https://smi.engin.umich.edu/gta-6-gameplay-leak
- https://commons.open.uci.edu/gta-6-leaks
- https://cuentame.coe.arizona.edu/gta-6-gameplay-leak
- https://ftp.dia.ucla.edu/gta-6-gameplay-leak
- https://eduadmin.fortune.com/gta-6-leaked
- https://smallbiz.monster.com/gta-6-leaked , https://smallbiz.monster.com/gta-6-map-leak
- https://gtanerd.com/gta-6/release-date/ , https://gta6tricks.com/guides/gta-6-release-date
- https://www.gtavispot.com/news/gta-6-release-date/ , https://tech-insider.org/gta-6-release-date-november-2026/
- https://pcgamecheck.com/blog/gta-6-release-countdown-date-time-2026 , https://www.gtaboss.gg/gta-6/guides/gta-6-release-date
- https://thepcenthusiast.com/gta-6-release-date-confirmed/ , https://gtasixguide.com/news/gta-6-delay-history-timeline/
- https://gta6index.com/news/gta-6-delay-explained/ , https://www.gamermarkt.com/blog/gta-6-all-characters-confirmed-full-list/
- https://sundayguardianlive.com/tech-news/gta-6-cast-leaks-grand-theft-auto-vi-voice-actors-confirmed-new-actor-surfaces-ahead-of-rumoured-trailer-3-heres-the-rumoured-voice-cast-behind-lucia-jason-brian-heder-and-more-243637/
- https://timesaver.gg/blog/gta-6-online-multiplayer-confirmed-2026 , https://games.gg/news/gta-6-single-player-only-launch/
- https://gta6-rp-servers.com/en/fivem-gta-6 , https://www.var-fivem.com/en/guides/fivem-gta-6 , https://ilovegta6.com/en/article/gta-6-fivem-mods-serveurs/
- https://www.wikigtavi.com/guides/leaks , https://bitsfrombytes.com/gta-6-leaks-verified-updates/
- https://shattered.io/rockstar-games-shinyhunters-breach-2026/ , https://www.explainx.ai/blog/are-gta-6-leaks-ai-generated-cyberleek-august-2026
- https://www.studioglobal.ai/discover/answers/what-is-known-about-cyberleek-s-week-long-campaign-6a8b4d54c58ffda6d9b2dd97
- https://drezzed.clownfishtv.com/p/gta-6-leakers-dead-mans-switch-story
- https://www.shanethegamer.com/nintendo/gta-6-leak-report-on-cyberleek-dead-mans-switch-retracted-as-fake/
- https://cosmicbook.news/gta-6-pre-orders-vastly-beat-take-two-forecasts

---

## 9. READY-TO-PASTE BOT CONFIG (YAML)

```yaml
# =====================================================================
# gta6-news-bot :: source credibility config
# Generated 2026-08-25. Re-audit after 2026-11-19 (launch changes everything).
# =====================================================================

meta:
  version: 1
  compiled: "2026-08-25"
  reaudit_after: "2026-11-19"

# ---------------------------------------------------------------------
# FACTUAL BASELINE — used by the contradiction gate (G4)
# ---------------------------------------------------------------------
baseline:
  release_date: "2026-11-19"
  platforms: ["PS5", "Xbox Series X", "Xbox Series S"]
  setting: "Leonida / Vice City"
  protagonists: ["Jason", "Lucia"]
  official_framing: "single player experience"
  preorders_opened: "2026-06-25"
  price_usd: {standard: 79.99, ultimate: 99.99}
  extended_look:
    netflix: "2026-08-27T15:00:00-04:00"
    rockstar_youtube: "2026-08-27T21:00:00-04:00"
    runtime: null            # NOT ANNOUNCED — BBC's "30 minutes" was retracted
  delays_official: ["2025-05-02 -> 2026-05-26", "2025-11-06 -> 2026-11-19"]

  not_announced:             # any non-tier1 source asserting these as fact = DROP
    pc_version: true
    pc_release_date: true
    switch2_version: true
    online_mode: true
    gta_online_2: true
    mod_support: true
    fivem_rp_support: true
    voice_cast: true
    extended_look_runtime: true
    review_copies_policy: true

  contradiction_patterns:    # regex, case-insensitive
    - "delayed?\\s+(to|until|into)\\s+20(2[7-9]|3\\d)"
    - "(coming|confirmed|announced|releasing)\\s+(for|on|to)\\s+(nintendo\\s+)?switch\\s*2"
    - "pc\\s+(version|release|port)\\s+(confirmed|announced|dated)"
    - "pc\\s+release\\s+date\\s+(confirmed|announced|revealed)"
    - "(gta\\s*6\\s*online|gta\\s*online\\s*2)\\s+(confirmed|announced|dated|detailed)"
    - "(fivem|roleplay|rp\\s+servers?|mod\\s+support)\\s+(confirmed|announced|supported)"
    - "(voice\\s+)?cast\\s+(confirmed|revealed|official)"
    - "dead\\s*man'?s\\s+switch"
    - "full\\s+(playable\\s+)?build\\s+(release|leak|drop)"
    - "extended\\s+look\\s+(is|will\\s+be)\\s+\\d+\\s*(-|\\s)?minutes?"

# ---------------------------------------------------------------------
# TIERS
# ---------------------------------------------------------------------
tiers:

  tier1:                     # first-party only. post as FACT.
    base_score: 100
    domains:
      - rockstargames.com
      - support.rockstargames.com
      - take2games.com
      - sec.gov
      - store.playstation.com
      - xbox.com
    handles:
      - "@RockstarGames"
    youtube:
      - "youtube.com/@RockstarGames"
    scoped:
      netflix.com: ["extended_look"]      # tier1 ONLY for the Extended Look

  tier2:                     # reputable press. see corroboration_rule.
    base_score: 60
    domains:
      - bloomberg.com
      - gamefile.news
      - videogameschronicle.com
      - pcgamer.com
      - gamespot.com
      - kotaku.com
      - engadget.com
      - tomshardware.com
      - gamesradar.com
      - gameinformer.com
      - eurogamer.net
      - ign.com
    business_scoped:         # tier2 for corporate/financial facts ONLY
      - variety.com
      - deadline.com
      - espn.com
      - cnbc.com
      - fortune.com          # NB: eduadmin.fortune.com is hijacked -> tier5
      - computerweekly.com
      - reuters.com
      - wsj.com
    topic_scoped:
      torrentfreak.com: ["copyright", "dmca", "legal"]
      "eurogamer.net/digitalfoundry": ["technical", "performance"]
      "youtube.com/@DigitalFoundry": ["technical", "performance"]
    caveats:
      bbc.com:
        tier: 2
        require_corroboration_for: ["product_specifics", "runtime", "features", "dates"]
        note: "Retracted 'Extended Look is a 30-minute special' (Aug 2026), no official source."
      ign.com:
        news: 2
        guides_and_hubs: 3
        note: "Evergreen 'everything we know' pages are SEO, not news."
      polygon.com:
        tier: 2
        provisional: true
        note: "No GTA-specific track record found. Rated on general standards only."
      bloomberg.com:
        written_articles: 2
        verbal_or_podcast_relay: 3
        note: "Schreier's spoken remarks are routinely hedge-stripped into false delay stories."

  tier3:                     # specialist / aggregator. HOLD; needs 1x tier2.
    base_score: 25
    domains:
      - insider-gaming.com   # DEMOTED from t2: retracted fabricated-image story 2026-08-22
      - rockstarintel.com
      - gtaboom.com
      - gtaforums.com
      - gtabase.com
      - rockstarmag.fr
      - techradar.com
      - tomsguide.com
      - notebookcheck.net
      - dexerto.com
      - pushsquare.com
      - thegamer.com
      - gameranx.com
      - nme.com
      - screenrant.com
      - psu.com
      - hothardware.com
      - tweaktown.com
      - gamingbolt.com
      - vice.com
    debunk_feed:             # ingest specifically for corrections/debunks
      - gtaboom.com
      - gamespot.com
      - notebookcheck.net

  tier4:                     # rumour surface. never post directly.
    base_score: 0
    subreddits:
      - r/GTA6                # bans leaked content — monitor only, never cite
      - r/GamingLeaksAndRumours
      - r/GrandTheftAutoV
      - r/gtaonline
    handles:
      - "@GTAVI_Countdown"
      - "@GTAVInewz"
      - "@GTA6_HQ"
      - "@GTAVIES"
    domains:
      - sportskeeda.com
      - ibtimes.co.uk        # laundered a 4chan post via a question headline
      - inkl.com
      - gta.fandom.com
      - imdb.com
    people:
      "Tez2":
        verifiable_artifact_claims: 3   # WHOIS/datamine/filing -> verify, then tier3
        hearsay_claims: 4
      "Nate the Hate": 4
      "KiwiTalkz": 4
      "Tom Henderson": 3
      "Jeff Grubb": 4          # UNRATED for GTA — no evidence found
      "Liam Robertson": 4      # UNRATED for GTA — no evidence found
    unrated:                   # do NOT promote without GTA-specific evidence
      - mp1st.com
      - rockstaruniverse.com
      - "Videotech"            # existence as a GTA source not established

  tier5:                     # HARD BLOCK
    base_score: -1000

    documented_fabrication:  # 5A — evidenced incidents
      handles:
        - "@zapactugta6"       # AI fake gameplay, 8M views, admitted (Nov 2025)
        - "Zap Actu GTA6"
        - "@GTASixJoker"       # Take-Two C&D, apologised 2026-04-24
      reddit_users:
        - "u/elefelelen"       # built the Mar 2026 Vice City bridge fake; "tenshi"

    leaker_and_impostors:    # never ingest, never name in output
      handles:
        - "@cyberleek_ar_io"
        - "@cyberleekario"
        - "@MrCyberLeek"
      youtube:
        - "CyberLeeks"
        - "Surfer24k"
        - "Cyberleek_ar_io"
      subreddits:
        - r/GTA6Unmoderated   # hosts leaked media; formally warned by Reddit
      forums:
        - boards.4chan.org    # origin of the "Feb 2027 delay" fabrication

    satire:                  # not malicious; same downstream effect
      handles:
        - "@DiscussingFish"   # GTA6-on-Switch-2 mashup went viral as real

    parasite_seo:            # 5B — hijacked subdomains on legit hosts
      hosts:
        - widescope.stanford.edu
        - smi.engin.umich.edu
        - commons.open.uci.edu
        - cuentame.coe.arizona.edu
        - ftp.dia.ucla.edu
        - eduadmin.fortune.com
        - smallbiz.monster.com

    seo_farms:               # 5C — blocked on STRUCTURAL grounds, not proven fabrication
      domains:
        - gtanerd.com
        - gta6tricks.com
        - gtavispot.com
        - gtaboss.gg
        - gtasixguide.com
        - gta6index.com
        - gta6monitor.com
        - gta6post.com
        - gta6realm.com
        - 6charts.com
        - ilovegta6.com
        - gtagenius.com
        - gtavicentral.com
        - gta6-rp-servers.com
        - var-fivem.com
        - gamelistzone.com
        - tech-insider.org
        - thepcenthusiast.com
        - pcgamecheck.com
        - techwiser.com
        - technwz.com
        - nerdyinfo.com
        - expertgamereviews.com
        - bitsfrombytes.com
        - jeu.video
        - sixhype.com
        - timesaver.gg
        - howtoplayhub.com
        - games.gg
        - gamingpromax.com
        - gfinityesports.com
        - gamermarkt.com
        - sundayguardianlive.com
        - driffle.com
        - eneba.com
        - drawpie.com
        - glitched.online
        - shattered.io
        - ar-pay.com
        - vpesports.com
        - egw.news
        - thepakistanconnect.com
        - thenews.com.pk
        - cosmicbook.news
        - esquireindia.co.in
        - shanethegamer.com
        - theshortcut.com
        - studioglobal.ai
        - explainx.ai
        - drezzed.clownfishtv.com
        - baike.baidu.com
        - namu.wiki
        - ifann.net
        - gamegpu.com
        - tech4gamers.com
        - nsaneforums.com
        - bluntmag.com.au
        - spieltimes.io

# ---------------------------------------------------------------------
# CORRELATED SOURCES — never count as independent corroboration
# ---------------------------------------------------------------------
correlated_groups:
  - [rockstarintel.com, rockstaruniverse.com, gtabase.com]
  - [eurogamer.net, "eurogamer.net/digitalfoundry", ign.com, gamesradar.com]
  - [ibtimes.co.uk, inkl.com]

# ---------------------------------------------------------------------
# HARD GATES — evaluated in order, before scoring
# ---------------------------------------------------------------------
hard_gates:
  - id: G1
    name: blocked_source
  - id: G2
    name: parasite_seo
    rule: "host matches *.edu|*.gov|*.ac.* OR non-gaming corporate subdomain, AND title matches gta-leak clickbait"
  - id: G3
    name: hosts_leak
    media_host_tokens: ["mega.nz", "mediafire", "magnet:", "anonfiles", "pixeldrain", "catbox.moe", "streamable"]
    phrase_tokens: ["watch the full clip", "download here", "link in bio", "mirror", "full video here"]
    note: "A tier2 article that only DESCRIBES passes. Apply this gate to the bot's OUTGOING embed too."
  - id: G4
    name: contradicts_baseline
    rule: "matches baseline.contradiction_patterns AND source_tier > 1"
  - id: G5
    name: scam
    tokens: ["memecoin", "crypto", "token", "giveaway", "free download", "beta key", "early access code", "referral"]
  - id: G6
    name: leaker_origin
  - id: G7
    name: satire
  - id: G8
    name: syndicated_spam
    rule: "normalised title hash shared by >=3 unrelated hosts"

# ---------------------------------------------------------------------
# SCORING
# ---------------------------------------------------------------------
scoring:
  base_by_tier: {tier1: 100, tier2: 60, tier3: 25, tier4: 0, unknown: -30, tier5: -1000}

  positive:
    independent_tier2_corroboration: {weight: 25, cap: 50}
    links_tier1_primary_document: 30
    verified_checkable_artifact: 35
    named_speaker_quote_with_venue: 15
    named_byline: 10
    explicit_attribution_chain: 10
    declines_to_link_leak: 10
    published_correction_on_this_claim: 20

  negative:
    hype_certainty_token_without_tier1_link: -25
    question_mark_headline: -20
    all_caps_token: -15
    evergreen_seo_template: -25
    leak_in_headline: -10
    domain_age_under_180d: -40
    domain_age_180_to_365d: -25
    no_masthead: -25
    affiliate_or_key_reseller: -20
    single_source_unnamed: -20
    origin_anonymous_forum_or_ama: -60
    hedge_stripped_vs_original: -30
    stale_reupload_over_7d: -20
    domain_retracted_gta_claim_last_30d: -20
    correlated_source_counted_as_independent: -25

  media_authenticity:       # apply when item carries claimed-leak media
    too_polished_no_debug_ui: -35        # real in-dev footage looks WORSE than trailers
    ocr_text_error_in_frame: -45         # cf. "poin of interest", Feb 2026
    reverse_image_match_to_promo_art: -50
    hud_map_inconsistency: -30
    burner_or_new_account_provenance: -30
    unnamed_former_rockstar_employee_claim: -35
    no_dmca_after_48h_virality: -20      # LOW confidence, weak tiebreaker only

  hype_tokens: ["CONFIRMED", "OFFICIAL", "FINALLY", "BREAKING", "SHOCKING", "INSANE", "HUGE", "EXPOSED", "REVEALED"]
  evergreen_tokens: ["everything we know", "all we know", "what we know so far", "complete guide", "explained", "here's why", "everything you need to know"]
  allcaps_allowlist: ["GTA", "VI", "PS5", "DLC", "NPC", "RP", "AI", "PC", "FPS", "CEO", "DMCA", "IGN", "VGC", "RDR2", "SEC", "FY", "HUD", "UI", "USA", "TTWO"]

  thresholds:
    post_as_fact: 80
    post_as_rumour: 40
    hold: 0
    drop_below: 0
  hold_ttl_hours: 48

# ---------------------------------------------------------------------
# CORROBORATION RULE
# ---------------------------------------------------------------------
corroboration_rule:
  tier1:                    {action: post_fact,   required: 0,  window_hours: 0}
  tier2_with_tier1_doc:     {action: post_fact,   required: 0,  window_hours: 0}
  tier2_named_source:       {action: post_fact,   required: 0,  window_hours: 0}
  tier2_unnamed_source:     {action: post_report, required: 0,  window_hours: 0,
                             promote_to_fact_with: 1, promote_window_hours: 24}
  tier3:                    {action: hold,        required: 1,  window_hours: 24, tier_of_corroborators: 2}
  tier4:                    {action: hold,        required: 2,  window_hours: 48, tier_of_corroborators: 2}
  tier5:                    {action: never}

  attribute_to: corroborating_tier2_outlet   # NEVER to the tier3/4/5 origin
  leak_derived_max_label: RUMOUR             # absolute cap, ignores score

  independence_test:
    - different_parent_company
    - not_citing_each_other_as_sole_source
    - not_same_single_upstream_origin
    - publication_time_delta_minutes: 20

  retraction_watch:
    recheck_at_hours: [6, 24, 72]
    on_retraction: [post_correction_in_channel, strike_original, log_domain_retraction]

# ---------------------------------------------------------------------
# OUTPUT POLICY — implements the community's editorial rule
# ---------------------------------------------------------------------
output_policy:
  suppress_discord_embeds: true       # auto-unfurl can surface leaked thumbnails
  attach_images_on_leak_items: false
  post_leak_media_urls: false
  name_leaker_handles: false          # also: the subpoenaed handles were impostors
  repeat_manifesto_or_crypto: false
  rumour_prefix: "🟡 RUMOUR — "
  fact_prefix: "🟢 "
  correction_prefix: "🔴 CORRECTION — "
  attribution_template: "Reported by {outlet}."
  leak_footer: >-
    Describes claims reported by the press. This server does not link to or host
    leaked material. Unverified; Rockstar has not commented.
  prefer_enforcement_story_over_leak_contents: true
```

---

*End of document.*
