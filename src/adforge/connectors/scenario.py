"""Scenario connector — primary path is the Scenario MCP inside Claude Code.

This module provides a minimal HTTP fallback for headless / Temporal usage.
If you only operate via Claude Code + the Scenario MCP, you can ignore this file.

Docs: https://docs.scenario.com/  (auth + endpoints)
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Callable

import httpx

from adforge.config import settings

BASE = "https://api.cloud.scenario.com/v1"


def _headers() -> dict[str, str]:
    """Scenario uses HTTP Basic auth with `apiKey:secretKey` base64-encoded."""
    s = settings()
    api_key, secret = s.scenario_api_key, s.scenario_secret_api_key
    if not api_key or not secret:
        raise RuntimeError(
            "SCENARIO_API_KEY and SCENARIO_SECRET_API_KEY must both be set in .env "
            "for headless use. Alternatively, drive Scenario via the MCP inside Claude Code."
        )
    token = base64.b64encode(f"{api_key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def generate_image(
    prompt: str,
    *,
    model_id: str | None = None,
    width: int = 1024,
    height: int = 1820,         # 9:16-ish
    num_images: int = 1,
    timeout_s: float = 180.0,
) -> list[bytes]:
    """Submit a generation job and poll until it returns image bytes.

    Returns a list of image bytes (one per `num_images`). Raises on timeout / failure.
    """
    body: dict = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "numSamples": num_images,
    }
    if model_id:
        body["modelId"] = model_id

    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{BASE}/generate/txt2img", headers=_headers(), json=body)
        r.raise_for_status()
        job_id = r.json().get("inferenceId") or r.json().get("job", {}).get("id")
        if not job_id:
            raise RuntimeError(f"Unexpected Scenario response: {r.json()}")

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(2.0)
            sr = client.get(f"{BASE}/generate/{job_id}", headers=_headers())
            sr.raise_for_status()
            data = sr.json()
            status = (data.get("status") or "").lower()
            if status in ("succeeded", "success", "completed"):
                images = data.get("images") or []
                urls = [img.get("url") for img in images if img.get("url")]
                results: list[bytes] = []
                for u in urls:
                    ir = client.get(u)
                    ir.raise_for_status()
                    results.append(ir.content)
                return results
            if status in ("failed", "error", "canceled"):
                raise RuntimeError(f"Scenario job {job_id} failed: {data}")
        raise TimeoutError(f"Scenario job {job_id} timed out after {timeout_s}s")


def save_images(images: list[bytes], out_dir: str | Path, prefix: str = "scenario") -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, b in enumerate(images, 1):
        p = out / f"{prefix}_{i:02d}.png"
        p.write_bytes(b)
        paths.append(p)
    return paths


def generate_video(
    prompt: str,
    *,
    model_id: str | None = None,
    width: int = 1024,
    height: int = 1820,         # 9:16-ish
    num_videos: int = 1,
    duration_s: int = 5,
    timeout_s: float = 600.0,
) -> list[bytes]:
    """Submit a text-to-video job and poll until it returns video bytes (.mp4).

    Returns a list of mp4 bytes (one per `num_videos`). Raises on timeout / failure.
    """
    body: dict = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "numSamples": num_videos,
        "duration": duration_s,
    }
    if model_id:
        body["modelId"] = model_id

    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{BASE}/generate/txt2vid", headers=_headers(), json=body)
        r.raise_for_status()
        job_id = r.json().get("inferenceId") or r.json().get("job", {}).get("id")
        if not job_id:
            raise RuntimeError(f"Unexpected Scenario txt2vid response: {r.json()}")

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            time.sleep(3.0)
            sr = client.get(f"{BASE}/generate/{job_id}", headers=_headers())
            sr.raise_for_status()
            data = sr.json()
            status = (data.get("status") or "").lower()
            if status in ("succeeded", "success", "completed"):
                videos = data.get("videos") or data.get("assets") or []
                urls = [v.get("url") for v in videos if v.get("url")]
                results: list[bytes] = []
                for u in urls:
                    vr = client.get(u)
                    vr.raise_for_status()
                    results.append(vr.content)
                return results
            if status in ("failed", "error", "canceled"):
                raise RuntimeError(f"Scenario video job {job_id} failed: {data}")
        raise TimeoutError(f"Scenario video job {job_id} timed out after {timeout_s}s")


def save_videos(videos: list[bytes], out_dir: str | Path, prefix: str = "scenario") -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, b in enumerate(videos, 1):
        p = out / f"{prefix}_{i:02d}.mp4"
        p.write_bytes(b)
        paths.append(p)
    return paths


SEEDANCE_2_0 = "model_bytedance-seedance-2-0"
SEEDANCE_2_0_FAST = "model_bytedance-seedance-2-0-fast"
SEEDANCE_1_5_PRO = "model_bytedance-seedance-1-5-pro"


def generate_video_seedance(
    prompt: str,
    *,
    model_id: str = SEEDANCE_2_0,
    aspect_ratio: str = "9:16",
    duration_s: int = 6,
    resolution: str = "720p",
    seed: int | None = None,
    generate_audio: bool = True,
    num_videos: int = 1,
    image_url: str | None = None,
    timeout_s: float = 900.0,
    poll_interval_s: float = 3.0,
    on_heartbeat: Callable[[str], None] | None = None,
) -> list[bytes]:
    """Generate video via Scenario's unified `/generate/custom/{modelId}` endpoint.

    This is the path for Seedance 2.0 / 2.0-fast / 1.5-pro / 1-pro and friends.
    Submit one job per video, poll `/v1/jobs/{jobId}` until success, resolve
    each `assetIds[]` entry through `/v1/assets/{assetId}`, then download the
    mp4 from `asset.url`.

    Returns: list of mp4 bytes, length = num_videos. Raises on timeout/failure.
    """
    body_base: dict = {
        "prompt": prompt,
        "duration": duration_s,
        "resolution": resolution,
        "aspectRatio": aspect_ratio,
        "generateAudio": generate_audio,
    }
    if seed is not None:
        body_base["seed"] = seed
    if image_url:
        body_base["image"] = image_url        # i2v mode

    results: list[bytes] = []
    with httpx.Client(timeout=60.0) as client:
        for n in range(1, num_videos + 1):
            if on_heartbeat:
                on_heartbeat(f"submitting seedance job {n}/{num_videos}")

            r = client.post(
                f"{BASE}/generate/custom/{model_id}",
                headers=_headers(),
                json=body_base,
            )
            if r.status_code >= 400:
                raise RuntimeError(f"Scenario submit failed ({r.status_code}): {r.text[:400]}")
            payload = r.json()
            job_id = payload.get("jobId") or (payload.get("job") or {}).get("jobId")
            if not job_id:
                raise RuntimeError(f"Unexpected Scenario submit response: {payload}")

            asset_ids = _poll_job(client, job_id, timeout_s=timeout_s,
                                  poll_interval_s=poll_interval_s,
                                  on_heartbeat=on_heartbeat)
            for aid in asset_ids:
                url = _resolve_asset_url(client, aid)
                vr = client.get(url, timeout=120.0)
                vr.raise_for_status()
                results.append(vr.content)
    return results


def _poll_job(
    client: httpx.Client,
    job_id: str,
    *,
    timeout_s: float,
    poll_interval_s: float,
    on_heartbeat: Callable[[str], None] | None,
) -> list[str]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(poll_interval_s)
        sr = client.get(f"{BASE}/jobs/{job_id}", headers=_headers())
        sr.raise_for_status()
        data = sr.json()
        job = data.get("job") or data
        status = (job.get("status") or "").lower()
        progress = job.get("progress")
        if on_heartbeat:
            on_heartbeat(f"job {job_id} status={status} progress={progress}")
        if status == "success":
            asset_ids = (job.get("metadata") or {}).get("assetIds") or []
            if not asset_ids:
                raise RuntimeError(f"Scenario job {job_id} succeeded but returned no assetIds: {data}")
            return asset_ids
        if status in ("failed", "canceled", "error"):
            raise RuntimeError(f"Scenario job {job_id} ended in {status}: {data}")
    raise TimeoutError(f"Scenario job {job_id} timed out after {timeout_s}s")


def _resolve_asset_url(client: httpx.Client, asset_id: str) -> str:
    ar = client.get(f"{BASE}/assets/{asset_id}", headers=_headers())
    ar.raise_for_status()
    body = ar.json()
    asset = body.get("asset") or body
    url = asset.get("url")
    if not url:
        raise RuntimeError(f"Scenario asset {asset_id} has no url field: {body}")
    return url
