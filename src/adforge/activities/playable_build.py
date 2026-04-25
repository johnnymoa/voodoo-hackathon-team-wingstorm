"""Activity: turn a GameAnalysis (+ optional market patterns) into a playable HTML.

Strategy:
  1. Start from `templates/playable_template.html`.
  2. Inject a CONFIG block derived from `analysis.configurable_parameters` and
     market `palette_mood` / `hook` cues if present.
  3. (Future) ask Claude to author the loop body. For the hackathon baseline we
     keep the template's tap-the-target loop and just retune CONFIG — Claude can
     replace the body in a follow-up activity once per game.

Returning the path lets the next activity (inline_assets / variations) run.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from temporalio import activity

from adforge.activities.types import PlayableBuildInput, PlayableBuildResult
from adforge.utils import file_size_mb

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "playable_template.html"
CONFIG_RE = re.compile(r"const\s+CONFIG\s*=\s*(\{.*?\})\s*;", re.S)


def _palette_for_mood(mood: str | None, fallback: list[str] | None) -> list[str]:
    if fallback:
        return fallback
    presets = {
        "neon-pop":          ["#0b0b1a", "#ff2bd6", "#22e1ff", "#fff700", "#ff7849"],
        "saturated-cartoon": ["#1c2541", "#3a506b", "#5bc0be", "#ffce3a", "#f08a1c"],
        "muted-realistic":   ["#222222", "#444444", "#888888", "#cfcfcf", "#e8d8a0"],
        "high-contrast":     ["#000000", "#ffffff", "#ff2200", "#00ccff", "#ffd400"],
        "warm-cozy":         ["#3b2a1a", "#a4582d", "#e8b96b", "#fff4d6", "#d35a3a"],
        "dark-fantasy":      ["#0a0a14", "#2c1f3a", "#5b3a8c", "#b186ff", "#ffd166"],
    }
    return presets.get((mood or "saturated-cartoon"), presets["saturated-cartoon"])


def _cta_for_framing(framing: str | None) -> str:
    return {
        "imperative-verb":      "Play Now",
        "question":             "Can you do it?",
        "challenge":            "Beat the level",
        "urgency":              "Play before it ends",
        "free-prize":           "Free — Tap to play",
        "social-proof":         "Join 10M players",
        "you-can't-do-this":    "Most fail — can you?",
    }.get(framing or "imperative-verb", "Install Now")


def _build_config(inp: PlayableBuildInput) -> dict:
    base = {
        "sessionSeconds": 30,
        "spawnEverySeconds": 1.2,
        "difficultyRamp": 1.05,
        "enemyCount": 12,
        "enemyHp": 1,
        "enemySpeed": 90,
        "playerDamage": 1,
        "tapRadius": 56,
        "winScore": 12,
        "failOnEscape": True,
        "palette": ["#1c2541", "#3a506b", "#5bc0be", "#ffce3a", "#f08a1c"],
        "showHintAfterMs": 1500,
        "ctaText": "Install Now",
        "showCtaAfterScore": 6,
        "showCtaAfterMs": 12000,
    }
    raw = inp.analysis.raw or {}
    for p in raw.get("configurable_parameters", []) or []:
        n, v = p.get("name"), p.get("default")
        if n in base and v is not None:
            base[n] = v
    if inp.analysis.palette:
        base["palette"] = inp.analysis.palette

    mp = inp.market_patterns or {}
    cats = mp.get("categories", {}) if isinstance(mp, dict) else {}

    def top(cat: str) -> str | None:
        ranked = cats.get(cat) or []
        return ranked[0]["value"] if ranked else None

    base["palette"] = _palette_for_mood(top("palette_mood"), inp.analysis.palette)
    base["ctaText"] = _cta_for_framing(top("cta_framing"))
    return base


@activity.defn(name="build_playable_html")
async def build_playable_html(inp: PlayableBuildInput) -> PlayableBuildResult:
    html = TEMPLATE.read_text(encoding="utf-8")
    cfg = _build_config(inp)
    new_block = "const CONFIG = " + json.dumps(cfg, indent=2) + ";"
    new_html = CONFIG_RE.sub(lambda _: new_block, html, count=1)

    out = Path(inp.out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new_html, encoding="utf-8")
    return PlayableBuildResult(html_path=str(out), size_mb=file_size_mb(out))
