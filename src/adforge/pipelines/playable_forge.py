"""playable_forge — Temporal workflow: gameplay video → playable HTML + variations.

Steps:
  1. analyze_gameplay_video   — Gemini structured breakdown of the loop
  2. (optional) market_patterns provided as input — bake winning hook/palette/CTA
  3. build_playable_html      — inject CONFIG into the template
  4. inline_html_assets       — collapse external refs, verify size
  5. generate_variations      — emit N variants by overriding CONFIG

Input: PlayableForgeInput. Output: PlayableForgeResult.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.types import (
        GameAnalysis,
        PlayableBuildInput,
        PlayableBuildResult,
        VariationsInput,
        VariationsResult,
        VariationSpec,
        VideoAnalysisInput,
    )


class PlayableForgeInput(BaseModel):
    video_path: str
    out_dir: str                          # e.g. output/playables/<run_id>/
    base_filename: str = "playable.html"
    asset_dir: str | None = None
    market_patterns: dict[str, Any] | None = None    # from creative_forge
    variants: list[VariationSpec] = []


class PlayableForgeResult(BaseModel):
    analysis: GameAnalysis
    base_playable: PlayableBuildResult
    variations: VariationsResult


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="playable_forge")
class PlayableForge:
    @workflow.run
    async def run(self, inp: PlayableForgeInput) -> PlayableForgeResult:
        analysis: GameAnalysis = await workflow.execute_activity(
            "analyze_gameplay_video",
            VideoAnalysisInput(video_path=inp.video_path),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        base_path = f"{inp.out_dir}/{inp.base_filename}"
        base: PlayableBuildResult = await workflow.execute_activity(
            "build_playable_html",
            PlayableBuildInput(
                analysis=analysis,
                asset_dir=inp.asset_dir,
                market_patterns=inp.market_patterns,
                out_path=base_path,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
        )

        if inp.asset_dir:
            base = await workflow.execute_activity(
                "inline_html_assets",
                base.html_path,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY,
            )

        variations: VariationsResult = await workflow.execute_activity(
            "generate_variations",
            VariationsInput(
                base_html_path=base.html_path,
                variants=inp.variants,
                out_dir=inp.out_dir,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=_RETRY,
        )

        return PlayableForgeResult(
            analysis=analysis, base_playable=base, variations=variations
        )
