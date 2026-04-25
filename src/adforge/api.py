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

from adforge import projects as projects_mod
from adforge.config import RUNS_DIR
from adforge.pipelines import PIPELINES
from adforge.runs import list_runs

app = FastAPI(title="adforge api", version="0.2.0")

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
        m = json.loads(p.read_text())
        # Back-compat: old manifests stored target_id; expose it as project_id too.
        if "project_id" not in m and "target_id" in m:
            m["project_id"] = m["target_id"]
        return m
    except Exception:
        return None


def _safe_run_path(run_id: str, rel: str) -> Path:
    base = (RUNS_DIR / run_id).resolve()
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=400, detail="invalid path")
    return target


def _summarize_manifest(rid: str, m: dict[str, Any] | None) -> dict[str, Any]:
    if m is None:
        return {
            "run_id": rid, "pipeline": None, "project_id": None, "config_id": None,
            "status": "unknown", "started_at": None, "completed_at": None,
            "artifact_count": 0, "has_manifest": False,
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
