"""
Export clustered stories for the web edition.

Kept separate from tools/build_web.py so the data step (needs the DB) and the
render step (needs only JSON) can run independently — handy when iterating on
the page design without re-reading the database.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import pathlib

from src import canonical, cluster, storage

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "web_edition.json"


async def build() -> dict:
    conn = await storage.connect()
    try:
        rows = await storage.get_unsent_items(
            conn, states=(storage.STATE_NEW, storage.STATE_HELD), limit=300)
        items = [cluster.row_to_dict(r) for r in rows]
    finally:
        await conn.close()

    stories = []
    for c in cluster.cluster_items(items):
        rep = c.representative
        # Prefer a real publisher URL over an aggregator wrapper for the headline
        # link, so the destination matches the outlet named beside it.
        best = min(c.members, key=lambda m: (
            1 if canonical.is_wrapper(m.get("url_canonical") or "") else 0,
            int(m.get("tier") or 9)))
        label = ("official" if int(rep.get("tier") or 9) == 1 and not rep.get("is_rumour")
                 else "rumour" if rep.get("is_rumour") else "report")
        sources, seen = [], set()
        for m in sorted(c.members, key=lambda m: int(m.get("tier") or 9)):
            dom = (m.get("source_domain") or "").casefold()
            if dom in seen:
                continue
            seen.add(dom)
            sources.append({
                "name": m.get("source_name") or dom or "unknown",
                "url": m.get("url_canonical") or "",
                "tier": int(m.get("tier") or 9),
                "wrapper": bool(canonical.is_wrapper(m.get("url_canonical") or "")),
            })
        stories.append({
            "title": rep.get("title") or "",
            "label": label,
            "size": c.size,
            "outlets": len(sources),
            "primary": best.get("url_canonical") or "",
            "primary_name": best.get("source_name") or best.get("source_domain") or "",
            "published": rep.get("published_epoch"),
            "sources": sources[:12],
        })

    # Rank by corroboration: the number of independent outlets is the most
    # useful signal a reader has, and it is what the page leads with.
    stories.sort(key=lambda s: (-s["outlets"], -s["size"]))
    payload = {
        "generated_local": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_items": len(items),
        "total_stories": len(stories),
        "stories": stories,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


if __name__ == "__main__":
    p = asyncio.run(build())
    print("wrote " + str(OUT) + ": " + str(p["total_stories"]) + " stories from "
          + str(p["total_items"]) + " items")
