"""Targets — the named, reusable input bundles that pipelines consume.

A target is the kitchen-sink folder for everything we know about one game.

    targets/<id>/
      target.json     # required — see schema below
      video.mp4       # optional — gameplay video (gitignored)
      assets/         # optional — images / audio to inline in playables
      README.md       # optional — human notes about the kit

`target.json` schema (everything but `name` is optional):

    {
      "name":        "Castle Clashers",          // display name
      "genre":       "tower-defense",            // free-form, fed to LLM context
      "description": "Tap-to-defend tower-defense hybrid…",   // long-form context
      "category_id": "7012",                     // SensorTower category (defaults: 7012 puzzle)
      "country":     "US",                       // primary market
      "app_id":      "1234567890",               // SensorTower / store id
      "store_urls":  { "ios": "...", "android": "..." },
      "notes":       "human-only notes, never sent to AI"
    }

Pipelines never touch the filesystem layout. They take a `target_id` plus
already-resolved paths via `Target.video_path` / `Target.asset_dir` plus all
the metadata fields above. This keeps workflows pure.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from adforge.config import TARGETS_DIR


class Target(BaseModel):
    id: str                                # folder name == id

    # Identity
    name: str                              # display name, e.g. "Castle Clashers"
    genre: str | None = None               # "tower-defense", "match-3", …
    description: str | None = None         # long-form, fed to LLM
    notes: str | None = None               # human-only, never sent to LLM

    # Market metadata
    category_id: str = "7012"              # SensorTower category (default: iOS Puzzle)
    country: str = "US"                    # primary market
    app_id: str | None = None              # store id
    store_urls: dict[str, str] = Field(default_factory=dict)

    # Resolved paths
    target_dir: str
    video_path: str | None = None
    asset_dir: str | None = None

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
        genre=meta.get("genre"),
        description=meta.get("description"),
        notes=meta.get("notes"),
        category_id=str(meta.get("category_id", "7012")),
        country=meta.get("country", "US"),
        app_id=meta.get("app_id"),
        store_urls=meta.get("store_urls", {}),
        target_dir=str(tdir),
        video_path=str(video) if video.is_file() else None,
        asset_dir=str(assets) if assets.is_dir() else None,
    )
