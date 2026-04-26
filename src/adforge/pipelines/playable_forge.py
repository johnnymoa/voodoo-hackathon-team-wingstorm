"""playable_forge — gameplay video → tailored single-file HTML playable.

Steps:
  1. analyze_gameplay_video   — Gemini structured breakdown of the loop
  2. build_playable_html      — Claude Sonnet authors a tailored loop body for
                                 THIS game's mechanic (validation-gated, falls
                                 back to a deterministic CONFIG-injection
                                 baseline if the LLM output is malformed)
  3. inline_html_assets       — collapse external refs, verify size
  4. generate_variations      — emit N variants by overriding CONFIG
  5. finalize_run             — write manifest.json
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    from adforge.activities.project_intel import ProjectIntel, ProjectIntelInput
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
    project_id: str
    run_id: str
    run_dir: str
    config_id: str = "default"
    video_path: str
    project_dir: str | None = None       # for GDD reading
    base_filename: str = "playable.html"
    asset_dir: str | None = None
    market_patterns: dict[str, Any] | None = None
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
        started_at = workflow.now().isoformat(timespec="seconds")

        # Read the project's GDD/README in parallel-thinking with Gemini's video
        # analysis. The GDD tells Claude what the game IS in the designer's words
        # (rules, win/lose, audience); Gemini's video analysis tells Claude what
        # it LOOKS LIKE. Together: a much richer build prompt.
        intel: ProjectIntel | None = None
        if inp.project_dir:
            intel = await workflow.execute_activity(
                "analyze_project_docs",
                ProjectIntelInput(project_id=inp.project_id, project_dir=inp.project_dir),
                result_type=ProjectIntel,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY,
            )
            await workflow.execute_activity(
                "write_json",
                {"path": f"{inp.run_dir}/project_intel.json", "data": intel.model_dump()},
                start_to_close_timeout=timedelta(seconds=15),
            )

        analysis: GameAnalysis = await workflow.execute_activity(
            "analyze_gameplay_video",
            VideoAnalysisInput(video_path=inp.video_path),
            result_type=GameAnalysis,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        # Fold GDD intel into market_patterns so Claude sees it too — this is
        # the cheap path; long-term we should add a dedicated `intel` field on
        # PlayableBuildInput, but the prompt template already handles dicts.
        merged_patterns = dict(inp.market_patterns or {})
        if intel:
            merged_patterns["project_intel"] = intel.model_dump()

        base_path = f"{inp.run_dir}/{inp.base_filename}"
        base: PlayableBuildResult = await workflow.execute_activity(
            "build_playable_html",
            PlayableBuildInput(
                analysis=analysis,
                asset_dir=inp.asset_dir,
                market_patterns=merged_patterns or None,
                out_path=base_path,
                config_id=inp.config_id,
            ),
            result_type=PlayableBuildResult,
            start_to_close_timeout=timedelta(minutes=4),
            retry_policy=_RETRY,
        )

        if inp.asset_dir:
            base = await workflow.execute_activity(
                "inline_html_assets",
                base.html_path,
                result_type=PlayableBuildResult,
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
            result_type=VariationsResult,
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
            result_type=FinalizeRunResult,
            start_to_close_timeout=timedelta(seconds=15),
        )

        return PlayableForgeResult(
            run_id=inp.run_id,
            analysis=analysis,
            base_playable=base,
            variations=variations,
            manifest_path=finalized.manifest_path,
        )
