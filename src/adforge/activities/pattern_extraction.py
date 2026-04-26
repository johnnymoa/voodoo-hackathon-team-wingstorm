"""Activity: extract patterns from a SensorTower top_creatives payload.

Two parts:

1. **Working-creative ranker** — before sampling, reorder the flattened
   creatives so top-advertiser membership and longevity (last_seen − first_seen)
   bubble winning ad units to the front. We concentrate the labeling budget
   on creatives that are demonstrably surviving in market, not whatever order
   SensorTower happened to return.

2. **Claude Haiku labeler** — fast, cheap, accurate enough for 30-creative
   sweeps. Reads ANTHROPIC_API_KEY from .env.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from temporalio import activity

from adforge.activities.types import PatternExtractionInput, Patterns
from adforge.connectors import claude
from adforge.utils import strip_json_fences

LABEL_VOCAB: dict[str, list[str]] = {
    "hook": [
        "near-fail tease", "satisfying-completion", "fake-fail / wrong choice",
        "pull-to-aim", "puzzle-with-bad-solution", "before-after-transformation",
        "rage-bait", "asmr / sensory", "narrative-reveal", "humor-fail",
    ],
    "opening_visual": [
        "ui-isolated", "hero-character-closeup", "level-overview", "extreme-zoom",
        "split-screen", "text-overlay-question", "fail-state-first",
    ],
    "mechanic_shown": [
        "merge", "match-3", "physics-drop", "pull-pin", "tower-defense", "runner",
        "shoot-aim", "stack", "color-sort", "rope-cut", "draw-path", "tap-rhythm",
        "build-place", "conquer-territory",
    ],
    "cta_framing": [
        "imperative-verb", "question", "challenge", "social-proof", "urgency",
        "free-prize", "you-can't-do-this",
    ],
    "palette_mood": [
        "saturated-cartoon", "neon-pop", "muted-realistic", "high-contrast",
        "warm-cozy", "dark-fantasy",
    ],
}

SYSTEM = (
    "You label mobile-game ad creatives. Choose ONE label per category. "
    "If unsure, return 'unknown'. Output JSON only — no preamble, no fences."
)

PROMPT_TPL = """Categories and allowed values:
{vocab}

Creative metadata (this ad unit is from {app_name}, network={network}, ad_type={ad_type}, alive {days_alive} days):
{meta}

Return JSON: {{"hook": str, "opening_visual": str, "mechanic_shown": str, "cta_framing": str, "palette_mood": str}}
"""


# ── flatten ────────────────────────────────────────────────────────────
def _flatten(payload: dict) -> list[dict]:
    rows = []
    for au in payload.get("ad_units", []):
        base = {
            "id": au.get("id"),
            "ad_type": au.get("ad_type"),
            "network": au.get("network"),
            "app_name": (au.get("app_info") or {}).get("name"),
            "app_id": au.get("app_id"),
            "first_seen_at": au.get("first_seen_at"),
            "last_seen_at": au.get("last_seen_at"),
        }
        for cr in au.get("creatives", []) or []:
            row = dict(base)
            row.update({
                "creative_id": cr.get("id"),
                "thumb_url": cr.get("thumb_url"),
                "video_duration": cr.get("video_duration"),
                "message": cr.get("message"),
                "button_text": cr.get("button_text"),
            })
            rows.append(row)
    return rows


# ── working-creative ranker ────────────────────────────────────────────
def _top_advertiser_app_ids(top_advertisers: dict) -> set[str]:
    apps = (
        top_advertisers.get("apps")
        or top_advertisers.get("top_apps")
        or top_advertisers.get("publishers")
        or []
    )
    out: set[str] = set()
    for row in apps:
        for k in ("app_id", "entity_id", "id", "unified_app_id"):
            v = row.get(k)
            if v:
                out.add(str(v))
                break
    return out


def _days_alive(meta: dict) -> int:
    fs, ls = meta.get("first_seen_at"), meta.get("last_seen_at")
    if not fs:
        return 0
    try:
        first = datetime.fromisoformat(fs.replace("Z", "+00:00"))
        last = (
            datetime.fromisoformat(ls.replace("Z", "+00:00"))
            if ls
            else datetime.now(timezone.utc)
        )
        return max(0, (last - first).days)
    except Exception:
        return 0


def _rank_working(metas: list[dict], top_advertiser_ids: set[str]) -> list[dict]:
    """Sort by (top-advertiser, days alive, original order). Top first."""
    indexed = list(enumerate(metas))
    indexed.sort(
        key=lambda im: (
            -(1 if str(im[1].get("app_id") or "") in top_advertiser_ids else 0),
            -_days_alive(im[1]),
            im[0],
        )
    )
    return [m for _, m in indexed]


# ── Claude labeler ─────────────────────────────────────────────────────
def _label_with_claude(meta: dict) -> dict[str, str]:
    prompt = PROMPT_TPL.format(
        vocab=json.dumps(LABEL_VOCAB, indent=2),
        meta=json.dumps(meta, indent=2),
        app_name=meta.get("app_name") or "?",
        network=meta.get("network") or "?",
        ad_type=meta.get("ad_type") or "?",
        days_alive=_days_alive(meta),
    )
    raw = claude.complete(
        prompt,
        system=SYSTEM,
        model=claude.HAIKU,
        max_tokens=512,
        temperature=0.0,
    )
    return json.loads(strip_json_fences(raw))


# ── summary ────────────────────────────────────────────────────────────
def _summarize(labels: list[dict], metas: list[dict]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for cat in LABEL_VOCAB:
        c = Counter(l.get(cat, "unknown") for l in labels)
        ranked = []
        for value, count in c.most_common():
            if value == "unknown":
                continue
            evidence = [
                metas[i].get("creative_id") or metas[i].get("id")
                for i, l in enumerate(labels) if l.get(cat) == value
            ][:8]
            ranked.append({
                "value": value,
                "count": count,
                "share": round(count / max(1, len(labels)), 3),
                "evidence_ids": evidence,
            })
        out[cat] = ranked
    return out


@activity.defn(name="extract_patterns")
async def extract_patterns(inp: PatternExtractionInput) -> Patterns:
    metas = _flatten(inp.creatives)

    if inp.top_advertisers:
        top_ids = _top_advertiser_app_ids(inp.top_advertisers)
        before = sum(1 for m in metas if str(m.get("app_id") or "") in top_ids)
        metas = _rank_working(metas, top_ids)
        activity.logger.info(
            f"[ranker] {before}/{len(metas)} creatives belong to {len(top_ids)} top advertisers; reordered."
        )

    metas = metas[: inp.sample]

    labels: list[dict[str, str]] = []
    for i, m in enumerate(metas):
        activity.heartbeat(f"label {i + 1}/{len(metas)} (Claude Haiku)")
        try:
            labels.append(_label_with_claude(m))
        except Exception as e:
            activity.logger.warning(f"label failed for {m.get('creative_id')}: {e}")
            labels.append({k: "unknown" for k in LABEL_VOCAB})

    return Patterns(
        creative_count=len(labels),
        categories=_summarize(labels, metas),
        per_creative=[{"meta": m, "labels": l} for m, l in zip(metas, labels)],
    )
