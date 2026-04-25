"""Temporal workflows + the pipeline catalog.

A **pipeline** is a recipe that turns a project (input material) into a run
(folder of artefacts). The PIPELINES registry below is the single source of
truth — the CLI, the API, and the UI all read from it.

Adding a new pipeline = one PipelineSpec entry + the workflow class. Iterating
on an existing one = a new PipelineConfig preset and a branch in the relevant
activity on `inp.config_id`. That's the whole forge.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from adforge.pipelines.creative_forge import CreativeForge, CreativeForgeInput
from adforge.pipelines.playable_forge import PlayableForge, PlayableForgeInput


class PipelineConfig(BaseModel):
    """A named preset of pipeline knobs. Same workflow, different behavior.

    `params` is a dict of overrides merged into the workflow input — model
    choice, prompt template, sample size, anything pipeline-specific.
    """
    id: str
    name: str
    description: str
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineInput(BaseModel):
    """One input the pipeline expects to find in a project folder.

    Used by the UI (to show what a pipeline needs) and by the auto-ingest
    activity (to map random files in projects/<id>/ into the right slot).
    """
    id: str                 # "video", "assets", "metadata"
    kind: str               # "file" | "dir" | "metadata"
    description: str        # human-readable
    required: bool = True


class PipelineSpec(BaseModel):
    id: str                              # workflow name + CLI subcommand
    name: str                            # display name
    description: str                     # one-sentence "what it does"
    inputs: list[PipelineInput] = []     # what the pipeline consumes from a project
    outputs: list[str] = []              # canonical artifact filenames
    cli: str = ""                        # canonical CLI invocation (with <id> placeholder)
    configs: list[PipelineConfig] = []   # named presets


PIPELINES: list[PipelineSpec] = [
    PipelineSpec(
        id="creative_forge",
        name="Video Ad",
        description="Project → web research + market insights → storyboard → AI-generated video ad creative.",
        inputs=[
            PipelineInput(id="metadata", kind="metadata", description="Game name, genre, category — read from project.json."),
        ],
        outputs=["brief.md", "scenario_prompt.txt", "patterns.json", "top_creatives.json", "top_advertisers.json"],
        cli="adforge run creative --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Default",
                description="Mistral for labeling, Gemini for analysis, Scenario MCP for the static creative.",
            ),
            PipelineConfig(
                id="render-images",
                name="With Scenario images [BLOCKED]",
                description="Calls Scenario txt2img after the brief. BLOCKED on this account: requires a `modelId` and the account has zero models registered (GET /v1/models returns []). Use the Scenario MCP via `scenario-generate` until models are configured in the Scenario dashboard.",
                params={"render_with_scenario_http": True, "render_mode": "image", "num_images": 3},
            ),
            PipelineConfig(
                id="render-video",
                name="With Veo video",
                description="Pipeline goes all the way — after the brief, calls Veo 3 (Gemini API) text-to-video to render a 9:16 vertical clip into runs/<id>/. The brief's Scenario prompt becomes an actual moving asset. Costs ~$0.40–2.00 per clip; keep num_videos at 1 while iterating.",
                params={"render_with_scenario_http": True, "render_mode": "video", "num_images": 1, "video_duration_s": 8},
            ),
        ],
    ),
    PipelineSpec(
        id="playable_forge",
        name="Playable",
        description="Gameplay video + asset kit → single-file HTML playable + parameter variants.",
        inputs=[
            PipelineInput(id="video",  kind="file", description="Gameplay capture (mp4/mov). The pipeline analyzes this with Gemini."),
            PipelineInput(id="assets", kind="dir",  description="Optional folder of images / audio to inline.", required=False),
        ],
        outputs=["playable.html", "playable__*.html"],
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
