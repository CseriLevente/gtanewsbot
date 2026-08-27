"""
Cross-outlet story clustering.

The problem this solves, observed live on 2026-08-26: one event (an NBA 2K27 /
GTA 6 crossover tease) occupied three of eight digest slots because GameSpot,
Kotaku and IGN each worded the headline differently. Exact title hashing cannot
catch that; only similarity can.

Clustering buys three things at once:

  1. one line per story instead of one per outlet;
  2. a shorter canonical link — a cluster containing both a Google News wrapper
     (300+ chars of base64) and the publisher's own URL prefers the publisher,
     which reclaims a large slice of the 6000-char embed budget;
  3. the corroboration count. `credibility.judge()` takes
     `tier2_corroborations` but every caller passed 0, so tier-3 and tier-4
     items were held forever. A cluster's distinct tier-2 publisher count IS
     that number.

WHY IDF WEIGHTING, NOT PLAIN JACCARD
------------------------------------
Every headline in this corpus contains "GTA 6" or "Grand Theft Auto VI", so
those tokens carry no discriminating power while inflating any set-overlap
measure toward a false merge. They are treated as domain stopwords.

What is left is short — five to eight tokens — so plain Jaccard is dominated by
length mismatch: the NBA headlines above share three tokens out of five and
eight, giving Jaccard 0.30, which is indistinguishable from noise. The actual
signal is that "nba" and "2k27" are RARE in the day's corpus. IDF weighting is
what turns that intuition into a number, so a shared rare token counts for far
more than a shared common one.

A REJECTED APPROACH, RECORDED SO IT IS NOT RETRIED
-------------------------------------------------
The first implementation gated merges on "shares >= 2 RARE tokens", where rare
meant document frequency <= ~6% of the corpus. It failed on the exact case it
was written for, and the reason is structural: the NBA headlines' distinctive
tokens ("nba", "2k27") had df=3 precisely BECAUSE three outlets covered the
story. A token shared by a k-member cluster has df >= k, so demanding df <= 2
makes any cluster larger than two impossible. The rule forbade what it was
meant to detect.

WHAT IS USED INSTEAD
--------------------
The weighted overlap coefficient — shared IDF weight over the SHORTER
document's total weight:

    wov(A,B) = sum(idf^2 for t in A&B) / min(sum(idf^2 in A), sum(idf^2 in B))

Measured on the live headlines, the NBA pairs score 0.44-0.53 while every
unrelated pair scores exactly 0.000 — a wide, safe margin against the 0.35
threshold. Dividing by the shorter document is what makes it robust to the
length mismatch that defeats Jaccard here.

Two guards keep it honest:
  * at least 2 shared tokens, so a one-token headline ("GTA 6 delayed" reduces
    to {delay}) cannot achieve wov=1.0 against anything mentioning delays;
  * a strong-cosine path, so genuinely similar long headlines merge even if the
    overlap ratio is diluted.

CORPUS-SIZE STABILITY
---------------------
IDF is defined relative to a corpus, and its premise is that a term appearing in
EVERY document is uninformative. That premise inverts here: in a three-item
batch where all three items are the SAME story, the shared signature would get
the minimum weight log(3/3)+1 = 1.0 — IDF declaring the signature worthless
exactly when it is the entire signal. Scores would then drift with batch size
(the same NBA pair measured 0.25 at N=3, 0.33 at N=5, 0.37 at N=7), so
clustering would behave differently on a quiet day than a busy one.

MIN_EFFECTIVE_CORPUS removes that by flooring the document count used for IDF.
Scores become batch-independent and the threshold can be set on merit. Unrelated
headlines score exactly 0.0 — not merely low — because once "GTA 6" is stopped
out they share no content tokens at all, so the margin is wide.
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field

from src.canonical import is_wrapper, normalise_title

logger = logging.getLogger(__name__)

# Tokens present in nearly every headline here, so they discriminate nothing.
_DOMAIN_STOPWORDS = frozenset({
    "gta", "grand", "theft", "auto", "vi", "v", "6", "5", "rockstar", "games",
    "game", "rockstars",
})

# Ordinary English function words.
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "there", "here", "we", "you",
    "he", "she", "they", "them", "his", "her", "their", "our", "your", "i",
    "not", "no", "so", "if", "than", "then", "when", "while", "after", "before",
    "some", "any", "all", "more", "most", "new", "now", "just", "also", "very",
    "can", "could", "will", "would", "may", "might", "should", "has", "have",
    "had", "do", "does", "did", "get", "gets", "got", "one", "two", "about",
    "into", "out", "up", "down", "over", "under", "again", "still", "what",
    "which", "who", "how", "why", "amid", "ahead", "via", "per", "s", "t",
}) | _DOMAIN_STOPWORDS

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Crude suffix stripping. Not linguistically correct, but it makes
# "teases"/"teasing" collide, which is exactly what the NBA case needs.
_SUFFIXES = ("ingly", "edly", "ing", "ies", "ied", "es", "ed", "ly", "s")


def stem(token: str) -> str:
    """Strip a common inflectional suffix. Short tokens are left alone."""
    if len(token) <= 4 or token.isdigit():
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            base = token[: -len(suf)]
            # "ies" -> "y" reads better ("stories" -> "story")
            if suf == "ies":
                return base + "y"
            return base
    return token


def tokenise(title: str) -> set[str]:
    """Content tokens of a headline: normalised, stopped and stemmed."""
    words = _TOKEN_RE.findall(normalise_title(title))
    return {stem(w) for w in words if w not in _STOPWORDS and len(w) > 1}


# IDF is computed against an assumed minimum corpus rather than the literal
# batch. Rationale: we want "how distinctive is this token in GTA 6 news
# generally", not "in the 3 items that happened to arrive this run". Without the
# floor, a batch of 3 items that are all ONE story gives its shared signature
# the minimum weight log(3/3)+1 = 1.0 — IDF concluding the signature is
# worthless precisely when it is the entire signal. Clustering would then behave
# differently on a quiet day than a busy one, which is indefensible.
MIN_EFFECTIVE_CORPUS = 20


def build_idf(token_sets: list[set[str]]) -> dict[str, float]:
    """
    Inverse document frequency, floored at MIN_EFFECTIVE_CORPUS documents.

    The floor makes similarity scores stable across batch sizes.
    """
    n = max(len(token_sets), MIN_EFFECTIVE_CORPUS)
    df: dict[str, int] = {}
    for ts in token_sets:
        for t in ts:
            df[t] = df.get(t, 0) + 1
    return {t: math.log(n / c) + 1.0 for t, c in df.items()}


def document_frequency(token_sets: list[set[str]]) -> dict[str, int]:
    df: dict[str, int] = {}
    for ts in token_sets:
        for t in ts:
            df[t] = df.get(t, 0) + 1
    return df


def cosine(a: set[str], b: set[str], idf: dict[str, float]) -> float:
    """IDF-weighted cosine over binary term vectors."""
    if not a or not b:
        return 0.0
    shared = a & b
    if not shared:
        return 0.0
    num = sum(idf.get(t, 1.0) ** 2 for t in shared)
    na = math.sqrt(sum(idf.get(t, 1.0) ** 2 for t in a))
    nb = math.sqrt(sum(idf.get(t, 1.0) ** 2 for t in b))
    if na == 0 or nb == 0:
        return 0.0
    return num / (na * nb)


def weighted_overlap(a: set[str], b: set[str], idf: dict[str, float]) -> float:
    """
    Shared IDF weight as a fraction of the SHORTER document's weight.

    Dividing by the shorter document is the point: news headlines about one
    event vary wildly in length, and a symmetric measure (Jaccard, cosine) is
    then dominated by that mismatch rather than by topical agreement.
    """
    if not a or not b:
        return 0.0
    shared = a & b
    if not shared:
        return 0.0
    num = sum(idf.get(t, 1.0) ** 2 for t in shared)
    wa = sum(idf.get(t, 1.0) ** 2 for t in a)
    wb = sum(idf.get(t, 1.0) ** 2 for t in b)
    denom = min(wa, wb)
    return num / denom if denom else 0.0


@dataclass
class Cluster:
    """One story, as reported by one or more outlets."""
    members: list[dict] = field(default_factory=list)

    @property
    def representative(self) -> dict:
        """
        The member whose link and attribution the digest will use.

        Order of preference:
          1. lowest tier  — authority beats cosmetics
          2. a direct publisher URL over an aggregator wrapper (within a tier)
          3. published earliest — the outlet that broke it
          4. longest title — usually the most informative phrasing
        """
        return min(
            self.members,
            key=lambda m: (
                int(m.get("tier") or 9),
                1 if is_wrapper(m.get("url_canonical") or "") else 0,
                m.get("published_epoch") or float("inf"),
                -len(m.get("title") or ""),
            ),
        )

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def outlets(self) -> list[str]:
        """Distinct publisher names, representative first."""
        rep = self.representative
        seen: list[str] = []
        for m in [rep] + [x for x in self.members if x is not rep]:
            name = (m.get("source_name") or m.get("source_domain") or "").strip()
            if name and name not in seen:
                seen.append(name)
        return seen

    @property
    def other_outlets(self) -> list[str]:
        return self.outlets[1:]

    def tier2_corroborations(self, exclude_domain: str | None = None) -> int:
        """
        Count of DISTINCT tier-1/2 publisher domains reporting this story.

        Independence is approximated by distinct domain. The research's stricter
        definition (different parent company, no citation link between them,
        >20 minutes apart) cannot be evaluated from a feed alone, so this is an
        upper bound — noted here because five outlets recycling one 4chan post
        would still count as five domains. Same-domain duplicates are collapsed,
        which is the most common inflation.
        """
        domains = {
            (m.get("source_domain") or "").casefold()
            for m in self.members
            if int(m.get("tier") or 9) <= 2
        }
        domains.discard("")
        if exclude_domain:
            domains.discard(exclude_domain.casefold())
        return len(domains)

    @property
    def any_rumour(self) -> bool:
        return any(bool(m.get("is_rumour")) for m in self.members)


def cluster_items(
    items: list[dict],
    *,
    overlap_threshold: float = 0.35,
    strong_cosine: float = 0.55,
    min_shared_tokens: int = 2,
    max_cluster_size: int = 12,
    cluster_merge_threshold: float = 0.32,
    cluster_merge_min_shared: int = 3,
) -> list[Cluster]:
    """
    Group items reporting the same story.

    An item joins a cluster iff it shares at least `min_shared_tokens` content
    tokens with that cluster's LEADER and either:
        weighted_overlap >= overlap_threshold      (the primary signal)
      OR
        cosine >= strong_cosine                    (long, closely-worded pair)

    `max_cluster_size` is a backstop, not the mechanism: a genuinely huge story
    might legitimately draw 12 outlets, but anything past that is far more
    likely to be over-merging, and capping it keeps one bad cluster from
    swallowing the digest.

    O(n * clusters) rather than O(n^2), and still pure set arithmetic — far
    below the cost of a single LLM call, which is why this stage is heuristic
    by design.
    """
    if not items:
        return []

    token_sets = [tokenise(it.get("title") or "") for it in items]
    idf = build_idf(token_sets)
    n = len(items)

    df = document_frequency(token_sets)
    # "Rare" = a token carried by only a handful of the day's headlines. Scaled
    # to corpus size so it means the same thing on a quiet and a busy day.
    rare_max_df = max(3, math.ceil(0.04 * max(n, MIN_EFFECTIVE_CORPUS)))

    def similar(a: set[str], b: set[str]) -> bool:
        shared = a & b
        # Guard: a one-token headline would otherwise score a perfect overlap
        # against anything containing that token.
        if len(shared) < min_shared_tokens:
            return False
        if weighted_overlap(a, b, idf) >= overlap_threshold:
            return True
        if cosine(a, b, idf) >= strong_cosine:
            return True
        # RARE-TOKEN CO-SIGNAL.
        #
        # Measured on four real headlines about one Rockstar statement, the
        # weighted overlap between same-story pairs ran as low as 0.080 while an
        # unrelated pair sharing the word "time" scored 0.112 — the signal is
        # genuinely inverted, so no threshold can separate them. Lowering the
        # threshold to catch them would merge unrelated news.
        #
        # What those headlines DID share was a distinctive word ("heartbreak")
        # that almost nothing else that day used. A shared rare token plus at
        # least one more shared token is decent evidence of one event.
        #
        # This is ADDITIVE — it can only merge more, never less — which is why
        # it does not reintroduce the structural flaw of a df-based GATE (a
        # k-member cluster's shared tokens always have df >= k, so a gate
        # forbids the clusters it should find). The overlap path still handles
        # large clusters; this only rescues the sparse-overlap tail.
        return any(df.get(t, 0) <= rare_max_df for t in shared)

    # LEADER CLUSTERING, deliberately not union-find.
    #
    # Union-find gives SINGLE-LINKAGE clustering: A joins B, B joins C, and the
    # transitive closure merges A with C even when A and C are unrelated. In a
    # corpus that is 140 headlines all about one franchise, that chains almost
    # everything into one blob — observed live on 2026-08-26, where a single
    # cluster swallowed 57 of 140 items and would have rendered as
    # "also VGC, Kotaku, Eurogamer +53" while silently marking 56 real stories
    # as already published.
    #
    # Assigning each item to a cluster only if it matches that cluster's LEADER
    # removes transitivity: membership is always judged against one fixed
    # headline, so a chain cannot form. Small unit tests could never catch this
    # — with 7 items there is nothing to chain through.
    leaders: list[int] = []
    assigned: list[list[int]] = []

    for i in range(n):
        if not token_sets[i]:
            leaders.append(i)
            assigned.append([i])
            continue
        best_cluster = -1
        best_score = 0.0
        for c, leader in enumerate(leaders):
            if not token_sets[leader]:
                continue
            if not similar(token_sets[i], token_sets[leader]):
                continue
            # Among matching leaders, take the closest — otherwise the first
            # acceptable leader wins arbitrarily on input order.
            score = weighted_overlap(token_sets[i], token_sets[leader], idf)
            if score > best_score:
                best_score = score
                best_cluster = c
        if best_cluster >= 0 and len(assigned[best_cluster]) < max_cluster_size:
            assigned[best_cluster].append(i)
        else:
            leaders.append(i)
            assigned.append([i])

    clusters = [Cluster(members=[items[idx] for idx in group]) for group in assigned]

    # SECOND PASS: merge whole clusters on their combined vocabulary.
    #
    # Leader comparison alone left ELEVEN separate clusters for one event
    # (Rockstar's statement on the leaks, 2026-08-27) — four of them reached the
    # digest and the rest filled the overflow. Individual headlines shared too
    # little: "Rockstar responds to GTA 6 leaks" and "GTA 6 leaks have been
    # heartbreaking for our team" agree on almost no words.
    #
    # A cluster's UNION of tokens is a much richer description of the event than
    # any single headline, so the same measure discriminates far better here:
    # those eleven scored 0.41-1.00 union-to-union where leader-to-leader was
    # under 0.20. Comparing groups rather than sentences is what makes this work.
    clusters = _merge_similar_clusters(
        clusters, idf,
        threshold=cluster_merge_threshold,
        min_shared=cluster_merge_min_shared,
    )
    # Most authoritative, then biggest story, then most recent.
    clusters.sort(
        key=lambda c: (
            int(c.representative.get("tier") or 9),
            -c.size,
            -(c.representative.get("published_epoch") or 0),
        )
    )
    merged = sum(1 for c in clusters if c.size > 1)
    if merged:
        logger.info(
            "clustered %d items into %d stories (%d multi-outlet)",
            n, len(clusters), merged,
        )
    return clusters



def cluster_tokens(c: "Cluster") -> set[str]:
    """The union of every member headline's content tokens."""
    out: set[str] = set()
    for m in c.members:
        out |= tokenise(m.get("title") or "")
    return out


def _merge_similar_clusters(
    clusters: list["Cluster"], idf: dict[str, float], *,
    threshold: float, min_shared: int, max_passes: int = 4,
) -> list["Cluster"]:
    """
    Repeatedly merge cluster pairs whose combined vocabularies agree.

    `min_shared` is load-bearing, not decoration. A cluster whose only member is
    a terse headline ("Rockstar responds to GTA 6 leaks" reduces to two content
    tokens) scores a perfect 1.0 against anything containing both words, so a
    ratio alone would let it swallow unrelated stories. Requiring a few shared
    tokens confines merging to pairs with real evidence.

    Passes are bounded: each one can only reduce the cluster count, and stopping
    early keeps a pathological corpus from collapsing into one blob.
    """
    for _ in range(max_passes):
        toks = [cluster_tokens(c) for c in clusters]
        merged_into: dict[int, int] = {}
        for i in range(len(clusters)):
            if i in merged_into:
                continue
            for j in range(i + 1, len(clusters)):
                if j in merged_into:
                    continue
                shared = toks[i] & toks[j]
                if len(shared) < min_shared:
                    continue
                if weighted_overlap(toks[i], toks[j], idf) < threshold:
                    continue
                clusters[i].members.extend(clusters[j].members)
                toks[i] = toks[i] | toks[j]
                merged_into[j] = i
        if not merged_into:
            break
        clusters = [c for k, c in enumerate(clusters) if k not in merged_into]

    clusters.sort(
        key=lambda c: (
            int(c.representative.get("tier") or 9),
            -c.size,
            -(c.representative.get("published_epoch") or 0),
        )
    )
    return clusters

def row_to_dict(row) -> dict:
    """Convert an aiosqlite Row to the plain dict this module expects."""
    return {k: row[k] for k in row.keys()}
