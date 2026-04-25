"""Activity: finalize_run — stamp manifest.json into a run folder.

Every pipeline calls this as its last step. The manifest is the single record
the UI / CLI / future tools read to know what a run produced. Artifacts are
listed as paths *relative* to the run_dir so the folder is portable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from temporalio import activity


class FinalizeRunInput(BaseModel):
    run_dir: str
    run_id: str
    pipeline: str                          # "playable_forge" | "creative_forge" | "full_forge"
    target_id: str
    started_at: str                        # ISO-8601, set by the workflow
    params: dict[str, Any] = {}            # the workflow's input args (for reproducibility)
    artifact_globs: list[str] = []         # patterns to include, e.g. ["*.html", "*.json", "**/*.html"]
    children: list[str] = []               # child run_ids (full_forge → [creative_run, playable_run])
    status: str = "completed"


class FinalizeRunResult(BaseModel):
    manifest_path: str
    artifact_count: int


def _collect_artifacts(run_dir: Path, globs: list[str]) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    out: list[dict[str, Any]] = []
    for pattern in globs:
        for p in run_dir.glob(pattern):
            if not p.is_file() or p.name == "manifest.json" or p in seen:
                continue
            seen.add(p)
            rel = p.relative_to(run_dir)
            out.append({
                "name": str(rel),
                "kind": p.suffix.lstrip(".") or "bin",
                "size_bytes": p.stat().st_size,
            })
    out.sort(key=lambda a: a["name"])
    return out


@activity.defn(name="finalize_run")
async def finalize_run(inp: FinalizeRunInput) -> FinalizeRunResult:
    run_dir = Path(inp.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts = _collect_artifacts(run_dir, inp.artifact_globs or ["*"])
    manifest = {
        "run_id": inp.run_id,
        "pipeline": inp.pipeline,
        "target_id": inp.target_id,
        "status": inp.status,
        "started_at": inp.started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": inp.params,
        "children": inp.children,
        "artifacts": artifacts,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return FinalizeRunResult(manifest_path=str(manifest_path), artifact_count=len(artifacts))
