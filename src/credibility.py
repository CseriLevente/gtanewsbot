"""
Source tiering, relevance filtering and the post/label/hold/drop decision.

The editorial rule this implements, decided by the operator:

    We may describe what a leak CLAIMS, as rumour only. We never link to,
    embed, or reupload leaked material, and every claim is attributed to the
    journalism that reported it — never to the leak itself.

Two consequences are enforced in code rather than left to discipline:

  * a leak-derived claim is capped at RUMOUR permanently, regardless of how
    many outlets pick it up. Corroboration can promote a tier-4 report to
    postable, but it can never promote leak-derived content to fact.
  * blocked domains/handles are dropped before scoring, so a documented
    fabricator cannot earn its way in by volume.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src import paths

logger = logging.getLogger(__name__)

# Decisions
POST_AS_FACT = "post_as_fact"
POST_AS_RUMOUR = "post_as_rumour"
HOLD = "hold"
DROP = "drop"

# Labels shown to readers.
LABEL_OFFICIAL = "Official"
LABEL_REPORT = "Report"
LABEL_RUMOUR = "Rumour"

# GTA-relevance keywords. The firehose feeds (PC Gamer, VGC, Eurogamer,
# GameSpot) carry all games; without this ~95% of their items are noise.
_RELEVANCE_RE = re.compile(
    r"\b(gta\s*6|gta\s*vi|grand\s*theft\s*auto\s*(?:6|vi)|gta\s*6\'?s|"
    r"rockstar\s*games|rockstar\s*north|"
    # "take two" is an ordinary English phrase ("it will take two weeks",
    # "take two players through the campaign"), and the firehose feeds carry
    # 2000-char summaries, so the bare form matched unrelated reviews and put
    # them in a GTA 6 digest. Require a corporate token beside it.
    r"take[\s\-]?two\s+(?:interactive|games|ceo|earnings|shares|stock|"
    r"investor|announces|reports|zelnick)|take2games|take2|"
    r"vice\s*city|leonida|cfx\.re|fivem|gta\s*online|gta\s*5|gta\s*v)\b",
    re.IGNORECASE,
)

# Strongly GTA-6-specific: used to prefer these over merely Rockstar-adjacent items.
_CORE_RE = re.compile(
    r"\b(gta\s*6|gta\s*vi|grand\s*theft\s*auto\s*(?:6|vi))\b", re.IGNORECASE
)

_DEFAULT_TIER = 4


@dataclass
class Verdict:
    """The outcome of judging one item."""
    decision: str
    tier: int
    label: str
    is_rumour: bool
    is_leak_derived: bool
    score: int
    reasons: list[str] = field(default_factory=list)

    @property
    def postable(self) -> bool:
        return self.decision in (POST_AS_FACT, POST_AS_RUMOUR)


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load config/sources.json."""
    with open(path or paths.SOURCES_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _lower_set(cfg: dict, key: str) -> set[str]:
    return {str(x).casefold() for x in cfg.get(key, [])}


def is_relevant(title: str, summary: str | None = None) -> bool:
    """Cheap keyword gate for firehose feeds."""
    blob = f"{title} {summary or ''}"
    return bool(_RELEVANCE_RE.search(blob))


def is_core_gta6(title: str, summary: str | None = None) -> bool:
    """True if the item is specifically about GTA 6, not merely Rockstar-adjacent."""
    blob = f"{title} {summary or ''}"
    return bool(_CORE_RE.search(blob))


def tier_for_domain(domain: str, cfg: dict[str, Any]) -> int:
    """
    Tier for a publisher domain, walking up the subdomain chain.

    'eduadmin.fortune.com' must NOT inherit fortune.com's tier — so blocked
    domains are checked as exact/suffix matches by the caller before this runs.
    """
    tiers: dict[str, int] = cfg.get("domain_tiers", {})
    d = (domain or "").casefold()
    if d in tiers:
        return int(tiers[d])
    parts = d.split(".")
    for i in range(1, len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in tiers:
            return int(tiers[candidate])
    return _DEFAULT_TIER


def blocked_reason(domain: str, url: str, title: str, cfg: dict[str, Any]) -> str | None:
    """Return a reason string if this item must be dropped outright."""
    d = (domain or "").casefold()
    blob = f"{url} {title}".casefold()

    for bad in _lower_set(cfg, "blocked_domains"):
        if d == bad or d.endswith("." + bad):
            return f"blocked domain: {bad}"

    for handle in _lower_set(cfg, "blocked_handles"):
        # Match as a token so a short handle cannot hit inside an unrelated word.
        if re.search(rf"(?:^|[^a-z0-9]){re.escape(handle)}(?:[^a-z0-9]|$)", blob):
            return f"blocked account: {handle}"

    for sub in _lower_set(cfg, "blocked_subreddits"):
        if f"/r/{sub}" in blob:
            return f"blocked subreddit: r/{sub}"

    return None


def _matches_any(text: str, needles: set[str]) -> list[str]:
    low = text.casefold()
    return [n for n in needles if n in low]


# Assertion patterns for the perennial GTA 6 fakes. Each requires the CLAIM VERB
# adjacent to the subject, so merely mentioning the topic is not enough.
_CONTRADICTION_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    (
        "a delay beyond the announced 2026-11-19 date",
        re.compile(r"delay(?:ed|s)?\s+(?:to|until|into)\s+20(?:2[7-9]|3\d)", re.I),
    ),
    (
        "a Nintendo Switch 2 version",
        re.compile(
            r"(?:coming|confirmed|announced|headed|coming\s+out|coming\s+soon|"
            r"releas\w+|port(?:ed|ing)?)\s+(?:to|for|on)\s+(?:the\s+)?"
            r"(?:nintendo\s+)?switch\s*2",
            re.I,
        ),
    ),
    (
        "a confirmed PC version",
        re.compile(
            r"pc\s+(?:version|release|port|edition)\s+(?:is\s+|has\s+been\s+)?"
            r"(?:confirmed|announced|dated|official|revealed)",
            re.I,
        ),
    ),
    (
        "a confirmed online mode at launch",
        re.compile(
            r"(?:gta\s*6|gta\s*vi)\s+online\s+(?:is\s+)?(?:confirmed|announced|dated)",
            re.I,
        ),
    ),
)

# If any of these appear, the headline is probably REPORTING ON or DEBUNKING the
# claim rather than making it.
_NEGATION_RE = re.compile(
    r"\b(?:not|isn'?t|aren'?t|won'?t|wasn'?t|never|no|nope|denies|denied|denial|"
    r"debunk\w*|false|fake|hoax|untrue|misleading|rumour|rumor|why|explained|"
    r"still\s+no|myth)\b",
    re.I,
)


def contradicts_baseline(title: str, summary: str | None, cfg: dict[str, Any]) -> str | None:
    """
    Flag an item that ASSERTS something contradicting established fact.

    Deliberately conservative, because the action taken on a hit is DELETION.

    The previous implementation matched "most significant words of a known-false
    claim co-occur anywhere", which made it a topic detector rather than a
    contradiction detector. Measured against real headlines it dropped 8 of 8
    probes including four TRUE stories — "Rockstar confirms GTA 6 is NOT
    delayed", "Why GTA 6 was delayed to November 2026", "No, GTA 6 is still not
    coming to the Switch 2", "GTA 6 PC version still not confirmed". Those are
    precisely the release-date stories the channel most needs, and it deleted
    them for containing the same words as the fake.

    Two rules fix it:
      1. the pattern must match an ASSERTION (claim verb adjacent to subject),
         not a bag of co-occurring words;
      2. any negation or reporting cue anywhere in the text vetoes the drop.
    Rule 2 flips the direction of error: a fake that survives is merely posted
    with a Rumour label, whereas a true story dropped is gone for good.
    """
    blob = f"{title} {summary or ''}"
    for label, pattern in _CONTRADICTION_PATTERNS:
        m = pattern.search(blob)
        if not m:
            continue
        if _NEGATION_RE.search(blob):
            # Reporting on or refuting the claim — keep it.
            return None
        return f"asserts {label}, which contradicts established fact"
    return None


def judge(
    *,
    title: str,
    summary: str | None,
    domain: str,
    url: str,
    feed_tier: int,
    cfg: dict[str, Any],
    tier2_corroborations: int = 0,
) -> Verdict:
    """
    Decide what to do with one item.

    `tier2_corroborations` is the count of INDEPENDENT tier-2 reports of the same
    story already seen. Independence (different parent company, no citation link,
    >20min apart) is the caller's responsibility — five outlets recycling one
    4chan post is one source, not five.
    """
    reasons: list[str] = []
    blob = f"{title} {summary or ''}"

    # 1. Hard blocks, before any scoring.
    blocked = blocked_reason(domain, url, title, cfg)
    if blocked:
        return Verdict(DROP, 5, LABEL_RUMOUR, True, False, 0, [blocked])

    # 2. Relevance.
    if not is_relevant(title, summary):
        return Verdict(DROP, feed_tier, LABEL_REPORT, False, False, 0, ["not GTA-related"])

    # 3. Tier: the worse of (publisher domain, originating feed).
    domain_tier = tier_for_domain(domain, cfg)
    tier = max(domain_tier, feed_tier) if feed_tier else domain_tier
    if domain_tier != feed_tier:
        reasons.append(f"tier {tier} (domain {domain_tier}, feed {feed_tier})")

    # 4. Leak-derived? This is a permanent cap, not a score penalty.
    leak_hits = _matches_any(blob, _lower_set(cfg, "leak_keywords"))
    is_leak_derived = bool(leak_hits)
    if is_leak_derived:
        reasons.append(f"leak-derived ({', '.join(sorted(leak_hits)[:3])})")

    rumour_hits = _matches_any(blob, _lower_set(cfg, "rumour_keywords"))
    is_rumour = is_leak_derived or bool(rumour_hits)
    if rumour_hits and not is_leak_derived:
        reasons.append(f"hedged language ({', '.join(sorted(rumour_hits)[:3])})")

    # 5. Contradiction of established fact — strong fabrication signal.
    contra = contradicts_baseline(title, summary, cfg)
    if contra:
        reasons.append(contra)

    # 6. Score. Starts from tier and is adjusted by signals.
    score = {1: 100, 2: 80, 3: 55, 4: 25, 5: 0}.get(tier, 25)
    clickbait = _matches_any(blob, _lower_set(cfg, "clickbait_patterns"))
    if clickbait:
        score -= 10 * len(clickbait)
        reasons.append(f"clickbait pattern ({clickbait[0]})")
    if title.isupper() and len(title) > 20:
        score -= 15
        reasons.append("ALL CAPS headline")
    if contra:
        score -= 40
    if is_core_gta6(title, summary):
        score += 10
    else:
        reasons.append("Rockstar-adjacent, not core GTA 6")
    score = max(0, min(100, score))

    # 7. Decision.
    corr = cfg.get("corroboration", {})

    if tier == 1:
        # First-party. Note: a tier-1 SOURCE can still report a rumour (e.g. a
        # Newswire post about a leak), so the rumour flag still applies.
        decision = POST_AS_RUMOUR if is_rumour else POST_AS_FACT
        label = LABEL_RUMOUR if is_rumour else LABEL_OFFICIAL
        return Verdict(decision, tier, label, is_rumour, is_leak_derived, score, reasons)

    if contra:
        return Verdict(DROP, tier, LABEL_RUMOUR, True, is_leak_derived, score,
                       reasons + ["dropped: contradicts established fact"])

    if tier == 2:
        if is_leak_derived:
            return Verdict(POST_AS_RUMOUR, tier, LABEL_RUMOUR, True, True, score,
                           reasons + ["leak-derived: capped at rumour permanently"])
        decision = POST_AS_RUMOUR if is_rumour else POST_AS_FACT
        label = LABEL_RUMOUR if is_rumour else LABEL_REPORT
        return Verdict(decision, tier, label, is_rumour, False, score, reasons)

    if tier == 3:
        need = int(corr.get("tier3_required_tier2_confirmations", 1))
        if tier2_corroborations >= need:
            return Verdict(POST_AS_RUMOUR if is_rumour else POST_AS_FACT, tier,
                           LABEL_RUMOUR if is_rumour else LABEL_REPORT,
                           is_rumour, is_leak_derived, score,
                           reasons + [f"corroborated by {tier2_corroborations} tier-2"])
        return Verdict(HOLD, tier, LABEL_RUMOUR, is_rumour, is_leak_derived, score,
                       reasons + [f"tier 3 needs {need} tier-2 confirmation(s), has {tier2_corroborations}"])

    # tier 4+
    need = int(corr.get("tier4_required_tier2_confirmations", 2))
    if tier2_corroborations >= need:
        return Verdict(POST_AS_RUMOUR, tier, LABEL_RUMOUR, True, is_leak_derived, score,
                       reasons + [f"corroborated by {tier2_corroborations} tier-2; "
                                  f"attribute to those outlets, never to the tier-4 origin"])
    return Verdict(HOLD, tier, LABEL_RUMOUR, True, is_leak_derived, score,
                   reasons + [f"tier {tier} needs {need} independent tier-2, has {tier2_corroborations}"])
