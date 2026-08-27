"""
Cross-outlet clustering tests.

The headlines in `NBA_*` are verbatim from a live run on 2026-08-26, where one
event occupied three of eight digest slots. They are the acceptance criterion
for this module — if they stop merging, the regression is real and user-visible.

`test_rare_token_gate_would_have_failed` documents the rejected first approach
so nobody reintroduces it.
"""
from __future__ import annotations

from src.cluster import (
    Cluster,
    build_idf,
    cluster_items,
    cosine,
    document_frequency,
    stem,
    tokenise,
    weighted_overlap,
)

NBA_A = "NBA 2K27 Teases GTA 6 Crossover Of Some Kind"
NBA_B = "NBA 2K27 Teases A GTA 6 -Themed Season Coming Later This Year"
NBA_C = "NBA 2K27 Is Teasing a GTA 6-Themed Event in Collaboration with Rockstar Games"
LEAKER = "GTA 6 leaker goes full cornball in newest videos, insists 'using crypto is the only way'"
TIMELINE = "GTA 6 Leaks: A Timeline Of The Events So Far"
OFFICIAL = "Grand Theft Auto VI: An Extended Look"
IGN_TIMES = "Grand Theft Auto 6: An Extended Look Global Release Times Confirmed"


def item(i, title, *, domain, name, tier=2, url=None, published=None, state="new", rumour=0):
    return dict(
        id=i, title=title, source_domain=domain, source_name=name, tier=tier,
        url_canonical=url or f"https://{domain}/story-{i}",
        published_epoch=published, state=state, is_rumour=rumour, summary_raw="",
    )


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def test_domain_stopwords_are_removed():
    """
    "GTA 6" appears in nearly every headline, so it carries no discriminating
    power and would inflate every similarity score toward a false merge.
    """
    toks = tokenise("GTA 6 Grand Theft Auto VI Rockstar Games crossover")
    assert "gta" not in toks and "rockstar" not in toks and "auto" not in toks
    assert "crossover" in toks


def test_stemming_collapses_inflections():
    """teases/teasing must collide or the NBA cluster cannot form."""
    assert stem("teases") == stem("teasing")
    assert stem("leaked") == stem("leaks") == stem("leak")


def test_short_tokens_are_not_mangled():
    assert stem("nba") == "nba"
    assert stem("2k27") == "2k27"


# ---------------------------------------------------------------------------
# The acceptance case
# ---------------------------------------------------------------------------

def test_nba_headlines_form_one_cluster():
    items = [
        item(1, NBA_A, domain="gamespot.com", name="GameSpot"),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku"),
        item(3, NBA_C, domain="ign.com", name="IGN"),
    ]
    clusters = cluster_items(items)
    assert len(clusters) == 1, "one event must occupy one digest slot"
    assert clusters[0].size == 3


def test_distinct_leak_stories_do_not_merge():
    items = [
        item(1, LEAKER, domain="pcgamer.com", name="PC Gamer", rumour=1),
        item(2, TIMELINE, domain="gamespot.com", name="GameSpot", rumour=1),
    ]
    assert len(cluster_items(items)) == 2


def test_full_live_set_clusters_as_expected():
    """The exact seven items observed live -> four stories."""
    items = [
        item(1, NBA_A, domain="gamespot.com", name="GameSpot"),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku"),
        item(3, NBA_C, domain="ign.com", name="IGN"),
        item(4, LEAKER, domain="pcgamer.com", name="PC Gamer", rumour=1),
        item(5, TIMELINE, domain="gamespot.com", name="GameSpot", rumour=1),
        item(6, OFFICIAL, domain="rockstargames.com", name="Rockstar Games", tier=1),
        item(7, IGN_TIMES, domain="ign.com", name="IGN"),
    ]
    clusters = cluster_items(items)
    assert len(clusters) == 4
    assert clusters[0].representative["tier"] == 1, "official news must sort first"


def test_rare_token_gate_would_have_failed():
    """
    Documents the REJECTED approach. The NBA cluster's distinctive tokens have
    df=3 precisely because three outlets covered it, so a "df <= 2 means rare"
    gate forbids exactly the cluster it was meant to find. Any cluster of size k
    has shared tokens with df >= k.
    """
    sets = [tokenise(t) for t in (NBA_A, NBA_B, NBA_C)]
    df = document_frequency(sets)
    shared = sets[0] & sets[1] & sets[2]
    assert shared, "there is a shared signature"
    assert all(df[t] >= 3 for t in shared), (
        "every shared token has df >= cluster size, which is why a rare-token "
        "gate is structurally unable to detect multi-outlet clusters"
    )


# ---------------------------------------------------------------------------
# Similarity measures
# ---------------------------------------------------------------------------

def test_weighted_overlap_separates_signal_from_noise():
    """
    Related pairs clear the threshold; unrelated pairs score exactly 0.0,
    because once "GTA 6" is stopped out they share no content tokens at all.
    That zero — not a merely-low number — is what makes a 0.30 threshold safe.
    """
    sets = [tokenise(t) for t in (NBA_A, NBA_B, NBA_C, LEAKER, TIMELINE)]
    idf = build_idf(sets)
    assert weighted_overlap(sets[0], sets[1], idf) >= 0.30
    assert weighted_overlap(sets[1], sets[2], idf) >= 0.30
    assert weighted_overlap(sets[3], sets[4], idf) == 0.0


def test_similarity_is_stable_across_batch_sizes():
    """
    MIN_EFFECTIVE_CORPUS exists so clustering does not behave differently on a
    quiet day than a busy one.

    Without the floor, IDF is computed over the literal batch and treats a term
    present in every document as uninformative — so a 3-item batch that is
    entirely ONE story gives its own signature the minimum weight. The same pair
    then measured 0.25 at N=3, 0.33 at N=5 and 0.37 at N=7. With the floor the
    score is identical regardless of how many unrelated items happen to arrive.
    """
    trio = [tokenise(t) for t in (NBA_A, NBA_B, NBA_C)]
    small = weighted_overlap(trio[0], trio[1], build_idf(trio))

    wider = trio + [tokenise(t) for t in (LEAKER, TIMELINE, OFFICIAL, IGN_TIMES)]
    large = weighted_overlap(trio[0], trio[1], build_idf(wider))

    assert small == large, "score must not depend on unrelated items in the batch"
    assert small >= 0.35, "and it must clear the merge threshold"


def test_single_token_headline_cannot_swallow_everything():
    """
    "GTA 6 delayed" reduces to one content token. Without the two-shared-token
    guard it would score a perfect overlap against every delay story.
    """
    items = [
        item(1, "GTA 6 delayed", domain="ign.com", name="IGN"),
        item(2, "Rockstar delayed the announcement of a new GTA Online update",
             domain="kotaku.com", name="Kotaku"),
    ]
    assert len(cluster_items(items)) == 2


def test_empty_and_stopword_only_titles_do_not_crash():
    items = [
        item(1, "", domain="a.com", name="A"),
        item(2, "GTA 6", domain="b.com", name="B"),
        item(3, NBA_A, domain="c.com", name="C"),
    ]
    clusters = cluster_items(items)
    assert sum(c.size for c in clusters) == 3


def test_cosine_and_overlap_are_zero_for_disjoint_sets():
    idf = {"a": 2.0, "b": 2.0}
    assert cosine({"a"}, {"b"}, idf) == 0.0
    assert weighted_overlap({"a"}, {"b"}, idf) == 0.0


# ---------------------------------------------------------------------------
# Representative selection
# ---------------------------------------------------------------------------

def test_representative_prefers_lower_tier():
    c = Cluster(members=[
        item(1, IGN_TIMES, domain="ign.com", name="IGN", tier=2),
        item(2, OFFICIAL, domain="rockstargames.com", name="Rockstar Games", tier=1),
    ])
    assert c.representative["id"] == 2


def test_representative_prefers_direct_url_over_wrapper():
    """
    This is what reclaims the embed budget: a Google News wrapper is 300+ chars
    of base64, the publisher's own URL is ~60.
    """
    wrapper = "https://news.google.com/rss/articles/" + "x" * 280
    c = Cluster(members=[
        item(1, NBA_A, domain="kotaku.com", name="Kotaku", url=wrapper, published=100),
        item(2, NBA_A, domain="gamespot.com", name="GameSpot",
             url="https://gamespot.com/nba-2k27", published=200),
    ])
    assert c.representative["id"] == 2
    assert "news.google.com" not in c.representative["url_canonical"]


def test_tier_beats_url_prettiness():
    """Authority outranks cosmetics: a tier-1 wrapper still wins."""
    wrapper = "https://news.google.com/rss/articles/" + "x" * 280
    c = Cluster(members=[
        item(1, OFFICIAL, domain="rockstargames.com", name="Rockstar Games",
             tier=1, url=wrapper),
        item(2, IGN_TIMES, domain="ign.com", name="IGN", tier=2,
             url="https://ign.com/short"),
    ])
    assert c.representative["tier"] == 1


def test_outlets_lists_representative_first_and_dedupes():
    c = Cluster(members=[
        item(1, NBA_A, domain="gamespot.com", name="GameSpot", published=100),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku", published=200),
        item(3, NBA_C, domain="gamespot.com", name="GameSpot", published=300),
    ])
    assert c.outlets[0] == "GameSpot"
    assert c.outlets.count("GameSpot") == 1
    assert "Kotaku" in c.other_outlets


# ---------------------------------------------------------------------------
# Corroboration counting — the gap this closes
# ---------------------------------------------------------------------------

def test_corroboration_counts_distinct_tier2_domains():
    c = Cluster(members=[
        item(1, NBA_A, domain="gamespot.com", name="GameSpot", tier=2),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku", tier=2),
        item(3, NBA_C, domain="ign.com", name="IGN", tier=2),
    ])
    assert c.tier2_corroborations() == 3


def test_same_domain_twice_counts_once():
    """Two GameSpot articles are not two independent confirmations."""
    c = Cluster(members=[
        item(1, NBA_A, domain="gamespot.com", name="GameSpot", tier=2),
        item(2, NBA_B, domain="gamespot.com", name="GameSpot", tier=2),
    ])
    assert c.tier2_corroborations() == 1


def test_corroboration_excludes_own_domain():
    """An outlet may not corroborate itself."""
    c = Cluster(members=[
        item(1, NBA_A, domain="rockstarintel.com", name="RockstarINTEL", tier=3),
        item(2, NBA_B, domain="gamespot.com", name="GameSpot", tier=2),
    ])
    assert c.tier2_corroborations(exclude_domain="gamespot.com") == 0
    assert c.tier2_corroborations(exclude_domain="rockstarintel.com") == 1


def test_tier3_and_below_do_not_corroborate():
    c = Cluster(members=[
        item(1, NBA_A, domain="rockstarintel.com", name="RockstarINTEL", tier=3),
        item(2, NBA_B, domain="unknown.example", name="Unknown", tier=4),
    ])
    assert c.tier2_corroborations() == 0


def test_any_rumour_is_detected():
    c = Cluster(members=[
        item(1, NBA_A, domain="gamespot.com", name="GameSpot"),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku", rumour=1),
    ])
    assert c.any_rumour is True


# ---------------------------------------------------------------------------
# Transitive-chaining guard (regression: one cluster swallowed 57 of 140 items)
# ---------------------------------------------------------------------------

def test_chain_does_not_merge_unrelated_ends():
    """
    A~B and B~C must NOT put A and C together.

    This is why leader clustering replaced union-find. Single-linkage takes the
    transitive closure, so in a corpus that is all one franchise it chains
    almost everything into a single blob. Small fixtures cannot catch it —
    there is nothing to chain through with 7 items.
    """
    items = [
        item(1, "Rockstar confirms Vice City map details", domain="ign.com", name="IGN"),
        item(2, "Vice City map details leak alongside airport footage",
             domain="kotaku.com", name="Kotaku"),
        item(3, "Airport footage shows new wanted system",
             domain="pcgamer.com", name="PC Gamer"),
        item(4, "New wanted system compared to RDR2 honor",
             domain="vgc.com", name="VGC"),
        item(5, "RDR2 honor system returns in some form",
             domain="gamespot.com", name="GameSpot"),
    ]
    clusters = cluster_items(items)
    for c in clusters:
        titles = {m["title"] for m in c.members}
        assert not (
            "Rockstar confirms Vice City map details" in titles
            and "RDR2 honor system returns in some form" in titles
        ), "opposite ends of a similarity chain must not share a cluster"


def test_large_same_topic_corpus_does_not_collapse_into_one_cluster():
    """140 leak headlines must not become one story."""
    items = [
        item(i, f"GTA 6 leak day {i} shows {thing}", domain=f"site{i}.example",
             name=f"Site{i}")
        for i, thing in enumerate([
            "a nightclub", "an airport", "a strip club", "the wasted screen",
            "nudist town", "physical media", "a fuel gauge", "weapon storage",
            "a honor meter", "focus stats", "vehicle damage", "a metro station",
            "beach traffic", "police chases", "a hospital interior",
        ])
    ]
    clusters = cluster_items(items)
    biggest = max(c.size for c in clusters)
    assert biggest <= 12, f"largest cluster is {biggest}; over-merging"
    assert len(clusters) >= 5, f"only {len(clusters)} clusters from 15 distinct stories"


def test_max_cluster_size_bounds_leader_assignment_not_deliberate_merging():
    """
    `max_cluster_size` is a backstop on the LEADER pass, where chaining could
    run away. The second pass merges whole clusters on their combined
    vocabularies, and there the similarity IS the control — a genuinely huge
    story legitimately exceeds the cap. Rockstar's statement on the leaks drew
    32 items across 11 initially-separate clusters on 2026-08-27; splitting that
    into arbitrary chunks of 12 would be worse than one honest line.

    What must always hold is that no item is lost or duplicated.
    """
    identical = [
        item(i, "NBA 2K27 Teases GTA 6 Crossover Of Some Kind",
             domain=f"s{i}.example", name=f"S{i}")
        for i in range(30)
    ]
    clusters = cluster_items(identical, max_cluster_size=5)
    assert sum(c.size for c in clusters) == 30, "no item may be dropped"
    ids = [m["id"] for c in clusters for m in c.members]
    assert len(ids) == len(set(ids)), "an item was duplicated across clusters"
    # 30 copies of one headline is ONE story.
    assert len(clusters) == 1, f"identical headlines should collapse, got {len(clusters)}"


def test_cluster_merge_can_be_disabled():
    """The second pass is tunable, so a caller can opt out."""
    identical = [
        item(i, "NBA 2K27 Teases GTA 6 Crossover Of Some Kind",
             domain=f"s{i}.example", name=f"S{i}")
        for i in range(30)
    ]
    clusters = cluster_items(identical, max_cluster_size=5,
                             cluster_merge_threshold=2.0)  # unreachable
    assert all(c.size <= 5 for c in clusters)
    assert sum(c.size for c in clusters) == 30


def test_cluster_merge_unites_differently_worded_reports_of_one_event():
    """
    Verbatim headlines from 2026-08-27. Leader comparison left these in separate
    clusters because they share almost no words; the union-based second pass
    recognises them as one event.
    """
    heads = [
        "Rockstar issues statement on GTA 6 gameplay leaks, calling them heartbreaking and warning they may include some spoilers",
        "Rockstar Games finally breaks silence on GTA 6 leaks, says it has been heartbreaking for our team",
        "Rockstar Games Responds to GTA 6 Leaks and Apologizes to Players",
        "Rockstar Games Releases Official Response to Heartbreaking GTA 6 Leaks",
    ]
    items = [item(i, h, domain=f"o{i}.example", name=f"O{i}") for i, h in enumerate(heads)]
    clusters = cluster_items(items)
    assert len(clusters) <= 2, (
        f"one event should not occupy {len(clusters)} digest slots: "
        f"{[c.representative['title'][:40] for c in clusters]}"
    )


def test_cluster_merge_keeps_genuinely_different_stories_apart():
    """The merge pass must not collapse the whole day into one line."""
    items = [
        item(1, "Rockstar issues statement on GTA 6 gameplay leaks calling them heartbreaking",
             domain="a.example", name="A"),
        item(2, "NBA 2K27 Teases GTA 6 Crossover Of Some Kind", domain="b.example", name="B"),
        item(3, "When to watch Grand Theft Auto 6 An Extended Look on Netflix in your time zone",
             domain="c.example", name="C"),
        item(4, "Discord is yet to be served Take-Two's GTA 6 leak subpoena",
             domain="d.example", name="D"),
    ]
    clusters = cluster_items(items)
    assert len(clusters) == 4, (
        f"four distinct stories collapsed to {len(clusters)}: "
        f"{[c.representative['title'][:34] for c in clusters]}"
    )


def test_every_item_lands_in_exactly_one_cluster():
    items = [
        item(1, NBA_A, domain="gamespot.com", name="GameSpot"),
        item(2, NBA_B, domain="kotaku.com", name="Kotaku"),
        item(3, LEAKER, domain="pcgamer.com", name="PC Gamer"),
        item(4, OFFICIAL, domain="rockstargames.com", name="Rockstar", tier=1),
        item(5, "", domain="x.example", name="X"),
    ]
    clusters = cluster_items(items)
    ids = [m["id"] for c in clusters for m in c.members]
    assert sorted(ids) == [1, 2, 3, 4, 5]
    assert len(ids) == len(set(ids)), "an item was duplicated across clusters"
