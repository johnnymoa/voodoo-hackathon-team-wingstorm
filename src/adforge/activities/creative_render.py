"""Activity: render the final ad asset from a creative brief.

Two modes:
- `image` → Scenario HTTP txt2img (limited; needs models registered in your Scenario account).
- `video` → Veo via the google-genai SDK using GEMINI_API_KEY (works out of the box).

The Scenario MCP path (interactive, via Claude Code) is documented in the
`scenario-generate` skill — use it for richer image/img2vid flows when a human
is in the loop. This activity is the headless path inside the Temporal worker.
"""

from __future__ import annotations

from pathlib import Path

from temporalio import activity

from adforge.activities.types import ScenarioRenderInput, ScenarioRenderResult
from adforge.connectors import gemini, scenario


@activity.defn(name="render_scenario_creative")
async def render_scenario_creative(inp: ScenarioRenderInput) -> ScenarioRenderResult:
    prompt = Path(inp.prompt_path).read_text()

    if inp.mode == "video":
        activity.heartbeat("submitting Veo (Gemini) text-to-video job")
        videos = gemini.generate_videos(
            prompt,
            aspect_ratio="9:16",
            num_videos=max(1, inp.num_images),
        )
        paths = gemini.save_videos(videos, inp.out_dir, prefix="creative")
        return ScenarioRenderResult(video_paths=[str(p) for p in paths])

    activity.heartbeat("submitting Scenario txt2img job")
    images = scenario.generate_image(
        prompt,
        width=inp.width,
        height=inp.height,
        num_images=inp.num_images,
    )
    paths = scenario.save_images(images, inp.out_dir, prefix="creative")
    return ScenarioRenderResult(image_paths=[str(p) for p in paths])
