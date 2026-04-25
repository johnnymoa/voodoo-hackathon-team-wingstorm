"""Targets — the named, reusable input bundles that pipelines consume.

A target is a folder under `targets/<id>/` containing:

    targets/<id>/
      target.json     # {name, app_id, store_urls, notes}    (required)
      video.mp4       # gameplay video                        (optional, gitignored)
      assets/         # images / audio to inline in playables (optional)
      README.md       # human notes about the kit             (optional)

Pipelines never touch the filesystem layout directly. They take a `target_id`
plus already-resolved paths via `Target.video_path` / `Target.asset_dir`.
This keeps workflows pure and the convention pinned in one file.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from adforge.config import TARGETS_DIR


class Target(BaseModel):
    id: str                                # folder name == id
    name: str                              # display name, e.g. "Castle Clashers"
    app_id: str | None = None              # SensorTower / store id (optional)
    store_urls: dict[str, str] = {}        # {"ios": "...", "android": "..."}
    notes: str | None = None

    target_dir: str                        # absolute path to targets/<id>/
    video_path: str | None = None          # absolute, if video.mp4 exists
    asset_dir: str | None = None           # absolute, if assets/ exists

    def has_video(self) -> bool:
        return self.video_path is not None

    def has_assets(self) -> bool:
        return self.asset_dir is not None


def list_targets() -> list[str]:
    """All target ids on disk (alphabetical)."""
    if not TARGETS_DIR.exists():
        return []
    return sorted(p.name for p in TARGETS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def load(target_id: str) -> Target:
    """Resolve a target by id, reading target.json + probing for video/assets.

    Raises FileNotFoundError if the target folder or target.json is missing.
    """
    tdir = TARGETS_DIR / target_id
    if not tdir.is_dir():
        raise FileNotFoundError(
            f"target '{target_id}' not found at {tdir}. "
            f"Available: {', '.join(list_targets()) or '<none>'}"
        )

    meta_path = tdir / "target.json"
    if not meta_path.is_file():
        raise FileNotFoundError(
            f"missing {meta_path}. Each target needs a target.json — see targets/README.md."
        )
    meta = json.loads(meta_path.read_text())

    video = tdir / "video.mp4"
    assets = tdir / "assets"
    return Target(
        id=target_id,
        name=meta.get("name", target_id),
        app_id=meta.get("app_id"),
        store_urls=meta.get("store_urls", {}),
        notes=meta.get("notes"),
        target_dir=str(tdir),
        video_path=str(video) if video.is_file() else None,
        asset_dir=str(assets) if assets.is_dir() else None,
    )
