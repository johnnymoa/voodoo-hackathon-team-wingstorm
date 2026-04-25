"""playable_forge — Temporal workflow: gameplay video → playable HTML + variations.

Steps:
  1. analyze_gameplay_video   — Gemini structured breakdown of the loop
  2. (optional) market_patterns provided as input — bake winning hook/palette/CTA
  3. build_playable_html      — inject CONFIG into the template
  4. inline_html_assets       — collapse external refs, verify size
  5. generate_variations      — emit N variants by overriding CONFIG
  6. finalize_run             — write manifest.json

Input: PlayableForgeInput. Output: PlayableForgeResult.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
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
    project_id: str                       # for manifest provenance
    run_id: str
    run_dir: str                          # absolute path to runs/<run_id>/
    config_id: str = "default"            # which PipelineConfig preset to apply
    video_path: str
    base_filename: str = "playable.html"
    asset_dir: str | None = None
    market_patterns: dict[str, Any] | None = None    # from creative_forge (when chained)
    variants: list[VariationSpec] = []


class PlayableForgeResult(BaseModel):
    run_id: str
    analysis: GameAnalysis
    base_playable: PlayableBuildResult
    variations: VariationsResult
    manifest_path: str


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="playable_forge")
class PlayableForge:
    @workflow.run
    async def run(self, inp: PlayableForgeInput) -> PlayableForgeResult:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        analysis: GameAnalysis = await workflow.execute_activity(
            "analyze_gameplay_video",
            VideoAnalysisInput(video_path=inp.video_path),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        base_path = f"{inp.run_dir}/{inp.base_filename}"
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
                out_dir=inp.run_dir,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=_RETRY,
        )

        finalized: FinalizeRunResult = await workflow.execute_activity(
            "finalize_run",
            FinalizeRunInput(
                run_dir=inp.run_dir,
                run_id=inp.run_id,
                pipeline="playable_forge",
                project_id=inp.project_id,
                config_id=inp.config_id,
                started_at=started_at,
                params=inp.model_dump(exclude={"market_patterns"}),
                artifact_globs=["*.html", "*.json", "*.md"],
            ),
            start_to_close_timeout=timedelta(seconds=15),
        )

        return PlayableForgeResult(
            run_id=inp.run_id,
            analysis=analysis,
            base_playable=base,
            variations=variations,
            manifest_path=finalized.manifest_path,
        )
