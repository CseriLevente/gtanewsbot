"""
Discord message rendering.

Hard limits enforced here (a 400 from Discord rejects the ENTIRE message with no
truncation, so the budget is checked before sending, not hoped for):

    embed title            256
    embed description     4096
    embed footer text     2048
    embed author name      256
    fields per embed        25
    embeds per message      10
    TOTAL chars across all embeds in one message   6000   <-- the real ceiling

Per-field limits are generous, so 6000-total is what actually bites. The design
response is ONE embed containing many masked-link lines rather than one embed per
story: ten embeds of a mere 656 chars each already breaches the total.

Note: the message content limit is documented as 2000 for the webhook route and
rendered as 4000 on the Create Message page; the research could not resolve that
conflict, so 2000 is used.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src import credibility
from src.clock import describe_now

logger = logging.getLogger(__name__)

EMBED_TITLE_MAX = 256
EMBED_DESC_MAX = 4096
EMBED_FOOTER_MAX = 2048
EMBED_AUTHOR_MAX = 256
EMBED_TOTAL_MAX = 6000
CONTENT_MAX = 2000

# Leave headroom so a footer or author change can never tip us over.
_TOTAL_BUDGET = EMBED_TOTAL_MAX - 200

# Characters held back for the "+N more items not shown" disclosure line.
_OMISSION_NOTE_RESERVE = 48

COLOUR_OFFICIAL = 0x2ECC71   # green
COLOUR_REPORT = 0x3498DB     # blue
COLOUR_RUMOUR = 0xE67E22     # orange
COLOUR_EMPTY = 0x95A5A6      # grey

_LABEL_PREFIX = {
    credibility.LABEL_OFFICIAL: "🟢 **Official**",
    credibility.LABEL_REPORT: "🔵 **Report**",
    credibility.LABEL_RUMOUR: "🟠 **Rumour**",
}


@dataclass
class DigestEntry:
    """One rendered line of the digest — one STORY, not one article."""
    item_id: int
    title: str
    url: str
    source_name: str
    label: str
    summary: str | None = None
    # Other outlets that reported the same story. Displayed so a reader can see
    # a story is widely corroborated without it consuming extra digest slots.
    other_outlets: list[str] = field(default_factory=list)
    # Every item id in the cluster. All are marked sent, not just the one
    # linked, otherwise the unused copies resurface tomorrow as "new" stories.
    member_ids: list[int] = field(default_factory=list)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


_URL_RUN_RE = __import__("re").compile(r"https?://\S+", __import__("re").IGNORECASE)


def _escape_markdown_link_text(text: str) -> str:
    """
    Make a headline safe inside a masked link [text](url).

    Unbalanced brackets in a headline break the link and can leak a raw URL into
    the rendered text.
    """
    return text.replace("[", "(").replace("]", ")")


def sanitise_attribution(text: str) -> str:
    """
    Make a publisher name safe to interpolate into a markdown line.

    Attribution strings come from feed metadata — `<source><title>` or the feed's
    own channel title — which nothing validates. Interpolated raw next to a
    masked link, a crafted value like `x](https://evil.example)` closes our link
    early and opens an attacker-controlled one. That turns an unvalidated text
    field into a clickable destination, which is precisely the outcome the
    describe-never-link rule exists to prevent, and it lands on the
    instant-alert line a reader is most likely to click.

    Breaking out requires the two-character sequence `](`, so neutralising the
    square brackets is sufficient — plus stripping embedded URLs, since a
    publisher name never legitimately contains one.

    Parentheses are deliberately LEFT ALONE. An earlier version replaced them
    with lookalike glyphs, which mangled every legitimate name that contains
    them — "Rockstar Games (YouTube)" rendered as "Rockstar Games ❨YouTube❩" on
    each instant alert. A bare paren cannot terminate link text, so escaping it
    was damage for no benefit.
    """
    if not text:
        return ""
    out = _URL_RUN_RE.sub("", text)
    out = out.replace("[", "(").replace("]", ")")
    return " ".join(out.split()).strip(" ·-|")



def _show_omitted_count() -> bool:
    import os
    return (os.environ.get("DIGEST_SHOW_OMITTED_COUNT") or "").strip().casefold() in (
        "1", "true", "yes", "on")


def _web_url() -> str | None:
    """The published web edition, if one is configured."""
    import os
    return (os.environ.get("DIGEST_WEB_URL") or "").strip() or None

def _entry_line(entry: DigestEntry) -> str:
    prefix = _LABEL_PREFIX.get(entry.label, "🔵 **Report**")
    title = _escape_markdown_link_text(_truncate(entry.title, 200))
    line = f"{prefix} · [{title}]({entry.url})"
    attribution = sanitise_attribution(entry.source_name)
    if entry.other_outlets:
        shown = [sanitise_attribution(o) for o in entry.other_outlets[:3]]
        more = len(entry.other_outlets) - len(shown)
        also = ", ".join(shown) + (f" +{more}" if more > 0 else "")
        attribution += f" · also {also}"
    line += f"\n-# {attribution}"
    if entry.summary:
        line += f"\n{_truncate(entry.summary, 300)}"
    return line


def select_entries(
    entries: list[DigestEntry],
    *,
    health_line: str,
    date_label: str,
    max_items: int = 8,
) -> tuple[list[DigestEntry], int]:
    """
    Decide which entries actually fit in one message.

    Returns (rendered, omitted_count). Exists as a separate function so the
    CALLER can know exactly which entries were published.

    Why that matters: the caller marks published items as sent_digest, and
    sent_digest is terminal. Previously it marked `entries[:max_items]` while
    render_digest silently dropped the tail that would not fit the 6000-char
    budget — so a real story was marked published, never shown to anyone, and
    could never be selected again. Deriving both the payload and the marking
    list from this one function makes that class of divergence impossible.
    """
    chosen = entries[:max_items]
    omitted_by_cap = max(0, len(entries) - len(chosen))

    title = _truncate(f"GTA 6 — Daily News Digest · {date_label}", EMBED_TITLE_MAX)
    footer = _truncate(f"{health_line} · {describe_now()}", EMBED_FOOTER_MAX)
    fixed_cost = len(title) + len(footer)

    rendered: list[DigestEntry] = []
    used = 0
    for entry in chosen:
        cost = len(_entry_line(entry)) + 2
        if (used + cost + _OMISSION_NOTE_RESERVE > EMBED_DESC_MAX
                or fixed_cost + used + cost + _OMISSION_NOTE_RESERVE > _TOTAL_BUDGET):
            continue
        rendered.append(entry)
        used += cost

    return rendered, omitted_by_cap + (len(chosen) - len(rendered))


def render_digest(
    entries: list[DigestEntry],
    *,
    health_line: str,
    date_label: str,
    max_items: int = 8,
) -> dict:
    """
    Build the daily digest message payload.

    Returns a dict ready to POST. Guaranteed to satisfy every Discord limit —
    entries that do not fit are dropped from the tail and the count is disclosed
    in the body rather than silently swallowed. Use select_entries() to learn
    which ones were actually included.
    """
    title = _truncate(f"GTA 6 — Daily News Digest · {date_label}", EMBED_TITLE_MAX)
    footer = _truncate(f"{health_line} · {describe_now()}", EMBED_FOOTER_MAX)
    chosen = entries[:max_items]

    if not chosen:
        # An empty digest still posts, and still carries the health line. That is
        # the whole point: "no news today" and "the bot is dead" must look
        # different to a reader.
        desc = (
            "No items cleared the credibility filter today.\n\n"
            "-# This is a normal outcome on a quiet day. The feed health line "
            "below shows whether the sources were actually reachable."
        )
        return {
            "embeds": [{
                "title": title,
                "description": desc,
                "color": COLOUR_EMPTY,
                "footer": {"text": footer},
            }],
            "allowed_mentions": {"parse": [], "roles": [], "users": [], "replied_user": False},
        }

    # Space for the "+N more" note is RESERVED up front by select_entries rather
    # than checked afterwards. If it were checked afterwards, a digest that
    # exactly fills the budget would have no room left for the note and would
    # silently swallow the omissions — which reads to a user as "that was
    # everything today". Honest disclosure outranks squeezing in one more entry.
    rendered, omitted = select_entries(
        entries, health_line=health_line, date_label=date_label, max_items=max_items
    )
    lines = [_entry_line(e) for e in rendered]
    # The "+N more not shown" count is deliberately NOT rendered any more.
    #
    # It was honest but useless: after clustering the overflow is dozens of
    # lower-ranked stories, and "+82 more" tells a reader nothing they can act
    # on. Nothing is actually lost — unrendered entries are never marked sent,
    # so they compete again tomorrow, and the web edition carries the full list.
    # Set DIGEST_SHOW_OMITTED_COUNT=true to bring the line back.
    if omitted and _show_omitted_count():
        lines.append(f"-# +{omitted} more item{'s' if omitted != 1 else ''} not shown")

    # A link to the full edition, which is what makes hiding the omitted count
    # honest: the reader can see everything, it just is not in the embed.
    web = _web_url()
    if web:
        # Deliberately no count. The embed's candidate list and the web edition
        # are built from different sets — the page also carries stories still
        # awaiting corroboration — so any number printed here would disagree
        # with what the reader finds when they click.
        lines.append(f"-# [Every story, on the web]({web})")

    has_rumour = any(e.label == credibility.LABEL_RUMOUR for e in chosen)
    has_official = any(e.label == credibility.LABEL_OFFICIAL for e in chosen)
    colour = COLOUR_OFFICIAL if has_official else (COLOUR_RUMOUR if has_rumour else COLOUR_REPORT)

    description = _truncate("\n\n".join(lines), EMBED_DESC_MAX)

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": colour,
            "footer": {"text": footer},
        }],
        # Digest never pings. Only instant alerts do.
        "allowed_mentions": {"parse": [], "roles": [], "users": [], "replied_user": False},
    }
    assert_within_limits(payload)
    return payload


def render_instant_alert(
    entry: DigestEntry, *, role_id: str | None, health_line: str | None = None
) -> dict:
    """
    Build a first-party instant alert.

    This is the ONLY message type that may mention a role, and it may mention
    exactly one: the opt-in notification role.
    """
    title = _truncate(entry.title, EMBED_TITLE_MAX)
    safe_source = sanitise_attribution(entry.source_name)
    desc_parts = [f"[Read on {safe_source}]({entry.url})"]
    if entry.summary:
        desc_parts.insert(0, _truncate(entry.summary, 600))
    embed = {
        "title": title,
        "description": "\n\n".join(desc_parts),
        "color": COLOUR_OFFICIAL if entry.label == credibility.LABEL_OFFICIAL else COLOUR_REPORT,
        "author": {"name": _truncate(f"{entry.label} · {safe_source}", EMBED_AUTHOR_MAX)},
    }
    if health_line:
        embed["footer"] = {"text": _truncate(health_line, EMBED_FOOTER_MAX)}

    content = f"<@&{role_id}>" if role_id else None
    payload: dict = {"embeds": [embed]}
    if content:
        payload["content"] = _truncate(content, CONTENT_MAX)

    payload["allowed_mentions"] = {
        "parse": [],
        "roles": [role_id] if role_id else [],
        "users": [],
        "replied_user": False,
    }
    assert_within_limits(payload)
    return payload


# Prefixes the embed author line of every breakout alert. The channel-side rate
# limit counts messages by this string, so it must stay stable: changing it
# makes older alerts uncountable and briefly lifts the cap.
BREAKOUT_MARKER = "Breaking ·"

_BREAKOUT_COLOUR: dict[str, int] = {
    credibility.LABEL_OFFICIAL: COLOUR_OFFICIAL,
    credibility.LABEL_REPORT: COLOUR_REPORT,
    credibility.LABEL_RUMOUR: COLOUR_RUMOUR,
}


def render_breakout_alert(
    entry: DigestEntry, *, role_id: str | None, outlet_count: int,
    health_line: str | None = None,
) -> dict:
    """
    Build a breakout alert: one story that many outlets ran at once.

    Distinct from an instant alert, which is reserved for first-party news. A
    breakout has no first-party source by definition -- if it had one it would
    already have been alerted -- so its warrant is corroboration: when this many
    independent outlets carry the same GTA 6 story within hours, something
    actually happened.

    Two consequences for the rendering:

      * the outlet count IS the evidence, so it leads, both in the author line
        (where BREAKOUT_MARKER makes the message countable for the channel-side
        rate limit) and as a listed set of names the reader can check;
      * a breakout can be sourced from leaked material, unlike an instant alert.
        The label therefore opens the description rather than sitting in the
        author line, so nobody can read the headline and miss that it is a
        rumour. Per the owner's rule we describe what the reporting claims and
        link the journalism, never the leaked material.
    """
    title = _truncate(entry.title, EMBED_TITLE_MAX)
    safe_source = sanitise_attribution(entry.source_name)
    prefix = _LABEL_PREFIX.get(entry.label, f"**{entry.label}**")

    desc_parts = [f"{prefix} · reported by **{outlet_count}** outlets"]
    if entry.summary:
        desc_parts.append(_truncate(entry.summary, 500))
    desc_parts.append(f"[Read on {safe_source}]({entry.url})")
    if entry.other_outlets:
        names = ", ".join(sanitise_attribution(o) for o in entry.other_outlets[:8])
        more = len(entry.other_outlets) - 8
        if more > 0:
            names += f" +{more}"
        desc_parts.append(f"-# Also: {names}")

    embed = {
        "title": title,
        "description": _truncate("\n\n".join(desc_parts), EMBED_DESC_MAX),
        "color": _BREAKOUT_COLOUR.get(entry.label, COLOUR_REPORT),
        "author": {"name": _truncate(
            f"{BREAKOUT_MARKER} {outlet_count} outlets · {safe_source}",
            EMBED_AUTHOR_MAX)},
    }
    if health_line:
        embed["footer"] = {"text": _truncate(health_line, EMBED_FOOTER_MAX)}

    payload: dict = {"embeds": [embed]}
    if role_id:
        payload["content"] = _truncate(f"<@&{role_id}>", CONTENT_MAX)
    payload["allowed_mentions"] = {
        "parse": [],
        "roles": [role_id] if role_id else [],
        "users": [],
        "replied_user": False,
    }
    assert_within_limits(payload)
    return payload


def embed_total_chars(payload: dict) -> int:
    """Sum every counted character across all embeds, as Discord does."""
    total = 0
    for e in payload.get("embeds", []):
        total += len(e.get("title", "") or "")
        total += len(e.get("description", "") or "")
        total += len((e.get("footer", {}) or {}).get("text", "") or "")
        total += len((e.get("author", {}) or {}).get("name", "") or "")
        for f in e.get("fields", []) or []:
            total += len(f.get("name", "") or "") + len(f.get("value", "") or "")
    return total


def assert_within_limits(payload: dict) -> None:
    """
    Fail loudly in-process rather than letting Discord 400 the whole message.

    Called on every payload before it is sent.
    """
    embeds = payload.get("embeds", [])
    if len(embeds) > 10:
        raise ValueError(f"too many embeds: {len(embeds)} > 10")
    for i, e in enumerate(embeds):
        if len(e.get("title", "") or "") > EMBED_TITLE_MAX:
            raise ValueError(f"embed[{i}].title exceeds {EMBED_TITLE_MAX}")
        if len(e.get("description", "") or "") > EMBED_DESC_MAX:
            raise ValueError(f"embed[{i}].description exceeds {EMBED_DESC_MAX}")
        if len((e.get("footer", {}) or {}).get("text", "") or "") > EMBED_FOOTER_MAX:
            raise ValueError(f"embed[{i}].footer.text exceeds {EMBED_FOOTER_MAX}")
        if len(e.get("fields", []) or []) > 25:
            raise ValueError(f"embed[{i}] has more than 25 fields")
    total = embed_total_chars(payload)
    if total > EMBED_TOTAL_MAX:
        raise ValueError(f"total embed characters {total} exceeds {EMBED_TOTAL_MAX}")
    if len(payload.get("content", "") or "") > CONTENT_MAX:
        raise ValueError(f"content exceeds {CONTENT_MAX}")

    # The @everyone guard. Bot messages (unlike webhooks) default to parsing
    # EVERYTHING including @everyone, so an unset allowed_mentions is a latent
    # mass-ping. Every payload must carry an explicit block.
    am = payload.get("allowed_mentions")
    if am is None:
        raise ValueError("allowed_mentions missing — bot messages default to parsing @everyone")
    if am.get("parse") != []:
        raise ValueError(f"allowed_mentions.parse must be [], got {am.get('parse')!r}")


def entry_from_row(row, *, label_override: str | None = None) -> DigestEntry:
    """Build a DigestEntry from an `items` row."""
    label = label_override
    if label is None:
        if row["is_rumour"]:
            label = credibility.LABEL_RUMOUR
        elif int(row["tier"]) == 1:
            label = credibility.LABEL_OFFICIAL
        else:
            label = credibility.LABEL_REPORT
    return DigestEntry(
        item_id=int(row["id"]),
        title=row["title"],
        url=row["url_canonical"],
        source_name=row["source_name"] or row["source_domain"] or "unknown",
        label=label,
        summary=None,  # milestone 2: LLM summary goes here
    )
