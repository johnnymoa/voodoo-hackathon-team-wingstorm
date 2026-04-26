"""Activity: analyze a gameplay video with Gemini.

Two performance fixes wrap the Gemini call:

1. **Compression** — gameplay captures are routinely 100+ MB and Gemini's
   upload + processing routinely takes 2+ minutes on those, which trips
   Temporal's "workflow task exceeded 10 seconds" check and triggers a
   retry storm. We downsample to 480p mono via ffmpeg first (cached at
   `.cache/compressed_videos/<sha256>.mp4`), shrinking 100 MB → ~5-10 MB.

2. **Result cache** — the analysis output is cached at
   `.cache/gemini_video_analysis/<sha256>.json`. A re-run of the same
   project's `playable_forge` skips the upload entirely.
"""

from __future__ import annotations

import json
from pathlib import Path

from temporalio import activity

from adforge.activities.types import GameAnalysis, VideoAnalysisInput
from adforge.config import CACHE_DIR
from adforge.connectors import gemini
from adforge.utils import compress_video_for_analysis, file_sha256

SCHEMA = """{
  "title": str, "genre": str, "core_loop_seconds": int,
  "core_loop_summary": str, "primary_input": str,
  "win_condition": str, "lose_condition": str,
  "entities": [{"name": str, "role": str, "behavior": str, "visual": str}],
  "actions":  [{"name": str, "input": str, "effect": str}],
  "scene":    {"setting": str, "perspective": str, "color_palette": [str], "art_style": str},
  "ui_elements": [{"name": str, "purpose": str, "screen_position": str}],
  "juice": [str],
  "audio_cues": [{"trigger": str, "feel": str}],
  "playable_simplifications": [str],
  "configurable_parameters": [{"name": str, "type": str, "default": "any", "min": "any", "max": "any", "why": str}],
  "asset_needs": [{"kind": str, "description": str, "count": int}],
  "first_3_seconds": str, "cta": str
}"""

DEFAULT_PROMPT = (
    "You are analyzing a gameplay video to build a 30-second interactive HTML "
    "playable ad. Identify ONE core mechanic that survives a 30-second slice. "
    "Capture scene, palette, juice, audio, UI, asset needs, and configurable "
    "parameters. Be concrete and specific."
)


_CACHE_ANALYSIS = CACHE_DIR / "gemini_video_analysis"
_CACHE_COMPRESSED = CACHE_DIR / "compressed_videos"


def _load_cached_analysis(digest: str) -> dict | None:
    p = _CACHE_ANALYSIS / f"{digest}.json"
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def _save_cached_analysis(digest: str, raw: dict) -> None:
    _CACHE_ANALYSIS.mkdir(parents=True, exist_ok=True)
    (_CACHE_ANALYSIS / f"{digest}.json").write_text(json.dumps(raw, indent=2))


@activity.defn(name="analyze_gameplay_video")
async def analyze_gameplay_video(inp: VideoAnalysisInput) -> GameAnalysis:
    src = Path(inp.video_path)
    digest = file_sha256(src)[:16]

    # Cache hit: skip Gemini entirely.
    cached = _load_cached_analysis(digest)
    if cached is not None:
        activity.logger.info(f"[video_analysis] cache hit ({digest}) — skipping Gemini upload.")
        scene = cached.get("scene") or {}
        return GameAnalysis(
            raw=cached,
            title=cached.get("title"),
            core_loop_summary=cached.get("core_loop_summary"),
            primary_input=cached.get("primary_input"),
            palette=scene.get("color_palette"),
        )

    # Compress before upload — 100 MB gameplay caps would otherwise time out.
    activity.heartbeat(f"compressing {src.name}")
    compressed = compress_video_for_analysis(src, cache_dir=_CACHE_COMPRESSED)
    activity.logger.info(
        f"[video_analysis] {src.stat().st_size / 1e6:.1f} MB → "
        f"{compressed.stat().st_size / 1e6:.1f} MB ({compressed.name})"
    )

    activity.heartbeat("uploading + analyzing")
    raw = gemini.analyze_video_json(
        compressed,
        prompt=inp.prompt or DEFAULT_PROMPT,
        schema_hint=SCHEMA,
    )

    _save_cached_analysis(digest, raw)
    activity.logger.info(f"[video_analysis] cached → {_CACHE_ANALYSIS / f'{digest}.json'}")

    scene = raw.get("scene") or {}
    return GameAnalysis(
        raw=raw,
        title=raw.get("title"),
        core_loop_summary=raw.get("core_loop_summary"),
        primary_input=raw.get("primary_input"),
        palette=scene.get("color_palette"),
    )
