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
