"""FastAPI shim — serves runs/ + targets/ to the Vite UI.

Endpoints:

    GET  /api/health                     liveness
    GET  /api/targets                    list of targets (with video/assets flags)
    GET  /api/targets/{id}               one target's resolved metadata + paths
    GET  /api/runs                       list of runs, newest first (manifest summary)
    GET  /api/runs/{run_id}              one run's full manifest
    GET  /api/runs/{run_id}/text/{rel}   read a text artifact (md/json/txt) as utf-8
    GET  /artifacts/{run_id}/{rel:path}  raw static serve of an artifact (HTML, PNG, …)

The UI (ui/) is a Vite SPA in dev. In prod it can be built into ui/dist and
served by mounting StaticFiles at "/" — left as a follow-up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from adforge import targets as targets_mod
from adforge.config import RUNS_DIR
from adforge.pipelines import PIPELINES
from adforge.runs import list_runs

app = FastAPI(title="adforge api", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _read_manifest(run_id: str) -> dict[str, Any] | None:
    p = RUNS_DIR / run_id / "manifest.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _safe_run_path(run_id: str, rel: str) -> Path:
    base = (RUNS_DIR / run_id).resolve()
    target = (base / rel).resolve()
    # prevent path traversal outside the run folder
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="invalid path")
    return target


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/pipelines")
def api_pipelines() -> list[dict[str, Any]]:
    return [p.model_dump() for p in PIPELINES]


@app.get("/api/targets")
def api_targets() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tid in targets_mod.list_targets():
        try:
            t = targets_mod.load(tid)
            out.append({
                "id": t.id,
                "name": t.name,
                "genre": t.genre,
                "description": t.description,
                "category_id": t.category_id,
                "country": t.country,
                "has_video": t.has_video(),
                "has_assets": t.has_assets(),
                "notes": t.notes,
            })
        except Exception as e:
            out.append({"id": tid, "name": tid, "error": str(e)})
    return out


@app.get("/api/targets/{target_id}")
def api_target(target_id: str) -> dict[str, Any]:
    try:
        t = targets_mod.load(target_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return t.model_dump()


@app.get("/api/runs")
def api_runs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rid in list_runs():
        m = _read_manifest(rid)
        if m is None:
            out.append({
                "run_id": rid, "pipeline": None, "target_id": None,
                "status": "unknown", "started_at": None, "completed_at": None,
                "artifact_count": 0, "has_manifest": False,
            })
            continue
        out.append({
            "run_id": m.get("run_id", rid),
            "pipeline": m.get("pipeline"),
            "target_id": m.get("target_id"),
            "status": m.get("status"),
            "started_at": m.get("started_at"),
            "completed_at": m.get("completed_at"),
            "artifact_count": len(m.get("artifacts", [])),
            "has_manifest": True,
        })
    return out


@app.get("/api/runs/{run_id}")
def api_run(run_id: str) -> dict[str, Any]:
    m = _read_manifest(run_id)
    if m is None:
        raise HTTPException(status_code=404, detail=f"no manifest for {run_id}")
    return m


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
