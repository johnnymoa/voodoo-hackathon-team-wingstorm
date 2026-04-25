"""Gemini connector — text + video understanding."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from adforge.config import settings
from adforge.utils import strip_json_fences

DEFAULT_MODEL = "gemini-2.0-flash-exp"
LARGE_MODEL = "gemini-2.5-pro"


def _client():
    from google import genai

    return genai.Client(api_key=settings().gemini_api_key)


def list_models() -> list[str]:
    return [m.name for m in _client().models.list()]


def text(prompt: str, *, model: str = DEFAULT_MODEL) -> str:
    resp = _client().models.generate_content(model=model, contents=prompt)
    return resp.text or ""


def text_json(prompt: str, *, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    raw = text(
        prompt + "\n\nReturn ONLY a valid JSON object — no markdown fences, no commentary.",
        model=model,
    )
    return json.loads(strip_json_fences(raw))


def analyze_video(
    video_path: str | Path,
    *,
    prompt: str,
    model: str = LARGE_MODEL,
    poll_interval_s: float = 2.0,
    timeout_s: float = 600.0,
) -> str:
    c = _client()
    p = Path(video_path)
    if not p.exists():
        raise FileNotFoundError(p)

    print(f"[gemini] uploading {p.name} ({p.stat().st_size / 1e6:.1f} MB)…", file=sys.stderr)
    file = c.files.upload(file=str(p))

    deadline = time.time() + timeout_s
    while file.state.name == "PROCESSING":
        if time.time() > deadline:
            raise TimeoutError(f"Gemini upload still processing after {timeout_s}s")
        time.sleep(poll_interval_s)
        file = c.files.get(name=file.name)

    if file.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini upload failed: state={file.state.name}")

    resp = c.models.generate_content(model=model, contents=[file, prompt])
    return resp.text or ""


def analyze_video_json(
    video_path: str | Path,
    *,
    prompt: str,
    schema_hint: str | None = None,
    model: str = LARGE_MODEL,
) -> dict[str, Any]:
    full = prompt + "\n\nReturn ONLY a valid JSON object — no markdown fences, no commentary."
    if schema_hint:
        full += f"\n\nThe JSON must conform to this shape:\n{schema_hint}"
    raw = analyze_video(video_path, prompt=full, model=model)
    return json.loads(strip_json_fences(raw))


# ───── Veo (text-to-video) ────────────────────────────────────────────────
# Veo is reachable via the same GEMINI_API_KEY through the google-genai SDK's
# `models.generate_videos` endpoint. Returns a long-running operation; poll until
# done, then download the video bytes via the Files API on the operation's
# response.

VEO_MODEL = "veo-3.0-generate-001"           # current GA Veo (1080p, 8s default)
VEO_FAST_MODEL = "veo-3.0-fast-generate-001"
VEO_PREVIEW_MODEL = "veo-3.1-generate-preview"


def generate_videos(
    prompt: str,
    *,
    model: str = VEO_MODEL,
    aspect_ratio: str = "9:16",
    num_videos: int = 1,
    poll_interval_s: float = 5.0,
    timeout_s: float = 600.0,
) -> list[bytes]:
    """Veo text-to-video. Returns a list of mp4 bytes (one per `num_videos`).

    Raises on timeout / failure. Costs roughly $0.10–0.50 per second of video
    depending on model — keep `num_videos` small while iterating.
    """
    c = _client()

    op = c.models.generate_videos(
        model=model,
        prompt=prompt,
        config={
            "aspect_ratio": aspect_ratio,
            "number_of_videos": num_videos,
        },
    )

    deadline = time.time() + timeout_s
    while not op.done:
        if time.time() > deadline:
            raise TimeoutError(f"Veo job still running after {timeout_s}s")
        time.sleep(poll_interval_s)
        op = c.operations.get(op)

    if op.error:
        raise RuntimeError(f"Veo job failed: {op.error}")

    generated = (op.response or op.result or {}).generated_videos or []
    if not generated:
        raise RuntimeError(f"Veo returned no videos in response: {op}")

    out: list[bytes] = []
    for g in generated:
        f = g.video
        # The SDK's File can be downloaded via .save() or via files.download
        c.files.download(file=f)         # populates f.video_bytes in some SDK versions
        if getattr(f, "video_bytes", None):
            out.append(f.video_bytes)
        else:
            # Fallback: write to a temp path then read
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                f.save(tmp.name)
                out.append(Path(tmp.name).read_bytes())
    return out


def save_videos(videos: list[bytes], out_dir: str | Path, prefix: str = "veo") -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, b in enumerate(videos, 1):
        p = out / f"{prefix}_{i:02d}.mp4"
        p.write_bytes(b)
        paths.append(p)
    return paths
