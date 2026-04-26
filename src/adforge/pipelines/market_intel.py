"""market_intel — competitive analysis pipeline (no Gemini, no Veo).

Steps:
  1. extract_keyframes              local frame extraction (imageio)
  2. intel_gather_context           reads GDD/text + lists assets
  3. intel_infer_genre              Claude vision: frames + text → genre/subgenre
  4. fetch_market_data              SensorTower top advertisers + creatives
  5. intel_analyze_competitors      Claude: project vs market → analysis
  6. intel_write_storyboards        Claude: playable + video storyboards
  7. write_json + write text artefacts
  8. intel_render_slide_deck        single-file HTML deck
  9. finalize_run

Input: MarketIntelInput. Output: MarketIntelResult.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    from adforge.activities.intel import (
        AnalyzeInput,
        CompetitiveAnalysis,
        GatherContextInput,
        GenreResult,
        ProjectContext,
        SlideDeckInput,
        SlideDeckResult,
        Storyboards,
        StoryboardsInput,
    )
    from adforge.activities.keyframes import KeyframeInput, KeyframeResult
    from adforge.activities.types import MarketData, MarketDataInput


class MarketIntelInput(BaseModel):
    project_id: str
    run_id: str
    run_dir: str
    config_id: str = "default"
    video_path: str | None = None
    network: str = "TikTok"
    period: str = "month"
    sample_creatives: int = 50
    num_keyframes: int = 8


class MarketIntelResult(BaseModel):
    run_id: str
    deck_path: str
    manifest_path: str


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=3)


@workflow.defn(name="market_intel")
class MarketIntel:
    @workflow.run
    async def run(self, inp: MarketIntelInput) -> MarketIntelResult:
        started_at = workflow.now().isoformat(timespec="seconds")

        keyframes: KeyframeResult = await workflow.execute_activity(
            "extract_keyframes",
            KeyframeInput(
                video_path=inp.video_path,
                out_dir=inp.run_dir,
                num_frames=inp.num_keyframes,
            ),
            result_type=KeyframeResult,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=_RETRY,
        )

        context: ProjectContext = await workflow.execute_activity(
            "intel_gather_context",
            GatherContextInput(project_id=inp.project_id, frame_paths=keyframes.frame_paths),
            result_type=ProjectContext,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY,
        )

        genre: GenreResult = await workflow.execute_activity(
            "intel_infer_genre",
            context,
            result_type=GenreResult,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=_RETRY,
        )

        market: MarketData = await workflow.execute_activity(
            "fetch_market_data",
            MarketDataInput(
                category=genre.category_id,
                country=context.country,
                network=inp.network,
                period=inp.period,
                limit=inp.sample_creatives,
            ),
            result_type=MarketData,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        analysis: CompetitiveAnalysis = await workflow.execute_activity(
            "intel_analyze_competitors",
            AnalyzeInput(
                config_id=inp.config_id,
                context=context,
                genre=genre,
                market={
                    "top_advertisers": market.top_advertisers,
                    "top_creatives": market.top_creatives,
                },
            ),
            result_type=CompetitiveAnalysis,
            start_to_close_timeout=timedelta(minutes=6),
            retry_policy=_RETRY,
        )

        storyboards: Storyboards = await workflow.execute_activity(
            "intel_write_storyboards",
            StoryboardsInput(
                config_id=inp.config_id,
                context=context,
                genre=genre,
                analysis=analysis,
            ),
            result_type=Storyboards,
            start_to_close_timeout=timedelta(minutes=6),
            retry_policy=_RETRY,
        )

        # Persist text artefacts so a human can read them outside the deck
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/genre.json", "data": genre.model_dump()},
            start_to_close_timeout=timedelta(seconds=15),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/analysis.json", "data": analysis.model_dump()},
            start_to_close_timeout=timedelta(seconds=15),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/top_advertisers.json", "data": market.top_advertisers},
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/top_creatives.json", "data": market.top_creatives},
            start_to_close_timeout=timedelta(seconds=30),
        )

        deck: SlideDeckResult = await workflow.execute_activity(
            "intel_render_slide_deck",
            SlideDeckInput(
                config_id=inp.config_id,
                context=context,
                genre=genre,
                analysis=analysis,
                storyboards=storyboards,
                out_path=f"{inp.run_dir}/deck.html",
            ),
            result_type=SlideDeckResult,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
        )

        finalized: FinalizeRunResult = await workflow.execute_activity(
            "finalize_run",
            FinalizeRunInput(
                run_dir=inp.run_dir,
                run_id=inp.run_id,
                pipeline="market_intel",
                project_id=inp.project_id,
                config_id=inp.config_id,
                started_at=started_at,
                params=inp.model_dump(),
                artifact_globs=["*.html", "*.json", "*.md", "frames/*.png"],
            ),
            result_type=FinalizeRunResult,
            start_to_close_timeout=timedelta(seconds=15),
        )

        return MarketIntelResult(
            run_id=inp.run_id,
            deck_path=deck.html_path,
            manifest_path=finalized.manifest_path,
        )
