"""Temporal workflows + the pipeline catalog.

  creative_forge — project → market insights → storyboard → video ad creative
  playable_forge — project (with video) → single-file HTML playable + variants

The PIPELINES registry below is the single source of truth for what's
available in the forge. The CLI, the API, and the UI all read from it.
Adding a new pipeline is one PipelineSpec entry plus the workflow class.

Each pipeline has named CONFIG presets — different model choices, prompts,
or code paths to A/B as we tune. Pick one with `--config <id>` (CLI) or via
the picker on the project page (UI). Configs are how we iterate scientifically.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from adforge.pipelines.creative_forge import CreativeForge, CreativeForgeInput
from adforge.pipelines.playable_forge import PlayableForge, PlayableForgeInput


class PipelineConfig(BaseModel):
    """A named preset of pipeline knobs. Same workflow, different behavior.

    `params` is a dict of overrides merged into the workflow input — model
    choice, prompt template, sample size, anything pipeline-specific.
    """
    id: str                              # short id, e.g. "default", "claude-prose", "fast"
    name: str                            # display name
    description: str                     # one-line summary of what makes this config different
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineSpec(BaseModel):
    id: str                              # workflow name + CLI subcommand
    name: str                            # display name
    glyph: str                           # one-char visual marker (UI uses this everywhere)
    tagline: str                         # one-sentence "what it does"
    track: Literal["track-2", "track-3"]
    needs: list[str] = []                # project requirements: "video", "assets"
    produces: list[str] = []             # canonical artifact filenames (post-tuning)
    cli: str = ""                        # canonical CLI invocation (with <id> placeholder)
    configs: list[PipelineConfig] = []   # named presets


PIPELINES: list[PipelineSpec] = [
    PipelineSpec(
        id="creative_forge",
        name="Video Ad",
        glyph="✦",
        tagline="Project → web research + market insights → storyboard → AI-generated video ad.",
        track="track-3",
        needs=[],
        produces=["brief.md", "scenario_prompt.txt", "patterns.json", "top_creatives.json", "top_advertisers.json"],
        cli="adforge run creative --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Default",
                description="Mistral for labeling, Gemini for analysis, Scenario MCP for the static creative.",
            ),
            # Drop in more presets here as you iterate — different models, prompts, or code paths.
            # PipelineConfig(id="claude-prose", name="Claude Prose Brief",
            #                description="Use Claude for the brief writing step (richer prose).",
            #                params={"brief_writer": "claude"}),
        ],
    ),
    PipelineSpec(
        id="playable_forge",
        name="Playable",
        glyph="▲",
        tagline="Gameplay video + asset kit → single-file HTML playable + parameter variants.",
        track="track-2",
        needs=["video"],
        produces=["playable.html", "playable__*.html"],
        cli="adforge run playable --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Default",
                description="Gemini video analysis → CONFIG-block injection into template → 4 baseline variants.",
            ),
        ],
    ),
]


WORKFLOWS = [PlayableForge, CreativeForge]


def find_pipeline(pipeline_id: str) -> PipelineSpec | None:
    return next((p for p in PIPELINES if p.id == pipeline_id), None)


def find_config(pipeline_id: str, config_id: str) -> PipelineConfig | None:
    spec = find_pipeline(pipeline_id)
    if not spec:
        return None
    return next((c for c in spec.configs if c.id == config_id), None)
