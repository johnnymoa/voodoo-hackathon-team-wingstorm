"""creative_forge — Temporal workflow: target game → ad creative + brief.

Steps:
  1. resolve_target_game     — search SensorTower, get unified app ID
  2. fetch_market_data       — top advertisers + top creatives in the genre
  3. extract_patterns        — Mistral/Gemini labels each creative on a vocab
  4. write_brief_and_prompt  — markdown brief + Scenario-ready prompt
  5. (optional) render_scenario_creative — headless image gen via Scenario HTTP API
                              (skipped by default — preferred path is the Scenario MCP
                              inside Claude Code)

Input: CreativeForgeInput. Output: CreativeForgeResult.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
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
    target_term: str
    out_dir: str
    category: str | int = 7012
    country: str = "US"
    network: str = "TikTok"
    period: str = "month"
    sample: int = 30
    render_with_scenario_http: bool = False     # set True for full headless mode
    num_images: int = 3


class CreativeForgeResult(BaseModel):
    target: TargetGame
    patterns: Patterns
    brief: BriefResult
    images: ScenarioRenderResult | None = None


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="creative_forge")
class CreativeForge:
    @workflow.run
    async def run(self, inp: CreativeForgeInput) -> CreativeForgeResult:
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
            {"path": f"{inp.out_dir}/target.json",            "data": target.model_dump()},
            start_to_close_timeout=timedelta(seconds=15),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.out_dir}/top_advertisers.json",   "data": market.top_advertisers},
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.out_dir}/top_creatives.json",     "data": market.top_creatives},
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.out_dir}/patterns.json",          "data": patterns.model_dump()},
            start_to_close_timeout=timedelta(seconds=30),
        )

        brief: BriefResult = await workflow.execute_activity(
            "write_brief_and_prompt",
            BriefInput(target=target, patterns=patterns, out_dir=inp.out_dir),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY,
        )

        images: ScenarioRenderResult | None = None
        if inp.render_with_scenario_http:
            images = await workflow.execute_activity(
                "render_scenario_creative",
                ScenarioRenderInput(
                    prompt_path=brief.scenario_prompt_path,
                    out_dir=inp.out_dir,
                    num_images=inp.num_images,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY,
                heartbeat_timeout=timedelta(seconds=60),
            )

        return CreativeForgeResult(
            target=target, patterns=patterns, brief=brief, images=images,
        )
