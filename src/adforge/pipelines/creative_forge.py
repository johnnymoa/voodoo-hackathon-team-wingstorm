"""creative_forge — the video-ad pipeline.

Steps:
  1. resolve_target_game     — search SensorTower for the unified app id
  2. fetch_market_data       — top advertisers + top creatives in the genre
  3. analyze_gameplay_video  — (only if project has a video) Gemini structured
                                breakdown of the actual game, compressed +
                                cached so re-runs are free
  4. extract_patterns        — Claude Haiku labels a working-creative-ranked
                                sample (top advertisers × longevity)
  5. write_brief_and_prompt  — markdown brief tying market patterns +
                                gameplay analysis + available assets +
                                video-ad-design rubric (hook, beat map, tone,
                                end-card) → defending rationale included
  6. render_seedance         — Scenario Seedance 2.0 (9:16 / 720p / 6s, audio)
  7. finalize_run            — write manifest.json
"""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    from adforge.activities.project_intel import ProjectIntel, ProjectIntelInput
    from adforge.activities.types import (
        BriefInput,
        BriefResult,
        GameAnalysis,
        MarketData,
        MarketDataInput,
        Patterns,
        PatternExtractionInput,
        ScenarioRenderInput,
        ScenarioRenderResult,
        TargetGame,
        TargetGameInput,
        VideoAnalysisInput,
    )


class CreativeForgeInput(BaseModel):
    project_id: str
    run_id: str
    run_dir: str
    project_dir: str | None = None       # to read GDDs from
    target_term: str
    config_id: str = "default"
    category: str | int = 7012           # FALLBACK ONLY — overridden by GDD+SensorTower lookup
    country: str = "US"
    network: str = "TikTok"
    period: str = "month"
    sample: int = 30
    seedance_model_id: str = "model_bytedance-seedance-2-0"
    num_videos: int = 1
    video_duration_s: int = 6
    # Optional: when present, the gameplay video gets analyzed by Gemini
    # and the resulting GameAnalysis is woven into the brief.
    video_path: str | None = None
    # Optional: when present, the brief lists what assets are available so
    # the prompt can call them by name (and a future agent step can use them).
    asset_dir: str | None = None
    # Genre string from project.json or GDD — used for better SensorTower category matching
    genre: str | None = None


class CreativeForgeResult(BaseModel):
    run_id: str
    target: TargetGame
    patterns: Patterns
    brief: BriefResult
    videos: ScenarioRenderResult
    manifest_path: str


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="creative_forge")
class CreativeForge:
    @workflow.run
    async def run(self, inp: CreativeForgeInput) -> CreativeForgeResult:
        started_at = workflow.now().isoformat(timespec="seconds")

        # Step 1: read the project's GDD/README/etc. → clean title + genre.
        # The project's own docs are the source of truth for what the game IS,
        # not the human-set name+category in project.json.
        intel: ProjectIntel | None = None
        target_term = inp.target_term
        if inp.project_dir:
            intel = await workflow.execute_activity(
                "analyze_project_docs",
                ProjectIntelInput(project_id=inp.project_id, project_dir=inp.project_dir),
                result_type=ProjectIntel,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY,
            )
            if intel.inferred_from_docs and intel.title:
                target_term = intel.title
            await workflow.execute_activity(
                "write_json",
                {"path": f"{inp.run_dir}/project_intel.json", "data": intel.model_dump()},
                start_to_close_timeout=timedelta(seconds=15),
            )

        target: TargetGame = await workflow.execute_activity(
            "resolve_target_game",
            TargetGameInput(term=target_term, genre=inp.genre),
            result_type=TargetGame,
            start_to_close_timeout=timedelta(minutes=2),  # Sensor Tower throttles under parallel load
            retry_policy=_RETRY,
        )

        # Step 2: derive the SensorTower category from the matched app
        # itself — fall back to the workflow input only if no match.
        effective_category: str | int = target.category_id or inp.category
        workflow.logger.info(
            f"[creative_forge] category resolution: project.json={inp.category} → "
            f"matched app={target.category_id} → using={effective_category}"
        )

        market: MarketData = await workflow.execute_activity(
            "fetch_market_data",
            MarketDataInput(
                category=effective_category, country=inp.country,
                network=inp.network, period=inp.period,
            ),
            result_type=MarketData,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=30),
        )

        patterns: Patterns = await workflow.execute_activity(
            "extract_patterns",
            PatternExtractionInput(
                creatives=market.top_creatives,
                sample=inp.sample,
                config_id=inp.config_id,
                top_advertisers=market.top_advertisers,
            ),
            result_type=Patterns,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY,
            heartbeat_timeout=timedelta(seconds=60),
        )

        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/target.json", "data": target.model_dump()},
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
        await workflow.execute_activity(
            "write_json",
            {"path": f"{inp.run_dir}/patterns.json", "data": patterns.model_dump()},
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Optional: analyze the project's gameplay video so the brief can ground
        # the concept in the actual game (mechanic, palette, juice, audio cues),
        # not just the genre. Compression + cache mean repeat runs are free.
        gameplay_analysis: dict = {}
        if inp.video_path:
            ga: GameAnalysis = await workflow.execute_activity(
                "analyze_gameplay_video",
                VideoAnalysisInput(video_path=inp.video_path),
                result_type=GameAnalysis,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY,
                heartbeat_timeout=timedelta(seconds=60),
            )
            gameplay_analysis = ga.raw or {}
            await workflow.execute_activity(
                "write_json",
                {"path": f"{inp.run_dir}/gameplay_analysis.json", "data": gameplay_analysis},
                start_to_close_timeout=timedelta(seconds=15),
            )

        # Optional: enumerate assets so the brief + prompt can reference them by name.
        assets: list[str] = []
        if inp.asset_dir:
            assets = await workflow.execute_activity(
                "list_assets",
                inp.asset_dir,
                result_type=list[str],
                start_to_close_timeout=timedelta(seconds=15),
            )

        brief: BriefResult = await workflow.execute_activity(
            "write_brief_and_prompt",
            BriefInput(
                target=target,
                patterns=patterns,
                out_dir=inp.run_dir,
                gameplay_analysis=gameplay_analysis,
                assets=assets,
            ),
            result_type=BriefResult,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY,
        )

        # The grounded-i2v config asks Seedance to do image-to-video starting
        # from the actual gameplay video's first frame — fixes the dominant
        # complaint that "the video is disconnected from my game" by pinning
        # the visual at INPUT time (not prompting harder for "make it look
        # like our game"). The seed-frame artifact lands in run_dir so it's
        # auditable in the UI.
        seed_image_path: str | None = None
        if inp.config_id == "grounded-i2v" and inp.video_path:
            seed_path = f"{inp.run_dir}/seed_frame.jpg"
            seed_image_path = await workflow.execute_activity(
                "extract_seed_frame",
                {"video_path": inp.video_path, "out_path": seed_path, "at_seconds": 3.0},
                result_type=str,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_RETRY,
            )

        # render_seedance gets a single-attempt retry policy: Seedance is
        # non-deterministic and expensive, so retries (a) waste credits and
        # (b) produce a DIFFERENT video that overwrites the first one —
        # the user observed this as "the video changes when I reload the
        # page." The activity is also idempotent now (skips if file exists),
        # so even if Temporal does retry it'll no-op.
        videos: ScenarioRenderResult = await workflow.execute_activity(
            "render_seedance",
            ScenarioRenderInput(
                prompt_path=brief.scenario_prompt_path,
                out_dir=inp.run_dir,
                num_images=inp.num_videos,
                mode="video",
                video_duration_s=inp.video_duration_s,
                config_id=inp.config_id,
                model_id=inp.seedance_model_id,
                seed_image_path=seed_image_path,
            ),
            result_type=ScenarioRenderResult,
            start_to_close_timeout=timedelta(minutes=20),
            retry_policy=RetryPolicy(maximum_attempts=1),
            heartbeat_timeout=timedelta(minutes=5),
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
                artifact_globs=["*.json", "*.md", "*.txt", "*.png", "*.jpg", "*.mp4"],
            ),
            result_type=FinalizeRunResult,
            start_to_close_timeout=timedelta(seconds=15),
        )

        return CreativeForgeResult(
            run_id=inp.run_id,
            target=target,
            patterns=patterns,
            brief=brief,
            videos=videos,
            manifest_path=finalized.manifest_path,
        )
