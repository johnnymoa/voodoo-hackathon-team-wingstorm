"""FastAPI shim — serves projects/ + runs/ to the Vite UI.

Endpoints:

    GET  /api/health                     liveness
    GET  /api/projects                   list of projects (with video/assets flags)
    GET  /api/projects/{id}              one project's resolved metadata + paths
    GET  /api/projects/{id}/runs         runs for one project, newest first
    GET  /api/pipelines                  pipeline catalog (with PipelineConfig presets)
    GET  /api/runs                       list of runs, newest first (manifest summary)
    GET  /api/runs/{run_id}              one run's full manifest
    GET  /api/runs/{run_id}/text/{rel}   read a text artifact (md/json/txt) as utf-8
    GET  /artifacts/{run_id}/{rel:path}  raw static serve of an artifact (HTML, PNG, …)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from adforge import feedback as feedback_mod
from adforge import projects as projects_mod
from adforge.config import RUNS_DIR
from adforge.pipelines import PIPELINES
from adforge.runner import StartRunError, start_run
from adforge.runs import list_runs

app = FastAPI(title="adforge api", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _read_manifest(run_id: str) -> dict[str, Any] | None:
    p = RUNS_DIR / run_id / "manifest.json"
    if not p.is_file():
        return None
    try:
        m = json.loads(p.read_text())
        # Back-compat: old manifests stored target_id; expose it as project_id too.
        if "project_id" not in m and "target_id" in m:
            m["project_id"] = m["target_id"]
        # Self-heal: if the worker died mid-finalize and the manifest is still
        # the "running" stub, infer the real status from disk. A run is
        # *completed* if the pipeline's expected final artifact exists; *failed*
        # if the run dir is older than 30 minutes with no signal of progress.
        m = _self_heal(run_id, m)
        return m
    except Exception:
        return None


def _self_heal(run_id: str, m: dict[str, Any]) -> dict[str, Any]:
    """Recompute status from artifacts on disk if manifest stub is stale.

    The Temporal pipeline writes a "running" stub at submit time and the
    `finalize_run` activity overwrites it on success. If the worker is killed
    between the last activity and finalize_run (e.g. `make restart` mid-flight),
    the artifacts are on disk but the manifest still says running. Fix that.
    """
    if m.get("status") != "running":
        return m

    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        return m

    pipeline = m.get("pipeline", "")
    finals_creative = list(run_dir.glob("creative_*.mp4"))
    finals_playable = list(run_dir.glob("playable.html"))

    final_present = (
        bool(finals_creative) if pipeline == "creative_forge"
        else bool(finals_playable) if pipeline == "playable_forge"
        else bool(finals_creative or finals_playable)
    )

    if final_present:
        m = dict(m)
        m["status"] = "completed"
        # Best-effort completion timestamp from the latest artifact mtime
        latest = max(
            (p.stat().st_mtime for p in run_dir.iterdir() if p.is_file() and p.name != "manifest.json"),
            default=None,
        )
        if latest is not None and not m.get("completed_at"):
            from datetime import datetime, timezone
            m["completed_at"] = datetime.fromtimestamp(latest, tz=timezone.utc).isoformat(timespec="seconds")
        # Surface every file in the dir so the UI shows them, since the original
        # finalize_run never got to populate the artifacts list.
        if not m.get("artifacts"):
            m["artifacts"] = [
                {
                    "name": str(p.relative_to(run_dir)),
                    "kind": p.suffix.lstrip(".").lower() or "bin",
                    "size_bytes": p.stat().st_size,
                }
                for p in sorted(run_dir.iterdir())
                if p.is_file() and p.name != "manifest.json"
            ]
        m["status_inferred"] = True   # tell the UI we self-healed
        return m

    # No final artifact and the stub is older than 15 minutes → mark failed.
    # Cold-cache runs take ~3min; 6 runs in parallel can stretch to 8-10min;
    # 15min covers worst case without leaving genuinely stuck runs forever.
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_file():
        import time as _t
        if _t.time() - manifest_path.stat().st_mtime > 900:
            m = dict(m)
            m["status"] = "failed"
            m["status_inferred"] = True
            return m

    return m


def _safe_run_path(run_id: str, rel: str) -> Path:
    base = (RUNS_DIR / run_id).resolve()
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="invalid path")
    return target


def _has_open_feedback(rid: str) -> tuple[bool, str | None]:
    """Quick check for the runs list: does this run have a non-empty feedback.md?

    Returns (has_feedback, status). Status is "open" / "fulfilled" / "wontfix".
    Reads the file directly and shallow-parses to avoid pulling all of feedback_mod.
    """
    p = RUNS_DIR / rid / "feedback.md"
    if not p.is_file():
        return False, None
    try:
        text = p.read_text()
    except Exception:
        return False, None
    if "---" not in text:
        return False, None
    # Look for status: line in frontmatter
    fm_end = text.find("---", 3)
    fm = text[:fm_end] if fm_end != -1 else text
    body = text[fm_end + 3:].strip() if fm_end != -1 else ""
    status = None
    for line in fm.splitlines():
        if line.strip().startswith("status:"):
            status = line.split(":", 1)[1].strip()
            break
    return bool(body), status


def _summarize_manifest(rid: str, m: dict[str, Any] | None) -> dict[str, Any]:
    has_fb, fb_status = _has_open_feedback(rid)
    if m is None:
        return {
            "run_id": rid, "pipeline": None, "project_id": None, "config_id": None,
            "status": "unknown", "started_at": None, "completed_at": None,
            "artifact_count": 0, "has_manifest": False,
            "has_feedback": has_fb, "feedback_status": fb_status,
        }
    return {
        "run_id": m.get("run_id", rid),
        "pipeline": m.get("pipeline"),
        "project_id": m.get("project_id") or m.get("target_id"),
        "config_id": m.get("config_id"),
        "status": m.get("status"),
        "started_at": m.get("started_at"),
        "completed_at": m.get("completed_at"),
        "artifact_count": len(m.get("artifacts", [])),
        "has_manifest": True,
        "has_feedback": has_fb,
        "feedback_status": fb_status,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/pipelines")
def api_pipelines() -> list[dict[str, Any]]:
    return [p.model_dump() for p in PIPELINES]


@app.get("/api/projects")
def api_projects() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pid in projects_mod.list_projects():
        try:
            p = projects_mod.load(pid)
            out.append({
                "id": p.id,
                "name": p.name,
                "genre": p.genre,
                "description": p.description,
                "category_id": p.category_id,
                "country": p.country,
                "has_video": p.has_video(),
                "has_assets": p.has_assets(),
                "notes": p.notes,
            })
        except Exception as e:
            out.append({"id": pid, "name": pid, "error": str(e)})
    return out


@app.get("/api/projects/{project_id}")
def api_project(project_id: str) -> dict[str, Any]:
    try:
        p = projects_mod.load(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # `has_video` / `has_assets` are methods on the model; surface them explicitly.
    return {**p.model_dump(), "has_video": p.has_video(), "has_assets": p.has_assets()}


@app.get("/api/projects/{project_id}/runs")
def api_project_runs(project_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rid in list_runs():
        m = _read_manifest(rid)
        if m and (m.get("project_id") or m.get("target_id")) == project_id:
            out.append(_summarize_manifest(rid, m))
    return out


@app.get("/api/runs")
def api_runs() -> list[dict[str, Any]]:
    return [_summarize_manifest(rid, _read_manifest(rid)) for rid in list_runs()]


@app.get("/api/feedback")
def api_feedback_index(status: str = "open") -> list[dict[str, Any]]:
    """Cross-run feedback index for the Iterate page.

    Returns one row per run with non-empty feedback, joined with the run's
    pipeline/project/config context AND addressed-by lineage if any. The UI
    uses this to surface "what to iterate on next" in one place.

    Query: ?status=open|fulfilled|wontfix|all  (default: open)
    """
    out: list[dict[str, Any]] = []
    for rid in list_runs():
        fb = feedback_mod.load(rid)
        if fb is None or not fb.body.strip():
            continue
        if status != "all" and fb.status != status:
            continue
        m = _read_manifest(rid) or {}
        out.append({
            "run_id": rid,
            "pipeline": m.get("pipeline"),
            "project_id": m.get("project_id") or m.get("target_id"),
            "config_id": m.get("config_id"),
            "run_status": m.get("status"),
            "started_at": m.get("started_at"),
            "feedback_status": fb.status,
            "body": fb.body.strip(),
            "created_at": fb.created_at,
            "updated_at": fb.updated_at,
            "addressed_in_run": fb.addressed_in_run,
            "addressed_by_config": fb.addressed_by_config,
        })
    # Newest first by updated_at
    out.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return out


class StartRunBody(BaseModel):
    pipeline_id: str
    project_id: str
    config_id: str = "default"


@app.post("/api/runs")
async def api_start_run(body: StartRunBody) -> dict[str, Any]:
    """Kick off a Temporal workflow. Returns the new run_id; does not await result."""
    try:
        return await start_run(body.pipeline_id, body.project_id, body.config_id)
    except StartRunError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to start workflow: {e}")


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> dict[str, Any]:
    m = _read_manifest(run_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"no manifest for {run_id}")
    return m


class SaveFeedbackBody(BaseModel):
    body: str
    status: str | None = None


@app.get("/api/runs/{run_id}/feedback")
def api_get_feedback(run_id: str) -> dict[str, Any]:
    fb = feedback_mod.load(run_id)
    if fb is None:
        # Return a synthetic empty record so the UI can show the editor
        # without first having to handle 404s.
        return {
            "run_id": run_id,
            "status": "open",
            "created_at": None,
            "updated_at": None,
            "addressed_in_run": None,
            "addressed_by_config": None,
            "body": "",
            "exists": False,
        }
    return {**fb.model_dump(), "exists": True}


@app.post("/api/runs/{run_id}/feedback")
def api_save_feedback(run_id: str, body: SaveFeedbackBody) -> dict[str, Any]:
    if not (RUNS_DIR / run_id).is_dir():
        raise HTTPException(status_code=404, detail=f"no run dir for {run_id}")
    try:
        fb = feedback_mod.save(run_id, body.body, status=body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**fb.model_dump(), "exists": True}


@app.get("/api/feedback")
def api_list_feedback(status: str | None = None) -> list[dict[str, Any]]:
    return [fb.model_dump() for fb in feedback_mod.list_all(status=status)]


@app.get("/api/runs/{run_id}/text/{rel:path}", response_class=PlainTextResponse)
def api_run_text(run_id: str, rel: str) -> str:
    p = _safe_run_path(run_id, rel)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="not found")
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="not a text artifact")


@app.get("/artifacts/{run_id}/{rel:path}")
def artifacts(run_id: str, rel: str) -> FileResponse:
    p = _safe_run_path(run_id, rel)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(p)
