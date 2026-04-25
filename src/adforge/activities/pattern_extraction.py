"""Activity: extract creative patterns from a SensorTower top_creatives payload.

Uses Mistral by default (cheap, fast for structured JSON over many short prompts).
Falls back to Gemini if MISTRAL_API_KEY is not set.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from temporalio import activity

from adforge.activities.types import PatternExtractionInput, Patterns
from adforge.config import settings
from adforge.connectors import gemini, mistral

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
    "If unsure, return 'unknown'. Output JSON only."
)

PROMPT_TPL = """Categories and allowed values:
{vocab}

Creative metadata:
{meta}

Return JSON: {{"hook": str, "opening_visual": str, "mechanic_shown": str, "cta_framing": str, "palette_mood": str}}
"""


def _flatten(payload: dict) -> list[dict]:
    rows = []
    for au in payload.get("ad_units", []):
        base = {
            "id": au.get("id"),
            "ad_type": au.get("ad_type"),
            "network": au.get("network"),
            "app_name": (au.get("app_info") or {}).get("name"),
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


def _label_one(meta: dict) -> dict[str, str]:
    prompt = PROMPT_TPL.format(
        vocab=json.dumps(LABEL_VOCAB, indent=2),
        meta=json.dumps(meta, indent=2),
    )
    s = settings()
    if s.mistral_api_key:
        return mistral.complete_json(prompt, system=SYSTEM)
    return gemini.text_json(SYSTEM + "\n\n" + prompt)


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
    metas = _flatten(inp.creatives)[: inp.sample]
    labels: list[dict[str, str]] = []
    for i, m in enumerate(metas):
        activity.heartbeat(f"label {i + 1}/{len(metas)}")
        try:
            labels.append(_label_one(m))
        except Exception as e:                       # one bad label shouldn't kill the run
            activity.logger.warning(f"label failed for {m.get('creative_id')}: {e}")
            labels.append({k: "unknown" for k in LABEL_VOCAB})
    return Patterns(
        creative_count=len(labels),
        categories=_summarize(labels, metas),
        per_creative=[{"meta": m, "labels": l} for m, l in zip(metas, labels)],
    )
