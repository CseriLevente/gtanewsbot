"""
LLM curation stage.

WHY THIS EXISTS — and it is not "nicer summaries".

Lexical clustering provably cannot merge some same-story groups. Measured on four
real headlines about one Rockstar statement (2026-08-26), the weighted overlap
between two copies of the SAME story ran as low as 0.080 while an UNRELATED pair
sharing the word "time" scored 0.112. The signal is inverted, so no threshold
separates them, and lowering it to catch the tail starts merging real news. That
story occupied 3-4 of 8 digest slots. Semantic judgement is the only fix.

So this stage does, in order of value:
  1. cluster what lexical similarity cannot,
  2. decide the credibility label with the nuance the keyword cap lacks
     (a Rockstar statement ABOUT leaks is a fact; a claim SOURCED FROM the leak
     is a rumour — the keyword rule cannot tell those apart and labels both
     Rumour),
  3. rank the day's stories,
  4. write a 2-3 sentence summary.

DEGRADATION IS MANDATORY
------------------------
Every failure here returns None and the caller falls back to the heuristic
digest. A missing API key, a network blip, a refusal, a schema violation or a
failed guardrail must never stop the channel from getting its daily post. The
LLM is an enhancement, not a dependency.

HALLUCINATION GUARDRAILS
------------------------
Layered cheapest-and-most-deterministic first, because prompting alone is not
sufficient:

  * THE MODEL NEVER EMITS A URL OR A DATE. It echoes an opaque `item_id`; this
    module looks the URL up from the DB row. A model cannot hallucinate a link
    it was never asked to produce, and "yesterday" is a hallucination generator.
  * `evidence_quote` must be a verbatim span of the provided text, verified by
    string containment. This turns an unverifiable generative claim into a
    deterministic test.
  * every number in the summary must also appear in the source text. For a GTA 6
    channel the highest-stakes hallucination is an invented release date.
  * `insufficient_text` gives refusal a legitimate slot — models fabricate
    hardest when abstaining is not an available action.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

# Imported lazily so the bot runs with no LLM stage installed at all.
try:  # pragma: no cover - environment dependent
    import anthropic
    from pydantic import BaseModel, Field
    LLM_AVAILABLE = True
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]
    LLM_AVAILABLE = False

    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(*_a, **_k):  # type: ignore[no-redef]
        return None


# Default model. The claude-api skill is explicit that cost is the operator's
# decision, not the code's: default to the strongest model and let them
# downgrade deliberately. Both are overridable in .env.
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_EFFORT = "high"
MAX_INPUT_ITEMS = 45
MAX_HEADLINE_CHARS = 140
MAX_SUMMARY_CHARS = 400

LABELS = ("official", "report", "rumour")


# ---------------------------------------------------------------------------
# Schemas — note what is ABSENT: no url, no date, no source name.
# ---------------------------------------------------------------------------

class CuratedStory(BaseModel):
    """One real-world event, however many outlets covered it."""
    item_ids: list[int] = Field(
        description="Every input item_id that is this SAME story. One event, one entry."
    )
    lead_item_id: int = Field(
        description="Which item_id to link. Prefer the most authoritative outlet."
    )
    headline: str = Field(description="A clear headline, under 140 characters.")
    summary: str = Field(description="2-3 sentences. Only facts present in the input.")
    evidence_quote: str = Field(
        description="A verbatim span copied from the provided text supporting the summary."
    )
    label: Literal["official", "report", "rumour"]
    is_leak_derived: bool = Field(
        description="True if the CLAIM originates from leaked material, rather than the "
                    "article merely being about the existence of a leak."
    )
    importance: int = Field(description="1-10. How much a GTA 6 fan would care.")
    insufficient_text: bool = Field(
        description="True if the input is too thin to summarise honestly. Leave summary empty."
    )


class Curation(BaseModel):
    stories: list[CuratedStory]
    dropped_item_ids: list[int] = Field(
        default_factory=list,
        description="Items that are not GTA-relevant, are pure clickbait, or duplicate "
                    "a story already listed."
    )


@dataclass
class CurationOutcome:
    stories: list[CuratedStory] = field(default_factory=list)
    dropped_ids: list[int] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def cost_usd(self) -> float:
        """Rough cost. Rates per million tokens, from the claude-api skill."""
        rates = {
            "claude-opus-5": (5.0, 25.0),
            "claude-fable-5": (10.0, 50.0),
            "claude-sonnet-5": (2.0, 10.0),
            "claude-haiku-4-5": (1.0, 5.0),
        }
        rin, rout = rates.get(self.model, (5.0, 25.0))
        return self.input_tokens / 1e6 * rin + self.output_tokens / 1e6 * rout


SYSTEM_PROMPT = """\
You are the editorial filter for a GTA 6 news channel run by a roleplay community.

Your job, in priority order:
1. GROUP items that report the SAME real-world event into one story, even when the
   headlines share almost no words. Different outlets word the same announcement
   very differently; that grouping is the single most valuable thing you do.
2. LABEL how well-sourced the claim is.
3. RANK by how much a GTA 6 fan would actually care.
4. SUMMARISE in 2-3 sentences.

LABELS — these describe the CLAIM, not the topic:
  official — a first-party Rockstar or Take-Two announcement, or a direct quote
             from one. A Rockstar statement is a FACT even when its subject is a
             leak: "Rockstar said the leaks are heartbreaking" is official.
  report   — a reputable outlet reporting something as established.
  rumour   — unconfirmed, hedged, single-sourced, or a claim whose ONLY source is
             leaked material.

Set is_leak_derived=true only when the CLAIM ITSELF comes from leaked material
(e.g. "the leak shows a fuel gauge"). An article about the existence of a leak,
or a company responding to one, is NOT leak-derived.

HARD RULES:
- Summarise ONLY from the text provided between the item markers. Use no outside
  knowledge about GTA 6, Rockstar or Take-Two.
- Never state a release date, price, platform or feature that is not literally
  written in the provided text.
- If an item reports a rumour or leak, your summary must say who claimed it.
- Do NOT output any URL, link or date. You will only ever echo item_id numbers.
- evidence_quote must be copied VERBATIM from the provided text, at least 30
  characters. If you cannot copy one, set insufficient_text=true.
- If the provided text is too thin to summarise honestly, set
  insufficient_text=true and leave summary empty. Do not guess.
- Put every item you are not reporting into dropped_item_ids. Every input id must
  appear exactly once across stories[].item_ids and dropped_item_ids.
"""


def build_user_prompt(items: list[dict], max_stories: int) -> str:
    """
    Render the candidate items. Deterministic, so it is unit-testable and so the
    prompt prefix stays cache-stable.
    """
    lines = [
        f"Select and rank at most {max_stories} stories from the {len(items)} items below.",
        "",
    ]
    for it in items:
        lines.append(f"<item id={int(it['id'])}>")
        lines.append(f"outlet: {it.get('source_name') or it.get('source_domain') or 'unknown'}")
        lines.append(f"tier: {it.get('tier')}")
        lines.append(f"headline: {it.get('title') or ''}")
        body = (it.get("summary_raw") or "").strip()
        if body:
            lines.append(f"text: {body[:1200]}")
        lines.append("</item>")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deterministic validation — the part that does not need the API
# ---------------------------------------------------------------------------

_NUM_RE = re.compile(r"\b\d[\d,.]*\b")


def _norm(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def quote_is_grounded(quote: str, source_text: str, *, min_len: int = 30) -> bool:
    """
    The highest-value check: is the evidence span really in the source?

    Converts an unverifiable generative claim into a string-containment test.
    """
    if not quote or len(quote.strip()) < min_len:
        return False
    return _norm(quote) in _norm(source_text)


def numbers_are_grounded(summary: str, source_text: str) -> tuple[bool, list[str]]:
    """
    Every number in the summary must appear in the source.

    For this channel the highest-stakes hallucination is an invented release
    date or price, and both are numbers.
    """
    src = _norm(source_text).replace(",", "")
    bad = []
    for tok in _NUM_RE.findall(summary or ""):
        clean = tok.rstrip(".").replace(",", "")
        if not clean:
            continue
        # Ignore trivially small numbers ("2 protagonists") which are rarely
        # the dangerous kind and often reworded legitimately.
        if len(clean) < 3:
            continue
        if clean.casefold() not in src:
            bad.append(tok)
    return (not bad), bad


def validate_story(
    story: CuratedStory, by_id: dict[int, dict], *, max_stories: int
) -> tuple[bool, str]:
    """Check one returned story against the input. Returns (ok, reason)."""
    if story.insufficient_text:
        return False, "model declared insufficient_text"
    ids = [int(i) for i in (story.item_ids or [])]
    if not ids:
        return False, "no item_ids"
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        return False, f"invented item_ids {unknown}"
    if int(story.lead_item_id) not in ids:
        return False, "lead_item_id is not among item_ids"
    if not story.headline.strip():
        return False, "empty headline"
    if len(story.headline) > MAX_HEADLINE_CHARS * 2:
        return False, "headline absurdly long"
    if story.label not in LABELS:
        return False, f"invalid label {story.label!r}"

    source_text = "\n".join(
        f"{by_id[i].get('title') or ''}\n{by_id[i].get('summary_raw') or ''}" for i in ids
    )
    if not quote_is_grounded(story.evidence_quote, source_text):
        return False, "evidence_quote is not a verbatim span of the source"
    ok, bad = numbers_are_grounded(story.summary, source_text)
    if not ok:
        return False, f"summary contains numbers absent from the source: {bad}"
    return True, ""


def validate(curation: Curation, items: list[dict], *, max_stories: int) -> CurationOutcome:
    """Filter the model's output down to what survives every deterministic check."""
    by_id = {int(i["id"]): i for i in items}
    out = CurationOutcome()
    seen: set[int] = set()
    for story in curation.stories or []:
        ok, reason = validate_story(story, by_id, max_stories=max_stories)
        if not ok:
            out.rejected.append(f"{reason} (ids={story.item_ids})")
            continue
        ids = [int(i) for i in story.item_ids]
        if any(i in seen for i in ids):
            out.rejected.append(f"item reused across stories (ids={ids})")
            continue
        seen.update(ids)
        out.stories.append(story)
    out.stories.sort(key=lambda s: -int(s.importance or 0))
    out.stories = out.stories[:max_stories]
    out.dropped_ids = [int(i) for i in (curation.dropped_item_ids or []) if int(i) in by_id]
    return out


# ---------------------------------------------------------------------------
# The live call — the only part that touches the network
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    return bool(LLM_AVAILABLE and (os.environ.get("ANTHROPIC_API_KEY") or "").strip())


def curate(items: list[dict], *, max_stories: int = 8,
           model: str | None = None, effort: str | None = None) -> CurationOutcome | None:
    """
    Ask Claude to cluster, label, rank and summarise.

    Returns None on ANY failure so the caller falls back to the heuristic
    digest. This function must never raise.
    """
    if not items:
        return None
    if not is_configured():
        logger.info("LLM curation skipped: ANTHROPIC_API_KEY not set or anthropic not installed")
        return None

    model = model or (os.environ.get("LLM_DIGEST_MODEL") or "").strip() or DEFAULT_MODEL
    effort = effort or (os.environ.get("LLM_EFFORT") or "").strip() or DEFAULT_EFFORT
    payload = items[:MAX_INPUT_ITEMS]

    try:
        client = anthropic.Anthropic()
        kwargs: dict = dict(
            model=model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(payload, max_stories)}],
            output_format=Curation,
        )
        # Haiku rejects output_config.effort; only send it to models that take it.
        if not model.startswith("claude-haiku"):
            kwargs["output_config"] = {"effort": effort}

        response = client.messages.parse(**kwargs)

        # stop_reason must be checked BEFORE reading content: on a refusal the
        # output may not match the schema at all.
        if getattr(response, "stop_reason", None) == "refusal":
            detail = getattr(response, "stop_details", None)
            logger.warning("LLM refused the curation request (%s); using heuristic digest",
                           getattr(detail, "category", "unknown"))
            return None

        parsed = response.parsed_output
        if parsed is None:
            logger.warning("LLM returned no parsed output; using heuristic digest")
            return None

        outcome = validate(parsed, payload, max_stories=max_stories)
        usage = getattr(response, "usage", None)
        outcome.input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        outcome.output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        outcome.model = model

        if outcome.rejected:
            logger.warning("LLM curation: %d story/stories failed validation: %s",
                           len(outcome.rejected), "; ".join(outcome.rejected[:3]))
        logger.info("LLM curation: %d stories from %d items (%d in / %d out tokens, ~$%.4f)",
                    len(outcome.stories), len(payload), outcome.input_tokens,
                    outcome.output_tokens, outcome.cost_usd)
        if not outcome.stories:
            logger.warning("LLM curation produced nothing usable; using heuristic digest")
            return None
        return outcome

    except Exception as exc:  # deliberately broad: the digest must still post
        logger.warning("LLM curation failed (%s: %s); using heuristic digest",
                       type(exc).__name__, exc)
        return None


def label_to_display(label: str, is_leak_derived: bool) -> str:
    """
    Map the model's label onto the reader-facing one.

    The leak cap still applies, but with the distinction the keyword rule could
    not make: an article ABOUT a leak keeps its real label, while a claim
    SOURCED FROM leaked material is forced to Rumour.
    """
    from src import credibility

    if is_leak_derived:
        return credibility.LABEL_RUMOUR
    return {
        "official": credibility.LABEL_OFFICIAL,
        "report": credibility.LABEL_REPORT,
        "rumour": credibility.LABEL_RUMOUR,
    }.get(label, credibility.LABEL_REPORT)
