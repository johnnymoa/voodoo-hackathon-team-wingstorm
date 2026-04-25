"""Activities: write a creative brief and a Scenario-ready prompt."""

from __future__ import annotations

import time
from pathlib import Path

from temporalio import activity

from adforge.activities.types import BriefInput, BriefResult


def _top(cats: dict, name: str, n: int = 3) -> list[str]:
    return [f"{r['value']} ({int(r['share']*100)}%)" for r in (cats.get(name) or [])[:n]]


def _first(cats: dict, name: str, default: str) -> str:
    rows = cats.get(name) or []
    return rows[0]["value"] if rows else default


@activity.defn(name="write_brief_and_prompt")
async def write_brief_and_prompt(inp: BriefInput) -> BriefResult:
    out = Path(inp.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cats = inp.patterns.categories

    brief = f"""# Creative brief — {inp.target.name}

**App ID**: {inp.target.app_id}
**Publisher**: {inp.target.publisher_name or "(unknown)"}

## Market signals (last period)

- **Hooks**: {", ".join(_top(cats, "hook")) or "—"}
- **Opening visuals**: {", ".join(_top(cats, "opening_visual")) or "—"}
- **Mechanics shown**: {", ".join(_top(cats, "mechanic_shown")) or "—"}
- **CTA framings**: {", ".join(_top(cats, "cta_framing")) or "—"}
- **Palette mood**: {", ".join(_top(cats, "palette_mood")) or "—"}

Based on {inp.patterns.creative_count} creatives sampled from top performers.

## Recommended concept

A {_first(cats, "opening_visual", "level-overview")} opener using a
{_first(cats, "hook", "near-fail tease")} hook around the
{_first(cats, "mechanic_shown", "core")} mechanic, ending on a
{_first(cats, "cta_framing", "imperative-verb")} CTA in a
{_first(cats, "palette_mood", "saturated-cartoon")} palette.

## Storyboard

1. **Hook (0–2s)**: most compelling visual; pose the question.
2. **Tease (2–6s)**: near-fail / wrong attempt; bait curiosity.
3. **Pay-off + CTA (6–10s)**: deliver the satisfying resolution; tap-to-install.

— generated {time.strftime("%Y-%m-%d %H:%M")}
"""
    brief_p = out / "brief.md"
    brief_p.write_text(brief)

    prompt = f"""Mobile game ad creative for "{inp.target.name}".

Style: {_first(cats, "palette_mood", "saturated-cartoon")}, vibrant, 9:16 vertical,
hero center-frame, bold readable type.

Scene: {_first(cats, "opening_visual", "level-overview")} framing the
{_first(cats, "mechanic_shown", "core")} mechanic with a
{_first(cats, "hook", "near-fail tease")} hook. Visible UI hint inviting a tap.

Mood: high-contrast, saturated, instantly readable on a phone at thumbnail size.
Overlay: a single short question or CTA, max 6 words.
CTA framing: {_first(cats, "cta_framing", "imperative-verb")}.

Constraints: no copyrighted logos, no real people, no text smaller than 24px. 9:16.
"""
    prompt_p = out / "scenario_prompt.txt"
    prompt_p.write_text(prompt)

    activity.logger.info(f"brief → {brief_p}")
    return BriefResult(brief_path=str(brief_p), scenario_prompt_path=str(prompt_p))
