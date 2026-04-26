"""Temporal workflows + the pipeline catalog.

A **pipeline** is a recipe that turns a project (input material) into a run
(folder of artefacts). The PIPELINES registry below is the single source of
truth — the CLI, the API, and the UI all read from it.

Two pipelines ship today:

  - **creative_forge**  →  Video Ad. Project → Sensor Tower market intel →
                           Claude Haiku labeled patterns → Scenario Seedance
                           2.0 video clip (9:16 / 720p / audio).
  - **playable_forge**  →  Playable HTML. Project's gameplay video → Gemini
                           analysis → Claude Sonnet authors a tailored loop
                           body → variants.

Iterating a pipeline = ship a new code revision in-place (the workflow file
+ activity files own the implementation). `PipelineConfig` presets are for
small knob tweaks within the same code path (model id, sample size, duration).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from adforge.pipelines.creative_forge import CreativeForge, CreativeForgeInput
from adforge.pipelines.market_intel import MarketIntel, MarketIntelInput
from adforge.pipelines.playable_forge import PlayableForge, PlayableForgeInput


class PipelineConfig(BaseModel):
    """A named preset of pipeline knobs. Same workflow, different parameters."""
    id: str
    name: str
    description: str
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineInput(BaseModel):
    id: str                 # "video", "assets", "metadata"
    kind: str               # "file" | "dir" | "metadata"
    description: str
    required: bool = True


class PipelineSpec(BaseModel):
    id: str
    name: str
    description: str
    output_kind: str = "asset"           # "video" | "playable" | "asset" — for UI grouping
    inputs: list[PipelineInput] = []
    outputs: list[str] = []
    cli: str = ""
    configs: list[PipelineConfig] = []


PIPELINES: list[PipelineSpec] = [
    PipelineSpec(
        id="creative_forge",
        name="Video Ad",
        description=(
            "Sensor Tower market intel → Claude Haiku labels working creatives "
            "(top advertisers × longevity) → optional Gemini analysis of the "
            "project's gameplay video grounds the brief in the actual game → "
            "Scenario Seedance 2.0 renders a 9:16 / 720p / audio-on video clip."
        ),
        output_kind="video",
        inputs=[
            PipelineInput(id="metadata", kind="metadata",
                description="Game name, genre, category — read from project.json."),
            PipelineInput(id="video", kind="file",
                description="Optional. Gameplay video.mp4 — when present, Gemini analyzes it and the brief grounds the concept in the actual game (mechanic, palette, juice, audio cues).",
                required=False),
            PipelineInput(id="assets", kind="dir",
                description="Optional. assets/ folder — listed in the brief by filename and referenced in the Scenario prompt.",
                required=False),
        ],
        outputs=["brief.md", "scenario_prompt.txt", "patterns.json", "top_creatives.json", "top_advertisers.json", "gameplay_analysis.json", "creative_*.mp4"],
        cli="adforge run creative --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Seedance 2.0",
                description="Best quality. 6s, 9:16, 720p, native audio.",
                params={
                    "seedance_model_id": "model_bytedance-seedance-2-0",
                    "video_duration_s": 6,
                    "num_videos": 1,
                },
            ),
            PipelineConfig(
                id="fast",
                name="Seedance 2.0 Fast",
                description="Cheaper iteration tier — same I/O, faster + lower cost. Good for sweeping prompt variants.",
                params={
                    "seedance_model_id": "model_bytedance-seedance-2-0-fast",
                    "video_duration_s": 6,
                    "num_videos": 1,
                },
            ),
            PipelineConfig(
                id="grounded",
                name="Grounded (game-specific prompt, 10s)",
                description=(
                    "Hypothesis: the disconnected-from-the-game complaint comes from "
                    "the prompt leading with meta-instructions (9:16, max-6-words) "
                    "and ending with weak generic style notes. Instead, lead with a "
                    "specific 'visual signature' built from Gemini's gameplay "
                    "analysis (exact scene, art style, palette in hex, named juice "
                    "cues), drop the literal game name (Seedance can't render text "
                    "reliably and we just got 'Spelletaire' instead of 'Spellitaire'), "
                    "and bump duration to 10s for proper TikTok-ad pacing."
                ),
                params={
                    "seedance_model_id": "model_bytedance-seedance-2-0-fast",
                    "video_duration_s": 10,
                    "num_videos": 1,
                    "prompt_style": "grounded",
                },
            ),
            PipelineConfig(
                id="grounded-i2v-v2",
                name="Grounded i2v v2 (genre-filtered + dynamic hooks)",
                description=(
                    "Hypothesis: the v1 i2v config still produces wrong-genre market "
                    "intel (Mini Slayer got anime horse-racing ads, Spellitaire got "
                    "language tutoring apps). v2 uses genre-aware SensorTower category "
                    "mapping so market patterns are from the right genre. Also: hook "
                    "blueprints are now game-specific (no more 'wrecked castle' for "
                    "every game), audio files filtered from visual props list, and "
                    "palette contradictions resolved."
                ),
                params={
                    "seedance_model_id": "model_bytedance-seedance-2-0",
                    "video_duration_s": 10,
                    "num_videos": 1,
                    "prompt_style": "grounded",
                },
            ),
            PipelineConfig(
                id="grounded-i2v",
                name="Grounded i2v (seed from game footage)",
                description=(
                    "Hypothesis: 11 of 13 open feedback items are 'the video is "
                    "disconnected from the game' — text prompts can't hold a "
                    "specific game's identity (Seedance hallucinated a dragon for "
                    "Mini Slayer, misspelled SPELLITAIRE, drew no match-3 grid). "
                    "Fix at INPUT time, not in prose: extract the gameplay "
                    "video's first frame and pass it to Seedance as the i2v seed "
                    "image. The animation then starts from real game pixels — "
                    "character, palette, UI all pinned to ground truth. The text "
                    "prompt becomes a beat-map / motion direction layered on top "
                    "instead of carrying the visual identity alone. 10s duration "
                    "for TikTok pacing."
                ),
                params={
                    "seedance_model_id": "model_bytedance-seedance-2-0",
                    "video_duration_s": 10,
                    "num_videos": 1,
                    "prompt_style": "grounded",
                },
            ),
        ],
    ),
    PipelineSpec(
        id="playable_forge",
        name="Playable",
        description=(
            "Gemini analyzes the gameplay video → Claude Sonnet authors a "
            "tailored loop body for the analyzed mechanic → assets are inlined "
            "→ parameter variants are emitted."
        ),
        output_kind="playable",
        inputs=[
            PipelineInput(id="video",  kind="file", description="Gameplay capture (mp4/mov)."),
            PipelineInput(id="assets", kind="dir",  description="Optional folder of images / audio to inline.", required=False),
        ],
        outputs=["playable.html", "playable__*.html"],
        cli="adforge run playable --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Claude Sonnet",
                description="Sonnet authors the loop body. Validation-gated; falls back to baseline build on failure.",
            ),
            PipelineConfig(
                id="claude-opus-v2",
                name="Claude Opus v2 + real asset inlining",
                description=(
                    "Hypothesis: v1 opus config generates Image() calls with relative "
                    "paths but inline_html_assets only processes HTML tags, not JS. "
                    "v2 fixes: (1) JS-level asset inlining rewrites img.src and "
                    "new Audio() to base64 data URLs, (2) resolves paths from project "
                    "assets/ not run dir, (3) title tag uses actual game name. "
                    "Should produce self-contained playables with real game art."
                ),
                params={"playable_model": "opus", "asset_aware": True, "relax_validation": True},
            ),
            PipelineConfig(
                id="claude-opus",
                name="Claude Opus + asset-aware",
                description=(
                    "Hypothesis: black/empty playables come from (a) the validation gate "
                    "rejecting Claude's output for missing `</script>` and silently falling "
                    "back to the asset-blind baseline tap-target, and (b) when Claude does "
                    "ship code, it doesn't know what visual assets exist so it renders "
                    "geometry on a canvas matching the bg colour (mini_slayer palette[0]=#000 "
                    "→ black-on-black). Fix: switch to Claude Opus 4.7, inline the project's "
                    "asset filenames + a short description of each into the prompt so Claude "
                    "explicitly draws sprites at known positions, and auto-wrap missing "
                    "<script> tags instead of falling back."
                ),
                params={"playable_model": "opus", "asset_aware": True, "relax_validation": True},
            ),
        ],
    ),
    PipelineSpec(
        id="market_intel",
        name="Market Intelligence",
        description=(
            "Project (video + assets + GDD) → competitive analysis vs SensorTower "
            "→ positioning, storyboards, slide deck. Uses Claude (vision + text); "
            "no Gemini/Veo."
        ),
        output_kind="asset",
        inputs=[
            PipelineInput(id="metadata", kind="metadata",
                description="Game name + description — read from project.json."),
            PipelineInput(id="video", kind="file",
                description="Optional gameplay video; frames extracted locally with imageio.",
                required=False),
            PipelineInput(id="assets", kind="dir",
                description="Optional folder of art/audio.", required=False),
        ],
        outputs=["deck.html", "genre.json", "analysis.json", "top_advertisers.json",
                 "top_creatives.json", "frames/*.png"],
        cli="adforge run intel --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Default",
                description=(
                    "Local frame extraction (imageio) → Claude vision genre inference "
                    "→ SensorTower → Claude analysis + storyboards → HTML slide deck. "
                    "No Gemini."
                ),
            ),
            PipelineConfig(
                id="intel-presentation-v2",
                name="Executive Deck (v2)",
                description=(
                    "Hypothesis: an executive 16:9 deck themed to the project's own "
                    "palette, with genre-targeted SensorTower competitors and visual "
                    "storyboard frames, will be far more useful than a text-heavy report."
                ),
            ),
            PipelineConfig(
                id="intel-presentation-v3",
                name="Executive Deck (v3)",
                description=(
                    "Hypothesis: short copy must be Claude-generated, not truncated; "
                    "storyboards need full beats with playbook-grounded SVG sketches; "
                    "competitors need real data points (rating count, release date)."
                ),
            ),
            PipelineConfig(
                id="intel-presentation-v5",
                name="Executive Deck (v5)",
                description=(
                    "Hypothesis: v5 widens the genre-search net, computes a Scale tier "
                    "(Mega Hit / Hit / Solid / Niche) from rating count, and attaches "
                    "Share-of-Voice from top_advertisers for spend context."
                ),
            ),
            PipelineConfig(
                id="intel-presentation-v6",
                name="Executive Deck (v6)",
                description=(
                    "Hypothesis: the deck becomes more useful when slide 3 filters out "
                    "Long Tail apps and studies Solid+ genre competitors through an "
                    "advertising lens."
                ),
            ),
            PipelineConfig(
                id="intel-presentation-v7",
                name="Executive Deck (v7)",
                description=(
                    "Hypothesis: the deck reads smarter when challenges and opportunities "
                    "are non-overlapping strategic tensions, competitor cards ranked by "
                    "creative activity, and theme chooses a contrast-safe background."
                ),
            ),
        ],
    ),
    PipelineSpec(
        id="playable_variations",
        name="Playable Variations",
        description=(
            "Takes an existing playable HTML as input, parses its CONFIG block "
            "(or injects CSS-level tweaks for vsdk-based playables), and generates "
            "smart variations — colors, speeds, difficulty, visual effects. "
            "Pure agentic pipeline (no Temporal). Run from Claude Code."
        ),
        output_kind="playable",
        inputs=[
            PipelineInput(id="playable", kind="file",
                description="Existing playable.html (from project dir or a previous run)."),
            PipelineInput(id="metadata", kind="metadata",
                description="Game name, genre — from project.json.", required=False),
        ],
        outputs=["playable__*.html", "variations_manifest.json"],
        cli="uv run python /tmp/playable_variations.py --project <id>",
        configs=[
            PipelineConfig(
                id="default",
                name="Smart Variations",
                description="Claude analyzes the CONFIG block + game context, proposes 5-8 coherent variations (palette, difficulty, pacing, visual effects).",
            ),
            PipelineConfig(
                id="aggressive",
                name="Aggressive Variations",
                description="Wider parameter sweeps — extreme difficulty, wild palettes, very short/long sessions.",
            ),
        ],
    ),
]


WORKFLOWS = [PlayableForge, CreativeForge, MarketIntel]


def find_pipeline(pipeline_id: str) -> PipelineSpec | None:
    return next((p for p in PIPELINES if p.id == pipeline_id), None)


def find_config(pipeline_id: str, config_id: str) -> PipelineConfig | None:
    spec = find_pipeline(pipeline_id)
    if not spec:
        return None
    return next((c for c in spec.configs if c.id == config_id), None)
