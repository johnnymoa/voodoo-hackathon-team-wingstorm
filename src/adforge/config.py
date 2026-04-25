"""Project config — loads .env once and exposes typed access.

Three top-level data buckets at the repo root, mapped to constants:

    projects/      PROJECTS_DIR    pipeline inputs (one folder per game)
    runs/          RUNS_DIR        pipeline outputs (one folder per execution)
    .cache/        CACHE_DIR       SensorTower API cache (internal)

Code never hard-codes these paths — always import from here.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def _repo_root() -> Path:
    """Project root for resolving projects/, runs/.

    Order:
      1. ADFORGE_ROOT env var (explicit override).
      2. Walk up from cwd looking for a marker (pyproject.toml + src/adforge/).
      3. Fall back to cwd.

    This works in both editable and wheel installs — file-relative paths can't,
    because under a wheel install __file__ lives in site-packages.
    """
    if env := os.environ.get("ADFORGE_ROOT"):
        return Path(env).expanduser().resolve()
    here = Path.cwd()
    for cand in [here, *here.parents]:
        if (cand / "pyproject.toml").is_file() and (cand / "src" / "adforge").is_dir():
            return cand
    return here


REPO_ROOT = _repo_root()
PROJECTS_DIR = REPO_ROOT / "projects"
RUNS_DIR = REPO_ROOT / "runs"
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
    for d in (PROJECTS_DIR, RUNS_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
