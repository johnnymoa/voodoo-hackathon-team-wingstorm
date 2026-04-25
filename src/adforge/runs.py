"""Runs — the on-disk record of every pipeline execution.

A run is a single folder under `runs/<run_id>/` holding:

    runs/<run_id>/
      manifest.json    # {pipeline, target_id, started_at, status, artifacts, ...}
      <pipeline-specific outputs>

`run_id` format:  `YYYYMMDD-HHMMSS__<pipeline>__<target_id>`
This sorts chronologically (`ls runs/`), greps by pipeline (`ls runs/ | grep creative`),
and survives copy-paste into Temporal's workflow_id field.

The CLI mints the run_id and creates the run_dir; pipelines just write into it
and call `finalize_run` at the end to stamp manifest.json.
"""

from __future__ import annotations

import time
from pathlib import Path

from adforge.config import RUNS_DIR


def make_run_id(pipeline: str, target_id: str) -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}__{pipeline}__{target_id}"


def run_dir(run_id: str) -> Path:
    """Absolute path of a run's folder. Does not create it."""
    return RUNS_DIR / run_id


def ensure_run_dir(run_id: str) -> Path:
    p = run_dir(run_id)
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_runs() -> list[str]:
    """All run ids on disk, newest first."""
    if not RUNS_DIR.exists():
        return []
    return sorted(
        (p.name for p in RUNS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")),
        reverse=True,
    )
