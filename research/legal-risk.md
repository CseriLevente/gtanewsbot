# GTA 6 News Bot + FiveM RP Server — Legal & Platform Risk Research

**Research date:** 2026-08-24/25
**Subject:** Hungarian GTA 5 FiveM RP community; planned GTA 6 RP server; monetised via Tebex; new Discord with an automated daily GTA 6 news digest in `#news`.
**Decision under stress-test:** *"We will mention leaks, but only describe what is RUMOURED TO HAPPEN based on them — no direct links to leaked material, no reuploads, no embedded leaked images/video."*

> **This is risk research, not legal advice.** I am not a lawyer. Throughout, I mark claims as
> **[LAW]** = statutory text or case law I could cite,
> **[PRACTICE]** = observed enforcement behaviour,
> **[CONTRACT]** = private terms of service (not law, but can kill you faster than law),
> **[THIN]** = evidence weak, single-source, or unverified.
> Where the honest answer is "grey but low-risk", I say so and explain why.

---

## 0. TL;DR — the verdict up front

**Your describe-don't-link rule is the correct call, and it is on solid legal ground.** Describing what a leak revealed is not copyright infringement in Hungary or the US, and Hungarian law says so almost in as many words (Szjt. Art. 1(5): copyright "shall not extend to facts and daily news").

**But the rule protects you from the wrong threat.** Nobody in this saga is being sued for copyright. What is actually happening in August 2026 is:

1. Take-Two is using **DMCA §512(h) subpoenas** to demand identifying data on **every account that communicated in named Discord servers since 1 June 2026** — including servers that, by their owner's account, never hosted a single leaked clip.
2. Platforms (Reddit, Telegram, X, YouTube) are removing content and locking communities pre-emptively, on **[CONTRACT]** grounds, with no court involved.
3. Your RP server runs on a **revocable Rockstar/Cfx.re licence key**. That is the asset with real value, and it can be pulled at Rockstar's discretion for reasons that need not be legal at all.

So the risk is not "we get sued for describing a leak." The risk is **discovery dragnet + platform discretion + licence revocation**, and your news channel is the thing that creates a discretionary reason to look at you. The asymmetry is severe: the `#news` channel earns you nothing, and the RP server earns you money.

**The single most important finding in this document:** see §1.3 (DarkViperAU). A well-known creator whose Discords contained *no leaked clips* was still named by name in Take-Two's subpoena, with his personal Discord data demanded. Clean hands did not keep him out of the filing.

---

## 1. THE LIVE CRACKDOWN — verified timeline

All dates 2026 unless stated. This section is **[PRACTICE]** except where marked.

### 1.1 The leak wave

| Date | Event | Source |
|---|---|---|
| **Aug 18** | An entity calling itself **"Cyberleek"** begins posting unreleased GTA 6 gameplay. Early clips show Jason playing basketball, driving Leonida streets, police reactions. A **full Leonida map** (reportedly 5 counties, one more than previously known) circulates. | GameSpot, Insider Gaming, Notebookcheck |
| **Aug 18 onward** | Rockstar issues DMCA takedowns "at remarkable speed" against accounts and sites **sharing** the leaks, **including those who published images of the in-game map**. Posts on X removed via copyright complaints. Reddit posts removed with "removed by Reddit's Legal Operations team". | DualShockers, GameSpot |
| **Aug 21** | **Bloomberg / Jason Schreier newsletter: "Rockstar Rattled As 'Grand Theft Auto VI' Leaks Again."** Rockstar has **not** identified the leaker or the breach vector. Internally "all hands on deck"; leadership and staff angry, frustrated, exhausted. No plans to move the Aug 27 premiere. Notes post-2022 security measures included **ending remote work** (return to office 5 days/week) — and it "didn't work". | Bloomberg (paywalled); corroborated via @iGrandTheftAuto, egw.news |
| **Aug 21** | Forbes: "The 'GTA 6' Leaker Is Leaking Again, Ending Rumors Of Being Caught." | Forbes |
| **Aug 22** | **Eurogamer: "Is this the end of the GTA 6 leaks? Take-Two's legal crusade appears to shut down the hubs behind them."** *(Headline verified; I reached it via the drimble.nl aggregator — I could not fetch Eurogamer directly.)* | Eurogamer via drimble.nl |
| **Aug 22–23** | Cyberleek's last working mirror returns **502**; the **Telegram channel is pulled for copyright infringement**. Described as "the most complete disruption of Cyberleek's distribution channels since the leaks began." | Notebookcheck |
| **After the blackout** | Leaks resume. New mirrors appear. **Two new official Telegram channels** open. A 7th leak set appears on Reddit; an 8th reportedly shows a strip club and a cutscene. Leaker threatens Lucia/prologue story spoilers and to "drop big files"; also threatens to leak from other developers. | Notebookcheck, GameDaily, RockstarINTEL, GamesRadar, ixbt |
| **Context** | Leaked footage carried a **"BUY $CYBERLEEK ON SOLANA"** watermark — i.e. the leaker is running a crypto pump alongside the leak. | TorrentFreak |

**Timing context that matters:** GTA 6 releases **19 November 2026** (PS5 / Xbox Series X|S). The official ~30-minute gameplay "Extended Look" premiered/premieres **27 August 2026**, Netflix-exclusive for six hours, then Rockstar's YouTube. So the leak wave lands in the most commercially sensitive window Rockstar has — days before its own showcase, ~3 months before launch. **[PRACTICE]** Expect maximum enforcement aggression through November, not a cooling-off.

### 1.2 The legal machinery — what Take-Two actually filed

**Nobody has been sued.** These are **DMCA §512(h) subpoenas**, which let a copyright holder compel a service provider to identify an alleged infringer **without filing a lawsuit first**. **[LAW]**

**Aug 20** — two requests filed in the **U.S. District Court for the Southern District of New York**. Orders signed by Judges **Andrew L. Carter Jr.** and **Jennifer L. Rochon**. Compliance deadline **September 4**.

**From Discord**, Take-Two demanded "all identifying information associated with all user accounts" in three named servers since **June 1, 2026**, covering **"every account that communicated"** in those spaces:

| Server | Guild ID |
|---|---|
| Ødyssey.gg (created 19 June 2026) | 1517326120867991592 |
| "! Odyssey" | 1127436882800816149 |
| **DarkViperAU** | 268280696601051136 |

Named Discord users include **CYBERLEEK** and **CINEMATICROCKSTAR**. Data sought: original message logs, IP access logs, email addresses, phone numbers, connected accounts (**Google, Xbox**), backend metadata and telemetry, device identifiers.

**From Microsoft:** **MachineGuid** and **MSA device identifiers**, registration and last-login IPs, phone numbers, linked Google/Xbox connections, and **OneDrive contents**.

**From GitHub** (via Microsoft): Take-Two demanded a repository be killed outright — *"The entire repository must be completely disabled, there are no remedies to rectify this clear case of infringement."*

**One day later**, a second wave: **X Corp** (three accounts — account IDs, registration emails, IP access logs, phone numbers, device identifiers) and **Google/YouTube** (one video, three channels: **CyberLeeks, Surfer24k, Cyberleek_ar_io**).

Take-Two's sworn declaration states the purpose is "to obtain the identity of an alleged infringer or infringers, and that such information will only be used for the purpose of protecting Take-Two's rights."

**Discord's response (Aug 24):** it had **not yet been served**, and *"When we do, we'll evaluate the validity and scope before responding."* **[PRACTICE]** That is a company signalling it may push back on scope — but it is not a promise, and you should not plan around it.

**TorrentFreak's own scope critique** — worth quoting because it is the crux: many targeted Discord users may have **"posted nothing at all"**, which raises the question whether a dragnet this broad complies with §512(h)'s limitation to identifying *"alleged infringers."* **[LAW, contested]** This is a genuine legal weak point in Take-Two's filing — but "the subpoena was arguably overbroad" is cold comfort if your data is already handed over.

### 1.3 ⚠️ The finding that should change your behaviour: DarkViperAU

**DarkViperAU** (Matthew Judge), a long-established GTA content creator, was **named by name** in the subpoena, and his server was listed. His response on X:

> "Take-Two has filed multiple subpoenas seeking info to catch the GTA 6 leaker. They're asking for my discord info, I'm mentioned by name. — I don't know anything. — That isn't my editors discord. — **There aren't even any clips of the leaks in either of my Discords.**"

He added that the leaker *may* have visited his Discord but he isn't sure, and that Rockstar had not emailed him — he inferred that if they thought he knew something, they'd have reached out.

**Why this matters more than anything else in this document:**

Judge did exactly what you plan to do. His communities discussed GTA 6. They did not host leaks. **He was still swept into a federal subpoena, by name, with his personal Discord metadata demanded.** The mechanism was not "you infringed" — it was "the leaker may have passed through your community, so give us everything on everyone in it since June 1."

**[PRACTICE]** Conclusion: *describe-don't-link protects you from liability, not from process.* Your legal exposure is genuinely low. Your **discovery exposure** — your members' IPs, emails, phone numbers, linked Google/Xbox accounts and device IDs landing in a Take-Two filing — is **not** controlled by whether you link anything. It is controlled by whether the leaker or leak-spreaders are *present in your server*. That is a **moderation** problem, not a phrasing problem.

### 1.4 Did anyone get actioned merely for DISCUSSING leaks?

This was a priority question. My honest answer: **not clearly, and the one source claiming otherwise does not hold up.**

- **[THIN — do not rely on this]** Notebookcheck states: *"Rockstar filed legal action against social media posts making text comments about leaks, not just those sharing footage."* I could **not corroborate this in any other outlet**, and I searched specifically for it. The X/YouTube subpoenas I *can* verify targeted **Cyberleek's own accounts and channels** — accounts that unquestionably posted footage. I believe this is most likely a mischaracterisation of those subpoenas. **Flagging it because if it were true it would materially weaken your plan** — treat as unconfirmed, and monitor.
- **[THIN]** DualShockers says Rockstar "targeted high-profile community accounts on X that are best-known for sharing GTA information," but names none and does **not** distinguish hosting from discussing.
- **[PRACTICE — verified and useful]** The clearest signal runs the *other* way, and it is a near-perfect natural experiment:

  - **r/GTA6** moderators prohibited posting **any** leaked content, "including directly shared material **or links to sources of leaks**." (Policy hardened after the March 2023 leak wave; the sub had previously had to lock down under a flood of takedown notices.) The subreddit **survives** and discusses leaks as news.
  - **r/GTA6Unmoderated** allowed **videos and images** from the leak, briefly became the largest GTA 6 subreddit (~1M weekly visits) — and was **officially warned by Reddit** and **put into lockdown**. Reportedly at Rockstar's instigation.

  **Two communities, same subject matter, opposite policies, opposite outcomes.** The one that banned media *and links* lived. The one that hosted media died. That is direct empirical support for your rule — with the DarkViperAU caveat that surviving as a *community* is not the same as staying out of a *subpoena*.

- **[PRACTICE]** Reddit/Telegram/X removals happened on **platform** authority, fast, with no court. Platform discretion is the fast-moving threat; law is the slow one.

---

## 2. THE DESCRIBE-DON'T-LINK LINE — is it actually safe?

### 2.1 Copyright: the idea/expression dichotomy

**[LAW] Hungary — Act LXXVI of 1999 on Copyright (Szjt.), as published by WIPO Lex:**

- **Art. 1(5):** *"Copyright protection shall not extend to facts and daily news underlying announcements released in the press."*
- **Art. 1(6):** *"Ideas, principles, theories, procedures, operating methods and mathematical operations shall not be the subject matter of copyright protection."*

These two provisions are, for your purposes, close to a direct answer. "GTA 6 reportedly has a basketball minigame; the leaked map reportedly shows five counties in Leonida" is a **fact about a work**, not the work. Reporting it reproduces **no protected expression**.

**[LAW] United States:** same result by a different route — 17 U.S.C. §102(b) (no protection for ideas, procedures, concepts, discoveries) plus *Feist* (facts are not copyrightable). You would not even need fair use, because there is no *prima facie* reproduction to excuse. Fair use is the fallback if you reproduce expression (a screenshot, a clip, a long verbatim quote).

**Where the line actually is:** infringement attaches to **fixed expression**. Therefore:

| Act | Reproduces protected expression? | Copyright risk |
|---|---|---|
| "Leak reportedly shows a basketball minigame" | No | **Effectively nil** |
| "The leaked map reportedly shows 5 counties" | No | **Effectively nil** |
| Your own prose describing a leaked scene | No | **Effectively nil** |
| Embedding/reuploading the leaked clip or map image | **Yes** | **High — direct infringement** |
| A frame-grab, crop, or thumbnail of leaked footage | **Yes** | **High** |
| Hotlinking the leaked file from another host | Communication to the public (EU); contributory (US) | **High** |
| A link to a page hosting it | No reproduction, but see §2.4 | **Moderate — platform risk dominates** |
| **A meticulous shot-by-shot transcript of a leaked cutscene** | **Arguably yes** | **Grey — see below** |
| **An AI-generated "recreation" of leaked imagery** | **Yes** | **High — see §2.6 and §3** |

**⚠️ The one place your rule can quietly fail:** description can become so exhaustive that it starts carrying the protected expression itself. A beat-by-beat retelling of a leaked cutscene, full dialogue transcription, or a redrawn/traced copy of the leaked map is no longer "a fact about the work" — it is a **detailed derivative account of the work's expression**. **[LAW — grey]** There is no bright line. Plot points and mechanics are facts; **dialogue is expression**, and a **map redrawn from the leaked map is a derivative of the map**.

Practical rule: **describe at the level of "what happens", never at the level of "how it is written or drawn."** No dialogue transcripts. No redrawn maps. No frame-by-frame.

### 2.2 EU/Hungarian quotation and news-reporting rights (and why you probably don't need them)

**[LAW] InfoSoc Directive 2001/29/EC Art. 5(3):**
- **(c)** reporting current events, to the extent justified by the informatory purpose, with source and author indicated unless impossible.
- **(d)** quotation for purposes such as criticism or review, of a work **already lawfully made available to the public**, in accordance with fair practice, with source indicated.

**[LAW] Hungarian implementation:**
- **Art. 34(1):** *"Anyone is entitled to quote parts of works – to the extent justified by the character and purpose of the recipient work – by designating the source and the author specified therein."*
- **Art. 36(2):** articles on current economic or political topics may be reproduced/communicated in the press freely, **provided the author has not expressly prohibited such use**.
- **Art. 37:** works may be used freely for the purpose of **providing information on current events**, to the extent justified by that purpose.
- **Art. 33(2)** (the gate on all of the above): free use is permitted *"only so far as it does not conflict with the proper use of the work and does not unreasonably prejudice the legitimate interests of the author."*

**⚠️ Three reasons not to lean on the quotation right for leaked material:**

1. **Art. 5(3)(d) / Szjt. 34 require the work to have been *lawfully* made available to the public.** Leaked GTA 6 footage was **not**. This is the doctrinal soft spot: the quotation exception is a poor fit for stolen material, and Take-Two would argue it is unavailable on its face. **[LAW]**
2. **Art. 33(2) cuts hard here.** Reproducing unreleased gameplay days before Rockstar's own paid-partnership showcase is close to the definition of "unreasonably prejudicing the legitimate interests of the author."
3. **[LAW]** The CJEU's 2019 trio — *Funke Medien* (C-469/17), *Spiegel Online* (C-516/17), *Pelham* (C-476/17) — held that the InfoSoc exceptions are **exhaustive**: press freedom under Art. 11 of the Charter does **not** create a free-standing exception beyond Art. 5. National courts must balance within the listed exceptions, not invent new ones. *Funke Medien* concerned **leaked confidential government documents** and still did not hand the press a blanket licence. **[THIN on detail]** — I could not fetch the Bird & Bird analysis (HTTP 402) and am relying on well-established summaries of these judgments rather than a source I retrieved this session; verify before relying on specifics.

**The good news:** none of this matters *if you never reproduce expression.* Art. 1(5) and 1(6) mean you never need to reach Art. 34 or 37 at all. **This is precisely why describe-don't-link is the right architecture** — it keeps you in the zone where no exception is required, instead of betting on an exception that is doctrinally shaky for stolen material.

### 2.3 Trade secret / misappropriation — a separate and under-appreciated exposure

**[LAW]** Yes, this is a **genuinely separate** cause of action from copyright, and it behaves differently in one alarming respect: **copyright protects expression; trade secret protects the information itself.** Your "we only describe the facts" defence is *strong* against copyright and *weaker* here, because the facts are the protected thing.

**EU Trade Secrets Directive 2016/943:**
- Acquisition, use or disclosure is unlawful where the person **"knew or ought to have known that the trade secret had been obtained directly or indirectly from another person who was using or disclosing the trade secret unlawfully."** **⚠️ Note the reach: this covers *downstream recipients*, not just the thief.** A public news wave means you cannot claim you didn't know.
- **Art. 5** requires member states to dismiss claims where the acquisition/use/disclosure was for **"exercising the right to freedom of expression and information as set out in the Charter, including respect for the freedom and pluralism of the media"**, or to reveal misconduct/wrongdoing in the general public interest.

**Realistic assessment [PRACTICE]:**
- Unreleased game content **probably qualifies** as a trade secret (commercially valuable, secret, subject to protection measures — Rockstar ended remote work over it, which is strong evidence of reasonable protection steps).
- **Once information is genuinely public and widely reported, it stops being secret in practical terms**, and suing the 10,000th republisher is pointless. Take-Two has shown **zero** appetite for trade-secret actions against fans in this wave — every action I found is copyright-based (DMCA takedowns, §512(h) subpoenas).
- **[PRACTICE]** A Hungarian gaming Discord is not a realistic trade-secret defendant. This is a **theoretical** exposure, not a live one. But it is the reason I would **not** advise you to think "facts can never get us in trouble" as a general principle — that is true for copyright, not for trade secrets.
- **Also:** the Art. 5 media-freedom defence is designed for journalism in the public interest. A hype channel for a commercial game server is a *much* weaker fit for it than Bloomberg is. **Don't assume you inherit the press's protections** — see §2.5.

### 2.4 DMCA §512 — is a *description* even a valid takedown target?

**[LAW] No.** A §512(c)(3) notification must identify **the copyrighted work** claimed to be infringed and **the material** claimed to be infringing. A sentence stating a fact about a game is not a copy of any work; there is nothing to remove. A takedown notice against pure description would be defective, and §512(f) exposes knowing material misrepresentation to liability.

**⚠️ But four important caveats:**

1. **§512 is a US safe-harbour framework for *service providers*, not a shield for you.** It structures how Discord/Reddit/X respond. It does not adjudicate your rights.
2. **§512(h) — the subpoena power — does not require a valid takedown of *your* content, or any lawsuit.** It only requires an allegation of infringement somewhere in the chain. This is exactly the tool being used, and it is how a clean server gets named (§1.3).
3. **[PRACTICE] Platforms over-comply.** Automated systems and legal-ops teams remove first and ask later, especially under a flood from a major rightsholder. A description that *sits next to* a link, quotes a headline, or carries a thumbnail can get swept up. **Expect false positives; do not expect §512(f) to help you.**
4. **Counter-notice puts you in the ring.** Filing one requires consenting to US federal jurisdiction. **[PRACTICE]** For a Hungarian hobby community facing Take-Two, filing a counter-notice is almost never the right move — the downside is unbounded and the upside is one restored message.

### 2.5 The precedent question: why do IGN, Kotaku, Eurogamer, Bloomberg get away with it?

They report on GTA leaks constantly, in detail, and have **not** been successfully actioned for **reporting**. Why:

1. **They mostly describe rather than reproduce.** Look closely at this wave's coverage: outlets describe the clips and the map in prose. Where they use imagery, it is overwhelmingly **official** Rockstar assets (trailer stills, key art), not leaked frames. **[PRACTICE]** This is the single biggest reason — *they are already following your rule.* Your instinct matches professional newsroom practice.
2. **Facts aren't copyrightable** (§2.1). Their core output is non-infringing.
3. **Genuine news-reporting/fair-use footing** where they do quote — Art. 5(3)(c) InfoSoc / §107 US fair use, applied to a *bona fide* journalistic purpose.
4. **Institutional deterrence:** media lawyers, insurance, editorial process, and the reputational cost to Take-Two of suing the press.
5. **Suing the press is counterproductive** for a company whose product depends on press coverage.

**⚠️ Does a Discord community get the same protection?**

**Partly on the law; much less in practice.**

- **[LAW]** Points 1 and 2 are **fully yours**. Facts are facts regardless of who states them; Szjt. Art. 1(5) has no press-only limitation. If you never reproduce expression, you are in the same position as IGN.
- **[LAW]** Point 3 is **weaker** for you. The quotation and news-reporting exceptions are calibrated to informatory purpose and fair practice. A channel that exists to hype a **commercial** RP server has a less convincing "informatory purpose" than a newsroom, and **[CONTRACT/LAW]** your monetisation is a fact a rightsholder would point at. Same for the Trade Secrets Directive Art. 5 media-freedom defence.
- **[PRACTICE]** Points 4 and 5 are **not yours at all, and this is the real gap.** Take-Two will not sue Eurogamer. Take-Two will absolutely send a scary letter to, DMCA, or subpoena a fan community — the record in §3 is unambiguous. **You have the newsroom's legal position without the newsroom's deterrent.** That means: match or exceed newsroom hygiene, because you have less margin for error than they do, not more.

### 2.6 Verdict on the decision

**The decision is SOUND. Keep it. It is the correct architecture and it matches what professional outlets actually do.** Specifically:

✅ **On copyright, describing a leak is not infringement.** In Hungary this is near-explicit (Szjt. Art. 1(5)–(6)). You don't even need an exception. Risk: **very low, and this is a statement about LAW, not just practice.**

⚠️ **But the decision does not address your three real risks**, none of which are copyright:
- **Discovery dragnet** (§1.3) — controlled by *who is in your server and what they post*, not by what your bot writes.
- **Platform discretion** (§5) — controlled by whether members post media/links in *any* channel.
- **Licence revocation** (§4) — controlled by Rockstar's goodwill toward your monetised RP server, which is discretionary and unappealable.

**Exact phrasing rules that make it materially safer:**

1. **Attribute to the report, never to the leak.** Write "according to Eurogamer" / "as reported by IGN", not "according to the leaked footage". **Cite the journalism, not the leak.** This is the highest-value single rule: it makes your source a lawful publication, keeps you inside Art. 1(5) facts-reporting, and means every claim has a legitimate provenance trail.
2. **Never link the leak; link the reporting.** A link to Eurogamer is fine and normal. A link to a mirror, Telegram channel, or reupload is the bright line.
3. **Hedge as rumour, always.** "Reportedly", "unverified", "állítólag". Serves double duty: reduces any misrepresentation angle, and protects your credibility when leaks turn out fake.
4. **Facts and mechanics only — never expression.** No dialogue transcripts. No shot-by-shot. No redrawn maps. No "here's every detail visible in frame 14."
5. **Zero leaked imagery, ever — including AI "recreations" and thumbnails.** See §3: Take-Two has actioned a fan account for *AI-generated fakes*. Auto-embeds are the sneaky failure mode (§6).
6. **Add a standing disclaimer** in `#news`: unofficial, fan-run, not affiliated with or endorsed by Rockstar Games or Take-Two; leak items are unverified rumour.
7. **Keep leak coverage a minority of output.** A channel that is 80% official news and 20% hedged rumour is a news channel. A channel that is 80% leaks is a leak hub with a disclaimer — and **[PRACTICE]** enforcement follows *perceived character*, not stated policy. r/GTA6Unmoderated is the cautionary case.
8. **Consider omitting this leak wave entirely until after 27 Aug / into September.** **[PRACTICE]** Highest-heat window of the entire cycle. The official Extended Look gives you abundant legitimate content. Lowest-cost risk reduction available — you lose almost nothing.

**Honest bottom line:** *Describing leaks without linking them is legally low-risk and practically low-risk for the news channel itself. It is not zero-risk for your members' privacy, and it does nothing to protect the RP server, which is where your actual money and exposure are.* Anyone telling you "just describe, don't link, you're fine" is answering the copyright question and ignoring the other three.

---

## 3. TAKE-TWO'S ENFORCEMENT PATTERN

**[PRACTICE]** Chronology of verified actions:

| Date | Target | Action | Outcome |
|---|---|---|---|
| **Aug 2015** | FiveM devs **NTAuthority, qaisjp, TheDeadlyDutchi** | Rockstar Social Club bans; FiveM called "an unauthorized alternate multiplayer service that contains code designed to facilitate piracy" | Banned |
| **Nov 2015** | A banned FiveM dev | **Take-Two reportedly sent private investigators to his home** to pressure him into halting development | ⚠️ Extra-legal pressure, no lawsuit |
| **May–Jun 2017** | **OpenIV** + "Liberty City in GTAV" | 19 May: legal counsel email. 5 Jun: formal **C&D** — OpenIV lets third parties "defeat security features". 14 Jun: OpenIV **stops updates, pulls the software** | Killed without litigation. T2 then publicly said it wasn't targeting single-player mods, blaming mods enabling "harassment of players" and interference with **GTA Online** |
| **2021–2023** | **re3 / reVC** (reverse-engineered GTA III & Vice City) | **Actual lawsuit** | One of very few times T2 truly litigated |
| **Nov 2022** | GTA Online mod policy | Liberalised: mods OK if **non-commercial**, **no IP violation**, **no interference with official online services** | ⚠️ Note the three conditions — they are the template for everything since |
| **Sep 2022** | Rockstar hack (Kurtaj) | 90+ videos leaked; Rockstar confirms hack, "extremely disappointed" | Mass takedowns |
| **Dec 2023** | **Arion Kurtaj** (Lapsus$) | UK: found to have committed the acts (deemed unfit to plead due to autism); **indefinite hospital order** — secure hospital for life unless doctors clear him | The **hacker**, criminally — via the state, not Take-Two |
| **~2024** | Vice City browser port | C&D within about a week | Killed |
| **Apr 2025** | Modder **"Dark Space"** — GTA 5 map mod built from **leaked GTA 6 coordinate data** + trailer shots | **DMCA takedown of the YouTube video**; no prior email. Modder: *"probably a little too accurate"*; removed all download links | ⚠️ **Derivative works from leaks are targets** |
| **Apr 24 2026** | Fan account **GTASixJoker** | **C&D** over **AI-generated images** made to look like leaked GTA 6 screenshots, using Rockstar logos, Trailer 1 character designs, Vice City neon aesthetic, GTA 6 title treatment. Public apology; admitted the images "risked confusing fans with real leaks" | ⚠️ **AI fakes are actioned like real infringement** |
| **Jul 2026** | Kurtaj | Released from secure hospital; **in ordinary prison awaiting retrial, scheduled November 2026** | Ongoing — verify before citing |
| **Aug 2026** | Cyberleek + platforms | DMCA takedowns; **§512(h) subpoenas** to Discord, Microsoft, GitHub, X, Google | Ongoing; no lawsuit filed |

### The observable pattern

**Take-Two hits, in descending order of aggression:**
1. **People who distribute unreleased/leaked material** — fastest, hardest, now with federal subpoenas.
2. **People who make derivative works from leaks** — Dark Space, GTASixJoker. **⚠️ Including AI-generated imitations. Including reconstructions from leaked *data* rather than leaked *files*.**
3. **Tools that defeat technical protection or touch official online services** — OpenIV, FiveM pre-2023.
4. **Reverse-engineered source ports / full-game recreations** — re3/reVC, Vice City browser port. The only category reliably drawing real litigation.
5. **Anything commercial using their IP.**

**Take-Two does NOT hit:**
- **Press reporting on leaks** — zero verified instances of successful action against reporting.
- **Communities that discuss leaks but moderate out the media** — r/GTA6 survives.
- **Non-commercial single-player mods respecting the Nov 2022 conditions.**
- **RP servers operating inside the Cfx.re licence.**

**Three uncomfortable meta-observations [PRACTICE]:**

- **They rarely sue. They don't need to.** C&D, DMCA, platform pressure, and subpoenas achieve compliance at a fraction of the cost. **Your realistic worst case is not a lawsuit — it is a scary letter, a nuked Discord, and a revoked FiveM licence, with no court and no appeal.** Do not calibrate risk to "would we lose in a Hungarian court?" — you'll likely never see a courtroom.
- **They often skip the warning.** Dark Space got a strike, not an email. Judge got named in a subpoena without ever being contacted. **[PRACTICE] Do not count on a warning shot.**
- **Escalation is asymmetric and cheap for them.** A §512(h) subpoena costs Take-Two a filing fee. Responding costs you a lawyer you don't have.

---

## 4. FIVEM / CFX.RE AND THE RP SERVER

### 4.1 The acquisition — confirmed

**[PRACTICE]** Rockstar announced it was working with **Cfx.re** (FiveM/RedM) on **11 August 2023**; Cfx.re said the team "officially became part of Rockstar Games." Cfx.re's **September 2023 Community Pulse** described it explicitly as an **acquisition**. Day-to-day operations were said not to change noticeably, and the work was framed as focused on FiveM/RedM, **not** the next GTA.

**⚠️ Structural consequence you must internalise:** the platform your business runs on is now **owned by the company whose leaks your other channel discusses**. Pre-2023 there was daylight between "Rockstar's IP interests" and "the FiveM platform's interests." **That daylight is gone.** Your RP server and your news channel now face the *same* corporate counterparty. This is the core reason the two projects should be kept at arm's length.

Note the irony and the lesson: Rockstar bought the people it **banned in 2015** and sent **private investigators** after. Positions change; the leverage never did.

### 4.2 Rockstar's Roleplay Server Policy

Original policy **18 November 2022** (article updated 5 Sep 2023). Named as a binding **Creator Policy** under the PLA. **[CONTRACT]**

**⚠️ I could not fetch `support.rockstargames.com/articles/5I66kExWgligszgMCU3XC1/roleplay-rp-servers` directly — it timed out twice.** The text below is quoted from DailyCoin, GameDeveloper, NME and TechRadar, which quote it consistently. **Verify against the live page before acting.**

Prohibited:

1. *"Misuse of Rockstar Games trademarks or game intellectual property"*
2. *"Importation or misuse of other IP in the project, including other Rockstar IPs, real-world brands, characters, trademarks, or music"*
3. *"Commercial exploitation, including the sale of 'loot boxes' for real-world currency or its in-game equivalent. The sale of virtual currencies, generating revenue via corporate sponsorships or in-game integrations, or the use of cryptocurrencies or crypto assets (e.g., 'NFTs')"*
4. *"Making new games, stories, missions, or maps"*
5. *"Interfering with official multiplayer or online services, including Grand Theft Auto Online and Red Dead Online"*

**⚠️ Flag on #4:** read literally, "making new games, stories, missions, or maps" prohibits most of what an RP server *is*. **[PRACTICE]** It is plainly not enforced literally — thousands of licensed servers run custom stories and jobs. But an unenforced-but-live clause is **discretionary leverage**: it means Rockstar can find a policy basis to act against essentially any RP server whenever it decides it wants to. **Never assume "we're compliant" is a defence when a clause this broad exists.** Your protection is goodwill, not compliance.

**Also:** #2 is why post-acquisition RP servers banned **real-world car brands and map imports from other games**. If you import branded vehicles or foreign maps, you are already in breach — and that is a far more likely trigger than anything your news bot does.

### 4.3 The Creator Platform License Agreement (last updated **12 Jan 2026**)

Master text: `https://fivem.net/terms` → redirects to `https://static.cfx.re/platform-license-agreement-12-jan-2026.pdf`. The Cfx.re forum announcement said only that the update would *"simplify and align the Platform License Agreement with updates made to the Rockstar Games Terms of Service earlier this year"* — no substantive detail. **⚠️ [THIN on primary text] I could not extract the PDF (no local PDF tooling; the fetch returned raw binary). Clause quotes below come from secondary sources that cite section numbers (GameServerKings, FiveM Coach). Treat section numbering as indicative and verify against the PDF.**

**Tebex exclusivity — [CONTRACT], and directly relevant to you:**
> *"The use of any other platform or payment provider is prohibited and is a violation of the Platform License Agreement."*

**⚠️ PayPal, Patreon, Ko-fi, direct card processing, crypto checkout, and Patreon perks delivering in-game items are ALL violations.** You mentioned "donations/Tebex" — **Tebex is correct and is the only correct answer.** If any legacy PayPal or Patreon link exists anywhere, remove it.

**⚠️ "Donations" is NOT a safe harbour — this is the trap most communities fall into.** Tebex clause **1.8** requires that packages **"should not be described as donations"** and mandates **defined benefits for every product**. Calling a sale a "donation" while delivering perks is a compliance breach, and **[PRACTICE]** vague package descriptions are a leading cause of chargebacks and frozen payouts. **If you currently label Tebex packages "donation", rename them and list exact deliverables.** This is probably your most likely near-term compliance failure — far more likely than anything involving leaks.

**Prohibited monetisation (cited as PLA §3.1):**
1. **Cash-out / gambling** — *"Players may never pay real money in and take real money or its equivalent out"*; real-money casinos (slots, blackjack, poker) named explicitly.
2. **Chance-based mechanics** — *"offering or selling for Real Money or in-game virtual currency any 'loot boxes,' 'gacha' elements"*. **⚠️ Applies even when bought with in-game currency. Renaming ("crates", "cases", "mystery boxes") changes nothing.**
3. **In-game currency sales** — *"offering or selling in-game virtual currency for Real Money"*. **⚠️ Unqualified — covers currency *your server* created. Common on live servers and still prohibited.**
4. **Rockstar-created content** — cannot sell Rockstar's built-in vehicles, weapons, or Virtual Items.
5. **Brand operations** — no running the server for/on behalf of a third-party brand or in ongoing commercial association.
6. **Reselling other creators' content** — no aggregator storefronts.
7. **In-game advertising** — no sponsored placements or paid brand integrations.
8. **Crypto / NFTs** — including tokens and **meme coins**.

**Tebex AUP adds:** nothing convertible to real-world currency; no cash-prize or play-to-earn; and on real-world IP, **"minor changes to copyrighted content do not make it compliant"** — badge-removed lookalike vehicles are still prohibited. No items that "impact core gameplay."

**Permitted:**
- **Cosmetics** you created — clothing, liveries, decor, vehicle skins
- **Custom vehicles/assets you hold rights to** (as in-server perks; standalone resale prohibited)
- **Convenience** — extra garage/character slots; **queue priority is explicitly permitted** (position only, not gameplay power)
- **Recognition** — supporter tags, credits, Discord roles
- **Memberships** — monthly bundles of perks/status/recognition

Common thread: **everything compliant is tied to your own community and to content you hold rights to grant.**

**Required housekeeping — easy to miss, cheap to fix:**
- **Operator identification and contact email** (PLA §2.3)
- **Disclaimer** substantially similar to: **"YOUR SERVER IS NOT APPROVED, SPONSORED, OR ENDORSED BY ROCKSTAR GAMES"** (PLA §2.3)
- Specific benefit descriptions per package (Tebex AUP)
- No distribution of licensed musical works (PLA §2.4) — **⚠️ this kills licensed-music radio stations, a very common RP feature**

**Enforcement mechanics [CONTRACT/PRACTICE]:**
- **Tebex:** on verified breach, **disables the webstore and restricts access to funds** — i.e. your money is frozen.
- **Rockstar/PLA:** *"Adverse Action against the account, the content, or the Custom Server itself, with no obligation to refund anything"* — extending to **the licence key your server boots with**.
- **[PRACTICE]** Typical failure sequence: **frozen payouts → chargebacks from vague package descriptions → key revocation.** Not a single dramatic ban. You will likely see money problems before you see platform problems.

### 4.4 Does a news Discord alongside a monetised RP server add exposure?

**[LAW] Legally: essentially no.** They are separate activities. Discussing news does not breach the PLA, which governs your *server*, not your *speech*. There is no clause tying community media commentary to licence compliance. I looked for one; I did not find one. (Caveat: **[THIN]** I could not read the PLA primary text, so I cannot categorically exclude a relevant clause in the 12 Jan 2026 version.)

**[PRACTICE] Practically: yes, and this is the risk that is genuinely underrated.** Three mechanisms:

1. **Reputational linkage.** Same brand, same staff, same Discord, cross-promotion. If your community becomes known as a GTA 6 leak venue, that reputation attaches to the **licensed, monetised** entity. Rockstar has **broad discretionary power** (§4.2 #4, §4.3 adverse action) and needs no legal theory to use it.
2. **"Commercial" characterisation.** Monetisation weakens your informatory-purpose/fair-practice footing under the quotation and news-reporting exceptions (§2.2), and weakens the Trade Secrets Directive Art. 5 media-freedom defence (§2.3). **The Tebex store is a fact a lawyer would put in a letter.**
3. **⚠️ Asymmetry — the whole point.** The `#news` channel generates **no revenue**. The RP server generates **all** of it. You are risking a revenue-generating licence to run a zero-revenue hype channel. Even at low probability, that trade is bad unless the news channel is genuinely valuable to you — and if it is, insulate it.

**Concrete mitigations, in order of value:**
- **Keep leaks out of the RP server's *game* and *assets* entirely.** No GTA 6 map recreations, no leaked-asset ports, no "Leonida" builds derived from leaks. **This is by far the biggest RP-side risk** — Dark Space is the precedent (§3), and it is *exactly* the temptation a GTA-6-hyped RP community faces. A leaked-map FiveM build is the single fastest way to lose your licence.
- Never imply Rockstar affiliation or endorsement; carry the PLA §2.3 disclaimer prominently.
- Never use leak material in **marketing** for the server or store. Monetised promotional use of leaked material is the worst-case combination.
- Consider separating brands, or at minimum keeping `#news` visually and textually distinct, with its own disclaimer.
- **[PRACTICE]** If forced to choose between the news channel and the RP licence, the licence is worth more. Decide that now, in the calm, rather than during an incident.

---

## 5. DISCORD'S OWN RULES AND ENFORCEMENT BEHAVIOUR

**[CONTRACT]** Sources: Discord ToS, Copyright & IP Policy, Unauthorized Copyright Access Policy Explainer (Community Guideline #24).

**What's prohibited.** Discord *"forbids any activity that gives anyone unauthorized access to copyrighted material, including through live-streams, and prohibits coordinating such access."* Also: tools that bypass copyright protections; services facilitating illegal sale/purchase/trade of copyrighted content; game exploits that bypass anti-cheat or illegally modify game code.

**⚠️ Note the two words "coordinating such access."** This is broader than hosting. **A channel where members point each other to mirrors — even without files being uploaded — is plausibly "coordinating unauthorized access."** This is the Discord-specific reason your no-links rule must extend to **members**, not just the bot. Your bot's discipline is irrelevant if `#general` is a link exchange.

**On description:** Discord's policies target *access to* copyrighted material. **[LAW/CONTRACT]** Describing a leak does not give access to anything, so a text-only description is outside the prohibition on its face. Discord's policy is not the risk here — member-posted links and media are.

**Enforcement mechanics [CONTRACT/PRACTICE]:**
- Valid DMCA report → **content removed** and a **warning** to the user. Actioned typically within days.
- Content is removed **immediately** on receipt; counter-notice window ~10–14 days.
- Reported as a **three-strike** copyright policy; **[THIN]** — this figure comes from third-party DMCA-service blogs (fanlock, Enforcity, Altahonos), **not** from Discord's own text. Treat "three strikes" as unconfirmed folklore; the reliable statement is that enforcement **escalates**.
- **Repeat infringement → server suspension, permanent bans, account termination.** Discord's stated policy is *"to terminate account holders who they determine to be repeat copyright infringers"*, per DMCA §512(i). **[LAW+CONTRACT]** This is not discretionary generosity — maintaining safe harbour *requires* Discord to have and use a repeat-infringer policy. **⚠️ Which means Discord is structurally incentivised to terminate rather than defend you.**
- ToS reserves the right to suspend or terminate **"with or without notice"** for breach, **including encouraging others to breach**.

**Does a DMCA notice nuke the server or just the message?** **[PRACTICE]** Normally **just the message**, plus a warning. Server-level deletion is an **escalation** outcome — repeat infringement, or a server whose evident purpose is infringement. Scale: Discord removed **41,000+ servers in H1 2024** across all policy violations; in Q2 2022 it received **840 facially valid DMCA notifications**, all sufficient for removal on review. **⚠️ [THIN]** I could **not** obtain an IP-specific server-deletion breakdown — the Transparency Hub landing page carries no figures and I could not retrieve the report PDFs. So I cannot tell you how often DMCA alone kills a server. Assume single notices remove messages and patterns kill servers.

**Have GTA-6-leak Discords been terminated?** **⚠️ [UNVERIFIED — and I want to be precise, because it's easy to overstate].** The three named servers (Ødyssey.gg, "! Odyssey", DarkViperAU) were **subpoenaed, not confirmed banned**. I found **no** report of Discord deleting them. Discord said on Aug 24 it had **not yet been served**. What *is* confirmed is platform action **elsewhere**: Telegram channel pulled for copyright; Reddit removals by Legal Operations; r/GTA6Unmoderated warned and locked.

**The repeat-infringer risk to your community, stated plainly [PRACTICE]:** the realistic path to losing your Discord is **not** your bot. It is **members** posting clips, mirrors, or map images in `#general`, accumulating strikes until Discord escalates to server level. **Your no-media rule is worth very little unless it is enforced against members, with automated help.** This is a moderation-engineering problem.

---

## 6. THE NEWS BOT — COPYRIGHT HYGIENE

### 6.1 Are headlines copyrightable?

**[LAW] Sometimes — the threshold is low but non-zero.** *Infopaq* (C-5/08) held that reproducing an **11-word extract** can be a partial reproduction **if** the extract expresses the author's own intellectual creation. So: no bright-line safe length. Short factual headlines ("GTA 6 delayed to November") are very unlikely to qualify; creative or punning headlines might.

**[PRACTICE]** Posting a headline verbatim **with attribution and a link** is universal internet practice, is what every aggregator and every Discord news bot does, and I found **no** instance of enforcement against it. **Risk: very low.** Safer still: **rewrite the headline in your own words** (or in Hungarian — a genuine translation-plus-paraphrase reduces the reproduction question substantially).

### 6.2 The EU press publishers' right (DSM Art. 15) — probably not your problem

**[LAW]** Directive 2019/790 Art. 15 grants press publishers rights over online use of their publications **by information society service providers**. Three carve-outs matter enormously to you:

> *"The rights provided for in the first subparagraph shall not apply to private or non-commercial uses of press publications by individual users."*
> *"The protection granted under the first subparagraph shall not apply to acts of hyperlinking."*
> *"The rights provided for in the first subparagraph shall not apply in respect of the use of individual words or very short extracts."*

Also: protection lasts **2 years** from publication and doesn't apply to publications first published before **6 June 2019**.

**Applied to you:**
- **Hyperlinking is expressly exempt.** Link freely. **[LAW]**
- **"Individual words or very short extracts" are exempt.** A headline plus a one-sentence teaser plausibly qualifies. **[LAW — but "very short" is undefined and contested across member states.]**
- **The right runs against "information society service providers"** — i.e. aggregators/platforms like Google News, not hobby Discord channels. **[LAW]** A Discord bot is at most a marginal fit.
- **The non-commercial/individual-user carve-out probably helps you but is the weakest link**, because of the Tebex store (§6.5).

**Hungary:** transposed Art. 15 and **adopted the definition verbatim**. **⚠️ [THIN]** Communia's comparative reporting notes Hungary offers no explicit protection for related-rights holders over subject matter incorporated in press publications, and no protection for expired-protection material — but I could **not** confirm how Hungary drafted the three carve-outs specifically. Given verbatim adoption of the definition, verbatim carve-outs are likely but unverified.

**[PRACTICE]** Enforcement of Art. 15 has been aimed at **Google, Meta and large aggregators**, via collective licensing and competition-law skirmishes. **Zero** realistic risk to a Discord bot. **Risk: negligible.**

### 6.3 Images — the highest-risk part of your bot

**⚠️ This is where an automated news bot is most likely to create real infringement, and it is easy to get wrong by accident.**

- **Rehosting press images** (downloading and re-uploading to Discord's CDN) = **reproduction**. Clearest infringement in your whole pipeline. **[LAW] Don't.**
- **Hotlinking** (pointing at the publisher's URL) — under *GS Media* (C-160/15) and *Renckhoff* (C-161/17), linking to lawfully-published material is generally **not** a new communication to the public; **[LAW]** but *Renckhoff* was emphatic that **re-uploading a copy is**. So hotlink, never rehost.
- **⚠️ Discord auto-embeds are the trap.** Post a URL and Discord fetches and **caches** the OpenGraph image and description onto its CDN. **[LAW — grey]** Arguably a reproduction, though performed by Discord and initiated by you. **[PRACTICE]** Universal behaviour, never enforced against, essentially zero risk. But be aware it is not as clean as "I only posted a link".
- **Official Rockstar assets** (trailer stills, key art, logos) — technically Take-Two's copyright and trademarks. **[PRACTICE]** Editorial/illustrative use alongside news is ubiquitous and unenforced. **But**: never use them so as to imply **endorsement or affiliation** (trademark, not copyright — and Rockstar RP Policy #1 prohibits "misuse of Rockstar Games trademarks"). Never use them in **store/marketing** contexts.
- **🔴 AI-generated GTA 6 imagery — do not, under any circumstances.** **GTASixJoker** got a C&D and issued a public apology (24 Apr 2026) precisely for AI images built on Rockstar's logos, Trailer 1 character designs, Vice City aesthetic, and title treatment, which "risked confusing fans with real leaks." **[PRACTICE]** Take-Two treats AI derivatives as infringement regardless of tool. If your bot generates or sources illustrative imagery, **hard-block anything GTA-6-like.**
- **🔴 Leaked imagery — never, in any form**, including crops, thumbnails, redraws, and "recreations". Rockstar takedowns in this wave **explicitly included accounts publishing map images**.

### 6.4 How much of an article may an automated summary reproduce? Does an LLM summary create derivative-work exposure?

**[LAW]** A summary that conveys **facts** rather than **expression** is not infringement — this is §2.1 again, and it is the strongest thing in your favour. Copyright protects expression; the facts in a news article are free (Szjt. Art. 1(5) is nearly on point). Abstracting is not copying.

**⚠️ Where a summary *does* create exposure:**
- **Near-verbatim or lightly-paraphrased reproduction of substantial portions** — that's copying, whatever you call it. **[LAW]**
- **Reproducing the article's structure and distinctive turns of phrase** — closer to derivative work. **[LAW — grey]**
- **Long verbatim quotes** without quotation-right compliance (source + author, justified extent). **[LAW]**
- **Comprehensive substitution** — if your digest is good enough that nobody clicks through, you're prejudicing normal exploitation (Szjt. Art. 33(2)), which is the factor courts and rightsholders care about most. **[LAW]**

**Does *LLM generation* itself add derivative-work exposure? [LAW — genuinely unsettled, and I won't pretend otherwise.]** The output's status turns on **what the output contains**, not on the fact that a model produced it. An LLM summary containing only facts is no more infringing than a human one. An LLM that **regurgitates** source sentences verbatim is exactly as infringing as copy-paste. Separately, whether *training* infringes is heavily litigated and irrelevant to you as a downstream user of a hosted model. **[PRACTICE]** Zero enforcement against small-scale LLM news summarisation that I could find.

**⚠️ The practical LLM-specific risk is regurgitation, and it is a real engineering concern:** models given a full article and asked to "summarise" will sometimes lift sentences intact. **Mitigations to build in:**
- Cap summaries hard — **2–3 sentences, ~40–60 words**.
- Instruct explicitly: *"Write in your own words. Do not reproduce any sentence from the source. Do not exceed N words."*
- **Add a programmatic n-gram overlap check** (e.g. reject/regenerate if any 8+ word sequence matches the source). This is cheap and it is the single most effective control.
- **Always attribute and always link** — outlet name + headline + URL. Attribution both satisfies the quotation-right source requirement and drives the click-through that keeps you out of "substitution" territory.
- Summarise **facts**, not phrasing.
- **[PRACTICE]** Prefer summarising **multiple** sources into one item — genuine synthesis is both safer and more useful.

### 6.5 Does a bot posting in a server that takes donations count as "commercial use"?

**⚠️ [LAW — grey, and I'd plan for the unhelpful answer.]** There is no clean rule, and "non-commercial" is defined differently across the provisions:

- **Szjt. Art. 34(2)** conditions certain free uses on the borrowing work **not being used commercially**. **[LAW]**
- **DSM Art. 15** exempts "private or **non-commercial** uses by individual users". **[LAW]**
- **Quotation/news-reporting** exceptions turn on **fair practice** and **informatory purpose**, where commerciality is a weighting factor rather than a switch. **[LAW]**
- **US fair use** factor 1 includes commercial character — not dispositive but relevant. **[LAW]**

**Honest assessment:** the news channel itself generates no revenue, and the bot is not selling anything. But you are a community that **takes money through a Tebex store** and whose Discord **promotes** that server. A rightsholder's lawyer would characterise the whole operation as commercial, and **[PRACTICE]** would probably be believed on the "not purely non-commercial" point.

**So: do not build your plan on qualifying as non-commercial.** Fortunately you don't have to — **the facts/ideas exclusion (Szjt. 1(5)–(6)) has no commerciality condition at all.** It applies whether you're a charity or a corporation. This is another reason the describe-don't-link architecture is the right one: **it doesn't depend on your commercial status, so the Tebex store can't undermine it.**

**Mitigations:** keep `#news` free of store links and purchase CTAs; don't put Tebex promotions in the same channel; don't use news/leak content as a store hook.

---

## 7. BLUNT DO / DON'T

### 7.1 THE NEWS CHANNEL (`#news`) AND THE BOT

**DO**
1. ✅ **DO cite the journalism, not the leak.** "According to Eurogamer…" — never "according to the leaked footage". *Highest-value rule in this document.*
2. ✅ **DO link to reputable outlets** (Eurogamer, IGN, Kotaku, PC Gamer, Bloomberg, VGC, RockstarINTEL). Hyperlinking is expressly exempt from DSM Art. 15 and is not reproduction.
3. ✅ **DO hedge everything leak-derived as unverified rumour** — "reportedly", "állítólag", "unverified".
4. ✅ **DO keep bot summaries to 2–3 sentences / ~40–60 words**, in the bot's own words, with outlet + headline + URL.
5. ✅ **DO add an automated n-gram overlap check** (reject any 8+ word verbatim match with the source) before posting an LLM summary.
6. ✅ **DO pin a disclaimer**: unofficial, fan-run, unaffiliated with and not endorsed by Rockstar Games / Take-Two; leak items unverified.
7. ✅ **DO hotlink images rather than rehosting them**, and prefer **official** Rockstar assets for illustration.
8. ✅ **DO moderate members harder than you moderate the bot** — automod blocking known leak domains/mirrors/Telegram invites, plus a pinned rule and fast deletion. **This is where your actual platform risk lives.**
9. ✅ **DO keep leak content a clear minority of the channel.** Character matters more than policy.
10. ✅ **DO log takedowns/warnings** and comply immediately, without argument.
11. ✅ **DO write the digest in Hungarian** where practical — genuine translation + paraphrase is further from reproduction than copy-paste.
12. ✅ **DO consider skipping this leak wave until after the 27 Aug showcase.** Cheapest risk reduction available, and the official Extended Look gives you better content anyway.

**DON'T**
1. 🔴 **DON'T post, embed, reupload, mirror, crop, thumbnail or redraw leaked video, screenshots, or the leaked map. Ever. In any channel.** This is the bright line and everything else is commentary.
2. 🔴 **DON'T link to leaks, mirrors, Telegram channels, or "where to find it"** — and don't let members do it either. Discord prohibits *"coordinating"* unauthorized access, which reaches beyond hosting.
3. 🔴 **DON'T post AI-generated GTA 6 imagery or "recreations".** GTASixJoker got a C&D and had to apologise publicly for exactly this.
4. 🔴 **DON'T transcribe dialogue, or do shot-by-shot/frame-by-frame breakdowns.** Facts and mechanics are free; expression is not.
5. 🔴 **DON'T let the bot reproduce whole articles, long verbatim quotes, or near-verbatim paraphrases.**
6. 🔴 **DON'T let your Discord become a known leak venue.** Reputation is the trigger for discretionary action.
7. 🔴 **DON'T file a DMCA counter-notice** against Take-Two without a lawyer — it means consenting to US federal jurisdiction.
8. 🔴 **DON'T put store links, Tebex promos or purchase CTAs in `#news`.**
9. 🔴 **DON'T assume you'll get a warning first.** Dark Space got a strike, not an email; DarkViperAU got named in a subpoena with no contact.
10. 🔴 **DON'T promise your members privacy you can't deliver.** Take-Two demanded IPs, emails, phone numbers, linked Google/Xbox accounts and device IDs for **everyone who communicated** in three servers since 1 June. You cannot protect them from that. Consider telling them so.

### 7.2 THE RP SERVER (FiveM now, GTA 6 later)

**DO**
1. ✅ **DO monetise exclusively through Tebex.** It is the only permitted provider. Remove every PayPal / Patreon / Ko-fi / direct-card / crypto path.
2. ✅ **DO rename any "donation" packages** and list **exact, specific deliverables** for each (Tebex clause 1.8 — packages "should not be described as donations"). *Most likely near-term compliance failure; cheapest to fix.*
3. ✅ **DO sell only:** your own cosmetics; custom vehicles/assets you hold rights to; **queue priority** (position only); extra garage/character slots; supporter tags/roles/recognition; monthly memberships bundling those.
4. ✅ **DO display the PLA §2.3 disclaimer** — substantially: **"YOUR SERVER IS NOT APPROVED, SPONSORED, OR ENDORSED BY ROCKSTAR GAMES"** — plus operator identification and a contact email.
5. ✅ **DO read the primary documents yourself** and re-check them: `https://static.cfx.re/platform-license-agreement-12-jan-2026.pdf` and the Rockstar RP Servers support article. I could not fully extract either (see §8).
6. ✅ **DO treat the Cfx.re licence key as your most valuable asset.** It is revocable, at discretion, with **"no obligation to refund anything."**
7. ✅ **DO expect the GTA 6 RP situation to be governed by rules that do not exist yet.** FiveM-equivalent support for GTA 6 has not been announced. Don't build a business plan on assumed permission.

**DON'T**
1. 🔴 **DON'T build, import, or host anything derived from GTA 6 leaks — no leaked map recreations, no "Leonida" builds, no leaked-asset ports.** **This is the single fastest way to lose your licence.** Dark Space's GTA 5 map mod, built from leaked coordinate data, was DMCA'd with no warning — and that was a *free* mod with no monetisation. Yours is monetised.
2. 🔴 **DON'T sell in-game virtual currency for real money** — prohibited unqualified, including currency you created, however common it is on other servers.
3. 🔴 **DON'T sell loot boxes / crates / cases / gacha / mystery boxes** — prohibited **even when purchased with in-game currency**; renaming changes nothing.
4. 🔴 **DON'T run real-money gambling or any cash-out mechanic.** "Players may never pay real money in and take real money or its equivalent out."
5. 🔴 **DON'T sell Rockstar-created content** — built-in vehicles, weapons, or Virtual Items.
6. 🔴 **DON'T take corporate sponsorships, run in-game ads, or operate for/with a third-party brand.**
7. 🔴 **DON'T touch crypto, tokens, NFTs or meme coins** in any form. (Note the leaker's own "$CYBERLEEK on Solana" watermark — you do not want to be adjacent to that.)
8. 🔴 **DON'T import real-world branded vehicles, other games' maps, other Rockstar IP, real-world characters/trademarks, or licensed music.** "Minor changes to copyrighted content do not make it compliant" — badge-removed lookalikes are still prohibited. Licensed-music radio stations are out (PLA §2.4).
9. 🔴 **DON'T resell other creators' scripts/assets** or run an aggregator storefront.
10. 🔴 **DON'T use leaks or leaked imagery in server or store marketing.** Monetised promotional use of leaked material is the worst combination available.
11. 🔴 **DON'T imply Rockstar affiliation, approval, or endorsement anywhere.**
12. 🔴 **DON'T rely on "everyone else does it."** Selective, discretionary enforcement is the documented pattern — widespread non-compliance is not a defence, it's just a queue.

---

## 8. WHERE THE EVIDENCE IS THIN — read this before relying on anything above

I want to be explicit about limits rather than imply uniform confidence.

**Could not retrieve (primary sources — genuinely important gaps):**
1. **🔴 The Cfx.re Creator Platform License Agreement PDF itself.** Fetch returned raw binary; no local PDF tooling (`pdftoppm` unavailable). **All PLA clause quotes and section numbers (§2.3, §2.4, §3.1) are from secondary sources that cite them** (GameServerKings, FiveM Coach). They agree with each other, which is reassuring but not verification. **Read the PDF yourself before acting on §4.3.**
2. **🔴 Rockstar's RP Servers support page** — timed out twice. Policy text quoted from DailyCoin, GameDeveloper, NME, TechRadar, which quote it consistently. **Verify against the live page.**
3. **Eurogamer's 22 Aug article** — headline confirmed only via the drimble.nl aggregator; could not fetch Eurogamer directly.
4. **Bloomberg / Schreier 21 Aug newsletter** — paywalled; content confirmed via secondary reporting and direct quotes on X/Bluesky.
5. **Discord Transparency Report IP-specific figures** — landing page carries no numbers; could not retrieve the PDFs. I have **no** figure for servers deleted specifically for copyright.
6. **EUR-Lex** returned empty for both directives; DSM Art. 15 text obtained from legislation.gov.uk's retained-EU-law copy. Text should be identical, but it is not the EU original.
7. **Kotaku, PC Gamer, Tom's Hardware, Insider Gaming (some), Bird & Bird** — 403 / paywall / truncation. Details cross-checked via search summaries and other outlets.

**Claims I could not verify and would not rely on:**
1. **🔴 Notebookcheck's claim that "Rockstar filed legal action against social media posts making text comments about leaks, not just those sharing footage."** **Single-source, uncorroborated after targeted searching.** Most likely a mischaracterisation of the X/YouTube subpoenas, which targeted Cyberleek's own footage-posting accounts. **If it were accurate it would materially weaken the describe-don't-link plan** — which is exactly why I'm flagging rather than burying it. **Monitor this.**
2. **Whether any Discord server has actually been terminated over this leak wave.** The three named servers were **subpoenaed**, not confirmed banned. Discord said on 24 Aug it hadn't been served.
3. **Discord's "three-strike" copyright policy** — from third-party DMCA-service blogs, not Discord's own text. The reliable statement is that enforcement escalates and repeat infringers are terminated.
4. **Hungary's exact drafting of the DSM Art. 15 carve-outs** (hyperlinking / very short extracts / non-commercial individual users). Hungary adopted the definition verbatim; the carve-outs are likely verbatim too, but unconfirmed.
5. **Kurtaj's retrial** (reported scheduled November 2026) — check current status before citing.
6. **CJEU detail on *Funke Medien* / *Spiegel Online* / *Pelham*** — I could not fetch the Bird & Bird analysis (HTTP 402); §2.2 rests on well-established general knowledge of those judgments, not a source retrieved this session. Verify specifics.
7. **Whether the PLA contains any clause tying community media commentary to licence compliance.** I found none and expect none — but see gap #1; I could not read the primary text.

**Fast-moving:** this wave is active as of 24–25 Aug 2026, with the Netflix showcase on 27 Aug, the subpoena deadline on 4 Sep, and release on 19 Nov. **Everything in §1 may be stale within days.** Re-check before making decisions.

**The one thing I'd flag as most likely to change my analysis:** if Take-Two starts actioning **text-only discussion** (claim #1 above), the describe-don't-link line stops being sufficient and the only safe posture becomes not covering leaks at all.

---

## 9. SOURCES — every URL consulted

### Live crackdown (Aug 2026)
- https://torrentfreak.com/take-two-expands-gta-6-leak-hunt-with-dmca-subpoenas/ *(best single source on the subpoenas)*
- https://www.tomshardware.com/video-games/console-gaming/take-two-subpoenas-microsoft-for-windows-device-ids-of-everyone-in-three-discord-servers-in-gta-6-leak-hunt *(truncated)*
- https://www.pcgamer.com/games/grand-theft-auto/take-two-kicks-off-gta-6-leaker-hunt-with-subpoenas-demanding-records-from-microsoft-and-discord/ *(truncated)*
- https://kotaku.com/take-two-subpoenas-microsoft-and-discord-records-related-to-spread-of-gta-6-leaks-2000726633 *(403)*
- https://kotaku.com/discord-says-it-hasnt-been-served-with-a-subpoena-over-gta-6-leaks-yet-well-evaluate-the-validity-and-scope-before-responding-2000727642 *(403)*
- https://variety.com/2026/gaming/news/gta-6-leaks-rockstar-subpoenas-microsoft-discord-1236840176/ *(redirect)*
- https://au.variety.com/2026/more/news/gta-6-leaks-rockstar-subpoenas-microsoft-discord-39599/
- https://insider-gaming.com/take-twos-gta-6-leaker-subpoenas-namedrop-popular-content-creator/ ✅ *(DarkViperAU)*
- https://x.com/DarkViperAU/status/2090807149186470231 ✅ *(his statement)*
- https://x.com/Kotaku/status/2090798850906669354
- https://tech.yahoo.com/gaming/articles/gta-6-leak-two-subpoenas-174000738.html ✅ *(GitHub subpoena)*
- https://gamerant.com/gta-6-gameplay-leaks-take-two-legal-response-statement/ ✅ *(T2 declaration)*
- https://www.notebookcheck.net/GTA-6-hacker-CyberLeek-goes-offline-as-Take-Two-and-Microsoft-mount-legal-crackdown.1375698.0.html ⚠️ *(unverified text-comments claim)*
- https://www.notebookcheck.net/GTA-6-gameplay-and-map-leaks-see-DMCA-strikes-as-confidence-grows-in-their-legitimacy.1372162.0.html
- https://www.dualshockers.com/gta-6-leaks-pages-hit-amid-rockstar-crackdown/
- https://www.gamespot.com/articles/apparent-gta-6-footage-and-map-leak-as-rockstar-issues-takedowns/
- https://insider-gaming.com/gta-6-gameplay-dmca/
- https://gameranx.com/updates/id/563784/article/cyberleek-down-take-two-ironically-uses-legal-means-to-dmca-gta-6-leaks-and-find-the-leakers/
- https://gamedaily.com/games/more-gta-6-leaks-take-two-legal-fight
- https://gamedaily.com/games/take-two-subpoenas-microsoft-discord-gta-6
- https://drimble.nl/entertainment/games/107777604/is-this-the-end-of-the-gta-6-leaks-take-twos-legal-crusade-appears-to-shut-down-the-hubs-behind-them.html ✅ *(Eurogamer headline)*
- https://www.bloomberg.com/news/newsletters/2026-08-21/rockstar-rattled-as-grand-theft-auto-vi-leaks-again *(paywalled)*
- https://x.com/iGrandTheftAuto/status/2090881732874572160
- https://www.forbes.com/sites/paultassi/2026/08/21/the-gta-6-leaker-is-leaking-again-ending-rumors-of-being-caught/
- https://www.gtaboom.com/take-two-is-now-chasing-the-gta-6-leaker-across-x-and-google-b287
- https://videocardz.com/newz/take-two-goes-after-cyberleek-after-gta-6-leak-spree-subpoenas-microsoft-and-discord
- https://www.ibtimes.co.uk/take-two-interactive-gta-6-leak-controversy-1815898
- https://www.gamesradar.com/games/grand-theft-auto/latest-gta-6-leaks-see-cyberleek-threaten-rockstar-with-lucia-story-spoilers-and-closely-examine-naked-npcs/
- https://rockstarintel.com/breaking-8th-gta-6-gameplay-leak-shows-strip-club-and-cutscene/
- https://www.manilatimes.net/2026/08/25/world/rockstar-games-subpoenas-microsoft-discord-over-gta-6-leaks/2411308
- https://hi-tech.ua/en/the-hunt-for-cyberleek-take-two-takes-legal-action-against-gta-6-leaks/
- https://ixbt.games/en/news/2026/08/24/430086-...
- https://x.com/GTA6_HQ/status/2090587114551366028 ✅ *(r/GTA6Unmoderated warned/locked)*
- https://thegamepost.com/new-gta-6-leaks-taken-down-by-rockstar-adding-more-weight-to-the-new-footage/
- https://gamedev.net/news/5208-rockstar-hit-with-more-leaks-as-gta-6-gameplay-and-assets-appear-to-circulate/
- https://www.aroged.com/2026/08/23/grand-theft-auto-vi-first-crackdown-on-leaker-after-further-leaks-of-game-content/
- https://thepcenthusiast.com/grand-theft-auto-6-leaks-response/
- https://www.choseno.com/news/rockstar-games-enforces-global-copyright-takedowns-gta-6-leaks-2026-08-18
- https://windowsreport.com/take-two-hits-gta-6-leaked-gameplay-with-dmca-takedown-notice/
- https://thecybersecguru.com/news/cyberleek-gta-6-leak-gameplay-map-dmca/

### GTA 6 release / showcase context
- https://variety.com/2026/gaming/news/gta-6-trailer-netflix-youtube-aug-27-1236789693/
- https://www.pushsquare.com/guides/gta-6-netflix-extended-look-when-and-how-to-watch
- https://www.netflix.com/tudum/articles/grand-theft-auto-6-extended-first-look
- https://www.thefpsreview.com/2026/08/08/the-first-gta-6-gameplay-footage-is-a-netflix-exclusive-for-six-hours-on-august-27/
- https://www.notebookcheck.net/BBC-leaks-GTA-6-Netflix-Extended-Look-length-after-Rockstar-confirmed-no-delay.1375714.0.html

### Enforcement history
- https://www.pcgamer.com/gta-modding-tool-openiv-shuts-down-claiming-cease-and-desist-from-take-two/
- https://openiv.com/?p=1324
- https://feeds.bbci.co.uk/news/technology-40301450
- https://www.neowin.net/news/take-two-interactive-slaps-popular-gta-modding-tool-openiv-with-cease-and-desist-order/
- https://gta.fandom.com/wiki/OpenIV
- https://www.gtaboom.com/take-two-just-killed-the-vice-city-browser-port-3955
- https://www.techdirt.com/2025/04/02/take-two-dmcas-video-of-gta5-mod-to-for-gta6-map-content/ ✅ *(Dark Space)*
- https://kotaku.com/gta-6-map-mod-youtube-video-take-two-copyright-fivem-1851771882
- https://www.videogamer.com/news/gta-6-map-mod-for-gta-5-killed-too-accurate/
- https://www.kitguru.net/tech-news/matthew-wilson/take-two-takes-down-gta-v-mod-that-recreated-the-gta-6-map/
- https://insider-gaming.com/gta-5-mod-adds-gta-6-removed/
- https://www.gosugamers.net/entertainment/news/74570-gta-5-mod-based-on-gta-6-leaks-taken-down-over-copyright-strike
- https://www.gtaboom.com/the-gta-6-ai-fake-problem-just-got-its-latest-legal-takedown-779e ✅ *(GTASixJoker AI C&D)*
- https://variety.com/2022/digital/news/grand-theft-auto-6-leak-rockstar-games-hack-1235376727
- https://www.bleepingcomputer.com/news/security/lapsus-hacker-behind-gta-6-leak-gets-indefinite-hospital-sentence/
- https://www.cbsnews.com/news/grand-theft-auto-leak-teen-hacker-hospitalized/
- https://www.siliconrepublic.com/enterprise/gta-6-hacker-life-hospital-prison-lapsu-arion-kurtaj
- https://www.techradar.com/gaming/gta-6-hacker-who-intended-to-return-to-cyber-crime-as-soon-as-possible-sentenced-to-an-indefinite-hospital-order
- https://www.pcgamer.com/games/grand-theft-auto/grand-theft-auto-6-leaker-who-was-given-an-indefinite-sentence-in-2023-because-he-wouldnt-stop-hacking-is-now-out-of-hospital-and-awaiting-retrial/ ✅ *(Jul 2026 status)*

### FiveM / Cfx.re / Rockstar RP
- https://static.cfx.re/platform-license-agreement-12-jan-2026.pdf 🔴 *(primary — could not extract)*
- https://fivem.net/terms *(redirects to above)*
- https://forum.cfx.re/t/updates-to-the-creator-platform-license-agreement/5371920
- https://support.rockstargames.com/articles/5I66kExWgligszgMCU3XC1/roleplay-rp-servers 🔴 *(primary — timed out)*
- https://www.gameserverkings.com/knowledge-base/fivem/server-monetisation/ ✅ *(§3.1 quotes)*
- https://fivemcoach.com/en/blog/fivem-monetization-rules ✅ *(most detailed)*
- https://fivemcoach.com/learn/fivem-tebex-monetization
- https://docs.fivem.net/docs/server-manual/setting-up-a-tebex-store/
- https://goodleafdev.com/blog/fivem-creator-license-agreement-update
- https://dailycoin.com/rockstar-games-updates-policy-on-rp-servers/ ✅ *(RP policy text)*
- https://www.gamedeveloper.com/business/rockstar-allows-roleplaying-in-i-gta-online-i-but-no-loot-boxes-or-nfts
- https://www.nme.com/news/gaming-news/rockstar-bans-nfts-from-gta-online-roleplay-servers-3353811
- https://www.techradar.com/news/rockstar-will-stop-you-from-trading-crypto-and-nfts-in-updated-gta-online-server-guidelines
- https://www.crunchbase.com/acquisition/rockstar-games-acquires-cfx-re--f66688c9 ✅ *(11 Aug 2023)*
- https://www.gamedeveloper.com/business/rockstar-acquires-community-roleplay-team-cfx-re
- https://www.videogameschronicle.com/news/rockstar-acquires-gta-5-roleplay-devs-cfx-re/
- https://www.pcgamer.com/rockstar-buys-the-makers-of-the-gta-online-fivem-mod-it-banned-8-years-ago/ ✅ *(2015 bans, PIs)*
- https://wccftech.com/previously-banned-gta-5-fivem-and-rdr2-redm-creators-are-now-part-of-rockstar-games/
- https://sportskeeda.com/gta/news-gta-5-rp-fivem-servers-ban-real-world-cars-map-imports-following-acquisition-rockstar *(405)*
- https://rockstarintel.com/rockstar-games-plans-to-monetize-fivem-and-protect-its-property-it-has-been-suggested/

### Discord
- https://discord.com/safety/copyright-trademark-policy-explainer ✅
- https://support.discord.com/hc/en-us/articles/4410339349655-Discord-s-Copyright-IP-Policy *(403)*
- https://discord.com/terms
- https://discord.com/safety/360043709612-our-policies
- https://discord.com/safety-transparency *(no figures)*
- https://cdn.prod.website-files.com/625fe439fb70a9d901e138ab/67056a054d453d30491c1ac9_Discord%20Jan_Jun%202024%20Transparency%20Report.pdf
- https://discord.com/blog/discord-transparency-report-q2-2022
- https://fanlock.com/blog/platform-guides/how-to-file-a-dmca-takedown-on-discord ⚠️ *(3-strike claim)*
- https://www.enforcity.com/discord-dmca-takedown ⚠️
- https://www.altahonos.com/discord-dmca-takedown ⚠️
- https://www.dmca.com/FAQ/DMCA-Takedown-Notice-and-Discord
- https://www.statista.com/statistics/1286876/discord-deleted-servers-by-method
- https://www.pellonia.io/post/protecting-your-ip-rights-and-trademarks-in-discord-in-2026

### Law — Hungary / EU / US
- https://www.wipo.int/wipolex/edocs/lexdocs/laws/en/hu/hu084en.html ✅ **primary — Szjt. Arts. 1(5), 1(6), 33(2), 34(1), 36(2), 37**
- https://www.wipo.int/wipolex/en/legislation/details/2213
- https://www.wipo.int/wipolex/en/legislation/details/18289
- https://www.legislation.gov.uk/eudr/2019/790/article/15 ✅ **DSM Art. 15 carve-outs**
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019L0790 *(empty)*
- https://eur-lex.europa.eu/eli/dir/2016/943/oj ✅ *(Trade Secrets, incl. Art. 5)*
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A32016L0943
- https://www.legislation.gov.uk/eudr/2016/943/article/5/data.html
- https://en.wikipedia.org/wiki/Directive_on_the_Protection_of_Trade_Secrets
- https://en.wikipedia.org/wiki/Infopaq_International_A/S_v_Danske_Dagblades_Forening ✅ *(11-word test)*
- https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62008CC0005
- https://www.twobirds.com/en/insights/2019/global/copyright-exceptions-for-reporting-current-events-and-quotations 🔴 *(402)*
- https://www.rpclegal.com/snapshots/intellectual-property/cjeu-rules-on-implementation-and-interpretation-of-copyright-exceptions-in-article-5-3/
- https://link.springer.com/article/10.1007/s40319-024-01467-3
- https://communia-association.org/2024/09/05/comparative-report-on-the-national-implementations-of-articles-15-17-cdsmd-14-new-countries/
- https://legalblogs.wolterskluwer.com/copyright-blog/an-update-on-the-hungarian-implementation-process-of-the-cdsm-directive/
- https://academic.oup.com/jiplp/article/16/8/887/6298309
- https://informationlabs.org/wp-content/uploads/2022/09/Angelopoulos-Report-Full-Report.pdf
- https://www.researchgate.net/publication/386123231_Press_Publishers'_Right_in_Hungary_Brief_Empirical_Report_after_the_Implementation
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3671358
- https://www.echr.coe.int/documents/d/echr/FS_Whistleblowers_ENG
