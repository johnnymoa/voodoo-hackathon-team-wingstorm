"""Pydantic models passed between activities/workflows.

Temporal serializes data with JSON; using pydantic gives us validation + clarity.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ───── playable_forge ──────────────────────────────────────────────────────────


class VideoAnalysisInput(BaseModel):
    video_path: str
    prompt: str | None = None


class GameAnalysis(BaseModel):
    raw: dict[str, Any]                  # the full Gemini JSON
    title: str | None = None
    core_loop_summary: str | None = None
    primary_input: str | None = None
    palette: list[str] | None = None


class PlayableBuildInput(BaseModel):
    analysis: GameAnalysis
    asset_dir: str | None = None
    market_patterns: dict[str, Any] | None = None   # optional: from creative_forge
    out_path: str


class PlayableBuildResult(BaseModel):
    html_path: str
    size_mb: float


class VariationSpec(BaseModel):
    name: str
    overrides: dict[str, Any]
    rationale: str | None = None         # why this variation tests something useful


class VariationsInput(BaseModel):
    base_html_path: str
    variants: list[VariationSpec]
    out_dir: str


class VariationsResult(BaseModel):
    files: list[str]


# ───── creative_forge ──────────────────────────────────────────────────────────


class TargetGameInput(BaseModel):
    term: str                            # e.g. "castle clasher"


class TargetGame(BaseModel):
    app_id: str
    name: str
    publisher_name: str | None = None
    raw: dict[str, Any]


class MarketDataInput(BaseModel):
    category: str | int = 7012
    country: str = "US"
    network: str = "TikTok"
    period: str = "month"
    limit: int = 80


class MarketData(BaseModel):
    top_advertisers: dict[str, Any]
    top_creatives: dict[str, Any]


class PatternExtractionInput(BaseModel):
    creatives: dict[str, Any]
    sample: int = 30


class Patterns(BaseModel):
    creative_count: int
    categories: dict[str, list[dict[str, Any]]]
    per_creative: list[dict[str, Any]]


class BriefInput(BaseModel):
    target: TargetGame
    patterns: Patterns
    out_dir: str


class BriefResult(BaseModel):
    brief_path: str
    scenario_prompt_path: str


class ScenarioRenderInput(BaseModel):
    prompt_path: str
    out_dir: str
    num_images: int = 3
    width: int = 1024
    height: int = 1820


class ScenarioRenderResult(BaseModel):
    image_paths: list[str]
