"""Projects — the named, reusable input bundles that pipelines consume.

A project is the kitchen-sink folder for everything we know about one game.

    projects/<id>/
      project.json    # required — see schema below
      video.mp4       # optional — gameplay video (gitignored)
      assets/         # optional — images / audio to inline in playables
      README.md       # optional — human notes about the kit

`project.json` schema (only `name` is required):

    {
      "name":        "Castle Clashers",
      "genre":       "tower-defense",
      "description": "Tap-to-defend tower-defense hybrid…",
      "category_id": "7012",
      "country":     "US",
      "app_id":      "1234567890",
      "store_urls":  { "ios": "...", "android": "..." },
      "notes":       "human-only notes, never sent to AI"
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from adforge.config import PROJECTS_DIR


class Project(BaseModel):
    id: str

    name: str
    genre: str | None = None
    description: str | None = None
    notes: str | None = None

    category_id: str = "7012"
    country: str = "US"
    app_id: str | None = None
    store_urls: dict[str, str] = Field(default_factory=dict)

    project_dir: str
    video_path: str | None = None
    asset_dir: str | None = None
    playable_path: str | None = None

    def has_video(self) -> bool:
        return self.video_path is not None

    def has_assets(self) -> bool:
        return self.asset_dir is not None

    def has_playable(self) -> bool:
        return self.playable_path is not None


def list_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))


def load(project_id: str) -> Project:
    """Resolve a project by id, reading project.json + probing for video/assets."""
    pdir = PROJECTS_DIR / project_id
    if not pdir.is_dir():
        raise FileNotFoundError(
            f"project '{project_id}' not found at {pdir}. "
            f"Available: {', '.join(list_projects()) or '<none>'}"
        )

    meta_path = pdir / "project.json"
    if not meta_path.is_file():
        raise FileNotFoundError(
            f"missing {meta_path}. Each project needs a project.json — see projects/README.md."
        )
    meta = json.loads(meta_path.read_text())

    video = pdir / "video.mp4"
    assets = pdir / "assets"
    playable = pdir / "playable.html"
    return Project(
        id=project_id,
        name=meta.get("name", project_id),
        genre=meta.get("genre"),
        description=meta.get("description"),
        notes=meta.get("notes"),
        category_id=str(meta.get("category_id", "7012")),
        country=meta.get("country", "US"),
        app_id=meta.get("app_id"),
        store_urls=meta.get("store_urls", {}),
        project_dir=str(pdir),
        video_path=str(video) if video.is_file() else None,
        asset_dir=str(assets) if assets.is_dir() else None,
        playable_path=str(playable) if playable.is_file() else None,
    )
