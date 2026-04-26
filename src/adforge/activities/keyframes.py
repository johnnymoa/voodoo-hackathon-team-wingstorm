"""Activity: extract evenly-spaced keyframes from a project's gameplay video.

Uses imageio (with the bundled imageio-ffmpeg static binary) so we don't depend
on a system ffmpeg install. Output: PNGs in <out_dir>/frames/, downscaled to
fit a max width so they're cheap to feed to Claude vision later.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from temporalio import activity


class KeyframeInput(BaseModel):
    video_path: str | None
    out_dir: str
    num_frames: int = 8
    max_width: int = 768


class KeyframeResult(BaseModel):
    frame_paths: list[str] = []
    fps: float | None = None
    duration_s: float | None = None


@activity.defn(name="extract_keyframes")
async def extract_keyframes(inp: KeyframeInput) -> KeyframeResult:
    if not inp.video_path:
        activity.logger.info("no video_path — skipping keyframe extraction")
        return KeyframeResult()

    video = Path(inp.video_path).resolve()  # follow symlinks (e.g. video.mp4 → .mov)
    if not video.exists() or video.stat().st_size == 0:
        activity.logger.info(f"video missing or empty at {video} — skipping")
        return KeyframeResult()

    out = Path(inp.out_dir) / "frames"
    out.mkdir(parents=True, exist_ok=True)

    import imageio.v2 as imageio
    from PIL import Image

    activity.heartbeat("opening video")
    reader = imageio.get_reader(str(video), format="ffmpeg")
    meta = reader.get_meta_data() or {}
    fps = float(meta.get("fps") or 0) or None
    duration_s = float(meta.get("duration") or 0) or None

    try:
        nframes = reader.count_frames()
    except Exception:
        nframes = int((fps or 30) * (duration_s or 0)) or 240

    n = max(1, min(inp.num_frames, nframes))
    if n == 1:
        indices = [0]
    else:
        indices = [int(i * (nframes - 1) / (n - 1)) for i in range(n)]

    paths: list[str] = []
    for i, idx in enumerate(indices):
        activity.heartbeat(f"frame {i + 1}/{n}")
        try:
            arr = reader.get_data(idx)
        except Exception as e:
            activity.logger.warning(f"failed to read frame {idx}: {e}")
            continue

        img = Image.fromarray(arr)
        if img.width > inp.max_width:
            ratio = inp.max_width / img.width
            img = img.resize((inp.max_width, int(img.height * ratio)), Image.LANCZOS)
        p = out / f"frame_{i:02d}.png"
        img.save(p, format="PNG", optimize=True)
        paths.append(str(p))

    reader.close()
    activity.logger.info(f"extracted {len(paths)} keyframes → {out}")
    return KeyframeResult(frame_paths=paths, fps=fps, duration_s=duration_s)
