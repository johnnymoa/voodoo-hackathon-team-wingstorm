"""Small cross-pipeline helpers."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any


def slug(s: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s[:max_len] or "untitled"


def run_id(prefix: str = "run") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}"


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return p


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def file_to_data_url(path: str | Path) -> str:
    p = Path(path)
    mime, _ = mimetypes.guess_type(p.name)
    if not mime:
        mime = "application/octet-stream"
    b = p.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"


def file_size_mb(path: str | Path) -> float:
    return Path(path).stat().st_size / 1_000_000


def assert_under_size(path: str | Path, max_mb: float = 5.0) -> None:
    size = file_size_mb(path)
    if size > max_mb:
        raise RuntimeError(f"{path} is {size:.2f} MB — over the {max_mb} MB ad-network limit.")


def strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip("` \n")
    return raw
