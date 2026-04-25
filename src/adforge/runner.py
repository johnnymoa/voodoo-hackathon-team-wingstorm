"""Workflow launcher used by the FastAPI shim (and reusable by the CLI).

Kicks off a Temporal workflow without awaiting it, mints the run_id, creates
the run_dir, and writes a placeholder manifest so the UI can render a
'running' state immediately. The pipeline's `finalize_run` activity overwrites
the manifest at the end with the real status + artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adforge import projects as projects_mod
from adforge.activities.types import VariationSpec
from adforge.config import settings
from adforge.pipelines import find_config, find_pipeline
from adforge.runs import ensure_run_dir, make_run_id


class StartRunError(Exception):
    """Raised when a run can't be started (bad pipeline/config/project)."""


_DEFAULT_PLAYABLE_VARIANTS = [
    VariationSpec(name="easy",     overrides={"enemySpeed": 60,  "winScore": 8,  "spawnEverySeconds": 1.6}),
    VariationSpec(name="hard",     overrides={"enemySpeed": 140, "winScore": 18, "spawnEverySeconds": 0.7}),
    VariationSpec(name="speedrun", overrides={"sessionSeconds": 15}),
    VariationSpec(name="neon",     overrides={"palette": ["#0b0b1a", "#ff2bd6", "#22e1ff", "#fff700", "#ff7849"]}),
]

_PIPELINE_SHORT = {"creative_forge": "creative", "playable_forge": "playable"}


def _build_workflow_input(
    pipeline_id: str,
    project: projects_mod.Project,
    run_id: str,
    run_dir: str,
    config_id: str,
):
    if pipeline_id == "playable_forge":
        from adforge.pipelines.playable_forge import PlayableForgeInput
        if not project.has_video():
            raise StartRunError(f"project '{project.id}' has no video.mp4 — playable_forge needs one.")
        return PlayableForgeInput(
            project_id=project.id, run_id=run_id, run_dir=run_dir, config_id=config_id,
            video_path=project.video_path,
            asset_dir=project.asset_dir,
            variants=_DEFAULT_PLAYABLE_VARIANTS,
        )
    if pipeline_id == "creative_forge":
        from adforge.pipelines.creative_forge import CreativeForgeInput
        cfg = find_config(pipeline_id, config_id)
        params = (cfg.params if cfg else {}) or {}
        return CreativeForgeInput(
            project_id=project.id, run_id=run_id, run_dir=run_dir, config_id=config_id,
            target_term=project.name,
            category=project.category_id, country=project.country,
            render_with_scenario_http=bool(params.get("render_with_scenario_http", False)),
            render_mode=str(params.get("render_mode", "image")),
            num_images=int(params.get("num_images", 3)),
            video_duration_s=int(params.get("video_duration_s", 5)),
        )
    raise StartRunError(f"unknown pipeline '{pipeline_id}'")


def _write_manifest_stub(
    run_dir: Path, *,
    run_id: str, pipeline: str, project_id: str, config_id: str, started_at: str,
) -> None:
    manifest = {
        "run_id": run_id,
        "pipeline": pipeline,
        "project_id": project_id,
        "config_id": config_id,
        "status": "running",
        "started_at": started_at,
        "completed_at": None,
        "params": {},
        "artifacts": [],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


async def start_run(pipeline_id: str, project_id: str, config_id: str = "default") -> dict[str, Any]:
    """Kick off a Temporal workflow. Returns metadata immediately; does not await result."""
    spec = find_pipeline(pipeline_id)
    if spec is None:
        raise StartRunError(f"unknown pipeline '{pipeline_id}'")
    if find_config(pipeline_id, config_id) is None:
        avail = ", ".join(c.id for c in spec.configs) or "<none>"
        raise StartRunError(f"unknown config '{config_id}' for {pipeline_id}. Available: {avail}")

    try:
        project = projects_mod.load(project_id)
    except FileNotFoundError as e:
        raise StartRunError(str(e))

    short = _PIPELINE_SHORT.get(pipeline_id, pipeline_id)
    run_id = make_run_id(short, project.id)
    run_dir = ensure_run_dir(run_id)

    inp = _build_workflow_input(pipeline_id, project, run_id, str(run_dir), config_id)

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_manifest_stub(
        run_dir, run_id=run_id, pipeline=pipeline_id,
        project_id=project.id, config_id=config_id, started_at=started_at,
    )

    from temporalio.client import Client
    from temporalio.contrib.pydantic import pydantic_data_converter

    s = settings()
    client = await Client.connect(
        s.temporal_address,
        namespace=s.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
    await client.start_workflow(
        pipeline_id, inp, id=run_id, task_queue=s.temporal_task_queue,
    )

    return {
        "run_id": run_id,
        "pipeline": pipeline_id,
        "project_id": project.id,
        "config_id": config_id,
        "started_at": started_at,
        "status": "running",
    }
