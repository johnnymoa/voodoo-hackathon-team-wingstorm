"""creative_forge — the video-ad pipeline.

Project (game) in. Video creative out. Steps today (will evolve as we iterate
under different configs — see PIPELINES registry):

  1. resolve_target_game     — search SensorTower for the unified app id
  2. fetch_market_data       — top advertisers + top creatives in the genre
  3. extract_patterns        — Mistral/Gemini labels each creative on a vocab
  4. write_brief_and_prompt  — markdown brief + Scenario-ready prompt
  5. (optional) render_scenario_creative — headless image via Scenario HTTP API
  6. finalize_run            — write manifest.json

Future iterations (per config preset): swap labelers/brief writers, add a web
research step, generate storyboards, swap in a video model. The activities are
the unit of swap; the workflow stays simple.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    from adforge.activities.types import (
        BriefInput,
        BriefResult,
        MarketData,
        MarketDataInput,
        Patterns,
        PatternExtractionInput,
        ScenarioRenderInput,
        ScenarioRenderResult,
        TargetGame,
        TargetGameInput,
    )


class CreativeForgeInput(BaseModel):
    project_id: str                      # for manifest provenance
    run_id: str
    run_dir: str                         # absolute path to runs/<run_id>/
    target_term: str                     # display name / search term, e.g. "Castle Clashers"
    config_id: str = "default"           # which PipelineConfig preset to apply
    category: str | int = 7012
    country: str = "US"
    network: str = "TikTok"
    period: str = "month"
    sample: int = 30
    render_with_scenario_http: bool = False     # set True for full headless mode
    num_images: int = 3


class CreativeForgeResult(BaseModel):
    run_id: str
    target: TargetGame
    patterns: Patterns
    brief: BriefResult
    images: ScenarioRenderResult | None = None
    manifest_path: str


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="creative_forge")
class CreativeForge:
    @workflow.run
    async def run(self, inp: CreativeForgeInput) -> CreativeForgeResult:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        target: TargetGame = await workflow.execute_activity(
            "resolve_target_game",
            TargetGameInput(term=inp.target_term),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY,
        )

        market: MarketData = await workflow.execute_activity(
            "fetch_market_data",
            MarketDataInput(
                category=inp.category, country=inp.country,
                network=inp.network, period=inp.period,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        patterns: Patterns = await workflow.execute_activity(
            "extract_patterns",
            PatternExtractionInput(creatives=market.top_creatives, sample=inp.sample),
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=60),
        )

        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/target.json",            "data": target.model_dump()},
            start_to_close_timeout=timedelta(seconds=15),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/top_advertisers.json",   "data": market.top_advertisers},
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/top_creatives.json",     "data": market.top_creatives},
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/patterns.json",          "data": patterns.model_dump()},
            start_to_close_timeout=timedelta(seconds=30),
        )

        brief: BriefResult = await workflow.execute_activity(
            "write_brief_and_prompt",
            BriefInput(target=target, patterns=patterns, out_dir=inp.run_dir),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY,
        )

        images: ScenarioRenderResult | None = None
        if inp.render_with_scenario_http:
            images = await workflow.execute_activity(
                "render_scenario_creative",
                ScenarioRenderInput(
                    prompt_path=brief.scenario_prompt_path,
                    out_dir=inp.run_dir,
                    num_images=inp.num_images,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY,
                heartbeat_timeout=timedelta(seconds=60),
            )

        finalized: FinalizeRunResult = await workflow.execute_activity(
            "finalize_run",
            FinalizeRunInput(
                run_dir=inp.run_dir,
                run_id=inp.run_id,
                pipeline="creative_forge",
                project_id=inp.project_id,
                config_id=inp.config_id,
                started_at=started_at,
                params=inp.model_dump(),
                artifact_globs=["*.json", "*.md", "*.txt", "*.png", "*.jpg"],
            ),
            start_to_close_timeout=timedelta(seconds=15),
        )

        return CreativeForgeResult(
            run_id=inp.run_id, target=target, patterns=patterns,
            brief=brief, images=images, manifest_path=finalized.manifest_path,
        )
