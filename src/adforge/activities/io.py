"""Activities: small disk-IO helpers used by workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from temporalio import activity

from adforge.utils import extract_first_frame


@activity.defn(name="write_json")
async def write_json(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(args["data"], indent=2, ensure_ascii=False))
    return str(path)


@activity.defn(name="extract_seed_frame")
async def extract_seed_frame(args: dict[str, Any]) -> str:
    """Pull the first interesting frame of the gameplay video as a JPEG.

    Used by creative_forge's grounded-i2v config so Scenario Seedance can do
    image-to-video from the actual game's pixels (not a text-prompt
    hallucination). Returns the absolute output path.
    """
    video = args["video_path"]
    out = args["out_path"]
    at = float(args.get("at_seconds", 3.0))
    return str(extract_first_frame(video, out, at_seconds=at))


@activity.defn(name="list_assets")
async def list_assets(asset_dir: str) -> list[str]:
    """Enumerate the files in a project's assets/ folder.

    Returns sorted relative filenames (e.g. "Background.png", "Music.ogg").
    Used by creative_forge to make the brief + prompt aware of what visual
    and audio assets the team can lean on for the final creative.
    """
    p = Path(asset_dir)
    if not p.is_dir():
        return []
    return sorted(
        f.name
        for f in p.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )
