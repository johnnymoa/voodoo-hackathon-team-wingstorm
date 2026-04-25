"""Project config — loads .env once and exposes typed access."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "output"
ASSETS_DIR = REPO_ROOT / "assets"
VIDEOS_DIR = REPO_ROOT / "videos"
CACHE_DIR = REPO_ROOT / ".cache"


class Settings(BaseModel):
    # LLM keys
    gemini_api_key: str
    anthropic_api_key: str = ""
    mistral_api_key: str = ""

    # Market data
    sensortower_api_key: str

    # Scenario (image gen — primarily via MCP; optional HTTP for headless mode)
    scenario_project_id: str = ""
    scenario_api_key: str = ""
    scenario_secret_api_key: str = ""

    # Temporal (defaults work with `temporal server start-dev`)
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "adforge"

    # Pipeline defaults
    default_country: str = "US"
    default_category_id: str = "7012"     # iOS Puzzle
    default_network: str = "TikTok"
    default_period: str = "month"


@lru_cache
def settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env", override=False)
    missing = [k for k in ("GEMINI_API_KEY", "SENSORTOWER_API_KEY") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}. Edit .env at repo root.")
    return Settings(
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        mistral_api_key=os.environ.get("MISTRAL_API_KEY", ""),
        sensortower_api_key=os.environ["SENSORTOWER_API_KEY"],
        scenario_project_id=os.environ.get("SCENARIO_PROJECT_ID", ""),
        scenario_api_key=os.environ.get("SCENARIO_API_KEY", ""),
        scenario_secret_api_key=os.environ.get("SCENARIO_SECRET_API_KEY", ""),
        temporal_address=os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"),
        temporal_namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
        temporal_task_queue=os.environ.get("TEMPORAL_TASK_QUEUE", "adforge"),
        default_country=os.environ.get("DEFAULT_COUNTRY", "US"),
        default_category_id=os.environ.get("DEFAULT_CATEGORY_ID", "7012"),
        default_network=os.environ.get("DEFAULT_NETWORK", "TikTok"),
        default_period=os.environ.get("DEFAULT_PERIOD", "month"),
    )


def ensure_dirs() -> None:
    for d in (
        OUTPUT_DIR,
        OUTPUT_DIR / "playables",
        OUTPUT_DIR / "creatives",
        OUTPUT_DIR / "full",
        CACHE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
