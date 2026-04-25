"""full_forge — Temporal workflow chaining creative_forge → playable_forge.

The merged pipeline. Single input → market intelligence + brief + Scenario poster
+ a market-informed playable HTML + market-hypothesis variants.

Layout on disk:

    runs/<full_run_id>/
      manifest.json              ← top-level, lists children
      creative/                  ← creative_forge child run, full creative_forge layout
        manifest.json
        brief.md
        ...
      playable/                  ← playable_forge child run, full playable_forge layout
        manifest.json
        playable.html
        ...

Use this when you want both pipelines bundled into one demo. For single-pipeline
runs, prefer playable_forge or creative_forge directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    from adforge.activities.types import VariationSpec
    from adforge.pipelines.creative_forge import CreativeForgeInput, CreativeForgeResult
    from adforge.pipelines.playable_forge import PlayableForgeInput, PlayableForgeResult


class FullForgeInput(BaseModel):
    target_id: str
    run_id: str
    run_dir: str
    target_term: str                      # display name / search term
    video_path: str
    asset_dir: str | None = None
    category: str | int = 7012
    country: str = "US"
    network: str = "TikTok"
    period: str = "month"
    sample: int = 30
    render_with_scenario_http: bool = False
    num_images: int = 3


class FullForgeResult(BaseModel):
    run_id: str
    creative: CreativeForgeResult
    playable: PlayableForgeResult
    manifest_path: str


def _hypothesis_variants(patterns_dump: dict) -> list[VariationSpec]:
    """Build market-informed variants — each one tests a different ranked hook."""
    cats = (patterns_dump or {}).get("categories", {})
    hooks = [r["value"] for r in (cats.get("hook") or [])[:3]]
    moods = [r["value"] for r in (cats.get("palette_mood") or [])[:2]]

    palettes = {
        "neon-pop":          ["#0b0b1a", "#ff2bd6", "#22e1ff", "#fff700", "#ff7849"],
        "saturated-cartoon": ["#1c2541", "#3a506b", "#5bc0be", "#ffce3a", "#f08a1c"],
        "muted-realistic":   ["#222222", "#444444", "#888888", "#cfcfcf", "#e8d8a0"],
        "high-contrast":     ["#000000", "#ffffff", "#ff2200", "#00ccff", "#ffd400"],
        "warm-cozy":         ["#3b2a1a", "#a4582d", "#e8b96b", "#fff4d6", "#d35a3a"],
        "dark-fantasy":      ["#0a0a14", "#2c1f3a", "#5b3a8c", "#b186ff", "#ffd166"],
    }

    variants: list[VariationSpec] = []
    for h in hooks or ["near-fail tease"]:
        variants.append(VariationSpec(
            name=f"hook-{h}",
            overrides={"spawnEverySeconds": 0.9, "winScore": 14},
            rationale=f"Tests the '{h}' hook (ranked top market signal).",
        ))
    for m in moods:
        variants.append(VariationSpec(
            name=f"mood-{m}",
            overrides={"palette": palettes.get(m, palettes["saturated-cartoon"])},
            rationale=f"Tests palette mood '{m}'.",
        ))
    if not variants:
        variants = [VariationSpec(name="default", overrides={}, rationale="fallback")]
    return variants


@workflow.defn(name="full_forge")
class FullForge:
    @workflow.run
    async def run(self, inp: FullForgeInput) -> FullForgeResult:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        creative_run_id = f"{inp.run_id}__creative"
        playable_run_id = f"{inp.run_id}__playable"

        creative: CreativeForgeResult = await workflow.execute_child_workflow(
            "creative_forge",
            CreativeForgeInput(
                target_id=inp.target_id,
                run_id=creative_run_id,
                run_dir=f"{inp.run_dir}/creative",
                target_term=inp.target_term,
                category=inp.category,
                country=inp.country,
                network=inp.network,
                period=inp.period,
                sample=inp.sample,
                render_with_scenario_http=inp.render_with_scenario_http,
                num_images=inp.num_images,
            ),
            id=creative_run_id,
            execution_timeout=timedelta(hours=1),
        )

        variants = _hypothesis_variants(creative.patterns.model_dump())

        playable: PlayableForgeResult = await workflow.execute_child_workflow(
            "playable_forge",
            PlayableForgeInput(
                target_id=inp.target_id,
                run_id=playable_run_id,
                run_dir=f"{inp.run_dir}/playable",
                video_path=inp.video_path,
                base_filename="playable.html",
                asset_dir=inp.asset_dir,
                market_patterns=creative.patterns.model_dump(),
                variants=variants,
            ),
            id=playable_run_id,
            execution_timeout=timedelta(hours=1),
        )

        finalized: FinalizeRunResult = await workflow.execute_activity(
            "finalize_run",
            FinalizeRunInput(
                run_dir=inp.run_dir,
                run_id=inp.run_id,
                pipeline="full_forge",
                target_id=inp.target_id,
                started_at=started_at,
                params=inp.model_dump(),
                artifact_globs=["**/*.html", "**/*.json", "**/*.md", "**/*.txt", "**/*.png"],
                children=[creative_run_id, playable_run_id],
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        return FullForgeResult(
            run_id=inp.run_id, creative=creative, playable=playable,
            manifest_path=finalized.manifest_path,
        )
