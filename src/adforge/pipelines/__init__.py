"""Temporal workflows. Two atoms + one merged.

  creative_forge — target game     → market-informed brief + Scenario prompt
  playable_forge — gameplay video  → interactive HTML playable + variants
  full_forge     — both, chained   → market-informed playable + brief + creative

The PIPELINES registry below is the single source of truth for what's
available in the forge. The CLI, the API, and the UI all read from it. Adding
a new pipeline is one PipelineSpec entry plus the workflow class.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from adforge.pipelines.creative_forge import CreativeForge, CreativeForgeInput
from adforge.pipelines.full_forge import FullForge, FullForgeInput
from adforge.pipelines.playable_forge import PlayableForge, PlayableForgeInput


class PipelineSpec(BaseModel):
    id: str                              # workflow name + CLI subcommand
    name: str                            # display name
    glyph: str                           # one-char visual marker (UI uses this everywhere)
    tagline: str                         # one-sentence "what it does"
    track: Literal["track-2", "track-3", "merged"]
    needs: list[str] = []                # target requirements: "video", "assets"
    produces: list[str] = []             # canonical artifact filenames
    cli: str = ""                        # the canonical CLI invocation


PIPELINES: list[PipelineSpec] = [
    PipelineSpec(
        id="creative_forge",
        name="Creative Intelligence",
        glyph="✦",
        tagline="Market data → ranked patterns → tailored creative brief + Scenario prompt.",
        track="track-3",
        needs=[],
        produces=["brief.md", "scenario_prompt.txt", "patterns.json", "top_creatives.json", "top_advertisers.json", "target.json"],
        cli="adforge run creative --target <id>",
    ),
    PipelineSpec(
        id="playable_forge",
        name="Playable Builder",
        glyph="▲",
        tagline="Gameplay video + asset kit → single-file HTML playable + parameter variants.",
        track="track-2",
        needs=["video"],
        produces=["playable.html", "playable__*.html"],
        cli="adforge run playable --target <id>",
    ),
    PipelineSpec(
        id="full_forge",
        name="Full Forge",
        glyph="◆",
        tagline="Both pipelines chained — the playable is informed by what's winning in market.",
        track="merged",
        needs=["video"],
        produces=["creative/*", "playable/*"],
        cli="adforge run full --target <id>",
    ),
]


WORKFLOWS = [PlayableForge, CreativeForge, FullForge]


def find_pipeline(pipeline_id: str) -> PipelineSpec | None:
    return next((p for p in PIPELINES if p.id == pipeline_id), None)
