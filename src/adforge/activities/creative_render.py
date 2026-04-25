"""Activity: render images via the Scenario HTTP API.

Primary path for Scenario is the MCP inside Claude Code. This activity is the
headless fallback used when running creative_forge end-to-end through Temporal
without a human in the loop.
"""

from __future__ import annotations

from pathlib import Path

from temporalio import activity

from adforge.activities.types import ScenarioRenderInput, ScenarioRenderResult
from adforge.connectors import scenario


@activity.defn(name="render_scenario_creative")
async def render_scenario_creative(inp: ScenarioRenderInput) -> ScenarioRenderResult:
    prompt = Path(inp.prompt_path).read_text()
    activity.heartbeat("submitting Scenario job")
    images = scenario.generate_image(
        prompt,
        width=inp.width,
        height=inp.height,
        num_images=inp.num_images,
    )
    paths = scenario.save_images(images, inp.out_dir, prefix="creative")
    return ScenarioRenderResult(image_paths=[str(p) for p in paths])
