"""
LLM curation guardrail tests.

None of these call the API. That is the point: every guardrail is a pure
function precisely so it can be tested without a key, without cost, and without
network flakiness — and so a model that misbehaves is caught deterministically
rather than hopefully.

The invariant these defend: the bot must never publish a claim the source text
does not support, and must never stop posting because the LLM had a bad day.
"""
from __future__ import annotations

import pytest

from src import llm

pytestmark = pytest.mark.skipif(not llm.LLM_AVAILABLE,
                                reason="anthropic/pydantic not installed")

ITEMS = [
    dict(id=1, title="Rockstar issues statement on GTA 6 leaks",
         summary_raw="Rockstar Games said the leaks 'have been heartbreaking for our team' "
                     "and warned they may contain spoilers.",
         source_name="Eurogamer", source_domain="eurogamer.net", tier=2,
         url_canonical="https://eurogamer.net/a"),
    dict(id=2, title="GTA 6 leaks heartbreaking, says Rockstar",
         summary_raw="The studio broke its silence on the gameplay leaks this week.",
         source_name="VGC", source_domain="videogameschronicle.com", tier=2,
         url_canonical="https://videogameschronicle.com/b"),
    dict(id=3, title="Extended Look premieres on Netflix",
         summary_raw="Grand Theft Auto VI: An Extended Look premieres August 27 on Netflix.",
         source_name="IGN", source_domain="ign.com", tier=2,
         url_canonical="https://ign.com/c"),
]
BY_ID = {i["id"]: i for i in ITEMS}


def story(**kw):
    base = dict(
        item_ids=[1, 2], lead_item_id=1,
        headline="Rockstar calls the GTA 6 leaks heartbreaking",
        summary="Rockstar Games said the leaks have been heartbreaking for its team.",
        evidence_quote="have been heartbreaking for our team",
        label="official", is_leak_derived=False, importance=9,
        insufficient_text=False,
    )
    base.update(kw)
    return llm.CuratedStory(**base)


# ---------------------------------------------------------------------------
# The model must never emit a URL or a date
# ---------------------------------------------------------------------------

def test_schema_has_no_url_or_date_field():
    """
    Structural guardrail: a model cannot hallucinate a link it is never asked
    to produce. The URL is looked up from the DB row by item_id instead.
    """
    fields = set(llm.CuratedStory.model_fields)
    for forbidden in ("url", "link", "href", "date", "published", "source_url"):
        assert forbidden not in fields, f"schema exposes {forbidden!r} to the model"
    assert "lead_item_id" in fields
    assert "item_ids" in fields


def test_prompt_forbids_urls_and_outside_knowledge():
    p = llm.SYSTEM_PROMPT
    assert "Do NOT output any URL" in p
    assert "no outside" in p or "Use no outside knowledge" in p
    assert "insufficient_text=true" in p


# ---------------------------------------------------------------------------
# evidence_quote grounding
# ---------------------------------------------------------------------------

def test_verbatim_quote_is_accepted():
    src = "Rockstar Games said the leaks have been heartbreaking for our team."
    assert llm.quote_is_grounded("have been heartbreaking for our team", src)


def test_invented_quote_is_rejected():
    src = "Rockstar Games said the leaks have been heartbreaking for our team."
    assert not llm.quote_is_grounded("Rockstar confirmed a 2027 delay is likely", src)


def test_quote_matching_ignores_whitespace_differences():
    src = "Rockstar   said   the  leaks\nhave been heartbreaking for our team."
    assert llm.quote_is_grounded("said the leaks have been heartbreaking", src)


def test_too_short_quote_is_rejected():
    """A three-word 'quote' proves nothing and matches almost anything."""
    assert not llm.quote_is_grounded("the leaks", "the leaks were bad", min_len=30)


def test_empty_quote_is_rejected():
    assert not llm.quote_is_grounded("", "anything at all here to match against")


# ---------------------------------------------------------------------------
# Number grounding — the invented-release-date guard
# ---------------------------------------------------------------------------

def test_numbers_present_in_source_are_accepted():
    ok, bad = llm.numbers_are_grounded(
        "The Extended Look premieres August 27 in 2026.",
        "Grand Theft Auto VI: An Extended Look premieres August 27 2026 on Netflix.")
    assert ok, bad


def test_invented_release_date_is_caught():
    """The highest-stakes hallucination for this channel."""
    ok, bad = llm.numbers_are_grounded(
        "Rockstar confirmed the game slips to 2027.",
        "Rockstar Games said the leaks have been heartbreaking.")
    assert not ok
    assert "2027" in bad


def test_invented_price_is_caught():
    ok, bad = llm.numbers_are_grounded(
        "The Ultimate Edition costs 129 dollars.",
        "Rockstar announced pre-orders open on June 25.")
    assert not ok
    assert "129" in bad


def test_small_numbers_are_tolerated():
    """'two protagonists' should not trip the check; it is not the dangerous kind."""
    ok, _ = llm.numbers_are_grounded("There are 2 protagonists.", "Jason and Lucia star.")
    assert ok


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------

def test_valid_story_passes():
    ok, reason = llm.validate_story(story(), BY_ID, max_stories=8)
    assert ok, reason


def test_invented_item_id_is_rejected():
    ok, reason = llm.validate_story(story(item_ids=[1, 99]), BY_ID, max_stories=8)
    assert not ok
    assert "invented item_ids" in reason


def test_lead_outside_members_is_rejected():
    """The lead supplies the URL, so it must be one of the grouped items."""
    ok, reason = llm.validate_story(story(item_ids=[1, 2], lead_item_id=3),
                                    BY_ID, max_stories=8)
    assert not ok
    assert "lead_item_id" in reason


def test_insufficient_text_story_is_dropped():
    ok, reason = llm.validate_story(story(insufficient_text=True), BY_ID, max_stories=8)
    assert not ok
    assert "insufficient_text" in reason


def test_ungrounded_quote_fails_validation():
    ok, reason = llm.validate_story(
        story(evidence_quote="Rockstar promised a PC version at launch"),
        BY_ID, max_stories=8)
    assert not ok
    assert "verbatim" in reason


def test_hallucinated_number_fails_validation():
    ok, reason = llm.validate_story(
        story(summary="Rockstar said the leaks were heartbreaking and confirmed 2027."),
        BY_ID, max_stories=8)
    assert not ok
    assert "numbers absent" in reason


# ---------------------------------------------------------------------------
# Whole-curation validation
# ---------------------------------------------------------------------------

def test_validate_keeps_good_and_drops_bad():
    c = llm.Curation(stories=[story(), story(item_ids=[3], lead_item_id=3,
                                             evidence_quote="INVENTED QUOTE NOT IN SOURCE AT ALL")],
                     dropped_item_ids=[])
    out = llm.validate(c, ITEMS, max_stories=8)
    assert len(out.stories) == 1
    assert len(out.rejected) == 1


def test_item_cannot_appear_in_two_stories():
    """
    Otherwise the same item is published twice and marked sent once.

    The second story's quote is deliberately grounded in item 2, so it reaches
    the reuse check rather than being rejected earlier for the quote.
    """
    second = story(
        item_ids=[2], lead_item_id=2,
        evidence_quote="broke its silence on the gameplay leaks this week",
    )
    c = llm.Curation(stories=[story(item_ids=[1, 2]), second], dropped_item_ids=[])
    out = llm.validate(c, ITEMS, max_stories=8)
    assert len(out.stories) == 1
    assert any("reused" in r for r in out.rejected), out.rejected


def test_stories_are_ordered_by_importance():
    c = llm.Curation(stories=[
        story(item_ids=[3], lead_item_id=3, importance=2,
              evidence_quote="An Extended Look premieres August 27 on Netflix"),
        story(item_ids=[1, 2], importance=9),
    ])
    out = llm.validate(c, ITEMS, max_stories=8)
    assert [s.importance for s in out.stories] == [9, 2]


def test_max_stories_is_enforced():
    c = llm.Curation(stories=[
        story(item_ids=[1], lead_item_id=1, importance=5),
        story(item_ids=[2], lead_item_id=2, importance=4,
              evidence_quote="broke its silence on the gameplay leaks this week"),
        story(item_ids=[3], lead_item_id=3, importance=3,
              evidence_quote="An Extended Look premieres August 27 on Netflix"),
    ])
    out = llm.validate(c, ITEMS, max_stories=2)
    assert len(out.stories) == 2


def test_dropped_ids_are_filtered_to_known_items():
    c = llm.Curation(stories=[story()], dropped_item_ids=[3, 999])
    out = llm.validate(c, ITEMS, max_stories=8)
    assert out.dropped_ids == [3]


# ---------------------------------------------------------------------------
# Label mapping — the distinction the keyword cap could not make
# ---------------------------------------------------------------------------

def test_official_statement_about_a_leak_stays_official():
    """
    The whole point of the LLM label. "Rockstar said the leaks are heartbreaking"
    is a FACT; the keyword rule called it Rumour because it contains "leak".
    """
    from src import credibility
    assert llm.label_to_display("official", False) == credibility.LABEL_OFFICIAL


def test_claim_sourced_from_a_leak_is_still_capped_at_rumour():
    """The editorial rule survives: leak-derived claims never become fact."""
    from src import credibility
    assert llm.label_to_display("official", True) == credibility.LABEL_RUMOUR
    assert llm.label_to_display("report", True) == credibility.LABEL_RUMOUR


def test_unknown_label_falls_back_to_report():
    from src import credibility
    assert llm.label_to_display("nonsense", False) == credibility.LABEL_REPORT


# ---------------------------------------------------------------------------
# Degradation — the bot must still post
# ---------------------------------------------------------------------------

def test_curate_returns_none_without_a_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert llm.curate(ITEMS) is None


def test_curate_returns_none_on_empty_input():
    assert llm.curate([]) is None


def test_curate_never_raises_when_the_client_explodes(monkeypatch):
    """Any exception must degrade, not propagate — the digest still has to post."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("network on fire")

    monkeypatch.setattr(llm.anthropic, "Anthropic", Boom)
    assert llm.curate(ITEMS) is None


def test_curate_degrades_on_refusal(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    class Resp:
        stop_reason = "refusal"
        stop_details = type("D", (), {"category": "test"})()
        parsed_output = None
        usage = None

    class Msgs:
        def parse(self, **kw):
            return Resp()

    class Client:
        def __init__(self, *a, **k):
            self.messages = Msgs()

    monkeypatch.setattr(llm.anthropic, "Anthropic", Client)
    assert llm.curate(ITEMS) is None


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_prompt_includes_every_item_id():
    p = llm.build_user_prompt(ITEMS, 8)
    for i in (1, 2, 3):
        assert f"<item id={i}>" in p


def test_prompt_is_deterministic():
    """Stable prefix keeps prompt caching viable and makes the test meaningful."""
    assert llm.build_user_prompt(ITEMS, 8) == llm.build_user_prompt(ITEMS, 8)


def test_cost_estimate_uses_the_model_rate():
    out = llm.CurationOutcome(model="claude-opus-5",
                              input_tokens=1_000_000, output_tokens=0)
    assert out.cost_usd == pytest.approx(5.0)
    cheap = llm.CurationOutcome(model="claude-haiku-4-5",
                                input_tokens=1_000_000, output_tokens=0)
    assert cheap.cost_usd == pytest.approx(1.0)
