"""Activity: render the final video ad with Scenario Seedance 2.0.

Calls Scenario's unified `/v1/generate/custom/{modelId}` endpoint with
Seedance 2.0. 9:16 vertical, 720p, native audio, 6-second default.

**Idempotency.** Seedance is non-deterministic (no fixed seed → different
video every call) AND expensive. Temporal will retry this activity on
heartbeat timeouts, and a naive retry overwrites the previous mp4 with a
brand new one — that's why the same run's video appeared to "change every
time you reloaded the page." We now skip the API call if the expected
output files already exist on disk; the activity becomes a no-op for
retries, the first-attempt video is preserved.

**Image-to-video grounding.** When `seed_image_path` is set on the input
(grounded-i2v config), we encode the image as a base64 data URL and hand
it to Seedance as the i2v seed. This is the single biggest lever for
"video is disconnected from the actual game" feedback — text prompts
hallucinate, but a seed frame from the real gameplay capture pins
character, palette, and environment to ground truth.
"""

from __future__ import annotations

from pathlib import Path

from temporalio import activity

from adforge.activities.types import ScenarioRenderInput, ScenarioRenderResult
from adforge.connectors import scenario
from adforge.utils import file_to_data_url


def _expected_output_paths(out_dir: str, num: int) -> list[Path]:
    base = Path(out_dir)
    return [base / f"creative_{i:02d}.mp4" for i in range(1, max(1, num) + 1)]


@activity.defn(name="render_seedance")
async def render_seedance(inp: ScenarioRenderInput) -> ScenarioRenderResult:
    out_dir = inp.out_dir
    n = max(1, inp.num_images)
    expected = _expected_output_paths(out_dir, n)

    # Idempotent retry: if the activity already wrote all expected mp4s,
    # don't re-submit to Seedance. (A retry that re-renders would produce
    # a different video and overwrite the original.)
    already_done = [p for p in expected if p.is_file() and p.stat().st_size > 0]
    if len(already_done) == n:
        activity.logger.info(
            f"[render_seedance] {n}/{n} output(s) already on disk — skipping Seedance call"
        )
        return ScenarioRenderResult(video_paths=[str(p) for p in already_done])

    prompt = Path(inp.prompt_path).read_text()
    model_id = inp.model_id or scenario.SEEDANCE_2_0

    # i2v: data-URL the seed frame so Seedance grounds in actual game pixels.
    seed_url: str | None = None
    if inp.seed_image_path:
        sp = Path(inp.seed_image_path)
        if sp.is_file() and sp.stat().st_size > 0:
            seed_url = file_to_data_url(sp)
            activity.logger.info(
                f"[render_seedance] i2v mode: seeding from {sp.name} "
                f"({sp.stat().st_size/1000:.0f}KB)"
            )
        else:
            activity.logger.warning(
                f"[render_seedance] seed_image_path={sp} missing or empty — "
                f"falling back to text-only"
            )

    activity.heartbeat(
        f"submitting Scenario Seedance ({model_id}, "
        f"{'i2v' if seed_url else 'txt2vid'})"
    )

    def hb(msg: str) -> None:
        activity.heartbeat(msg)

    videos = scenario.generate_video_seedance(
        prompt,
        model_id=model_id,
        aspect_ratio="9:16",
        duration_s=int(inp.video_duration_s),
        resolution="720p",
        generate_audio=True,
        num_videos=n,
        image_url=seed_url,
        on_heartbeat=hb,
    )
    paths = scenario.save_videos(videos, out_dir, prefix="creative")
    return ScenarioRenderResult(video_paths=[str(p) for p in paths])
