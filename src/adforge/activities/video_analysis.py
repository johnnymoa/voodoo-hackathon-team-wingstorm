"""Activity: analyze a gameplay video with Gemini."""

from __future__ import annotations

from pathlib import Path

from temporalio import activity

from adforge.activities.types import GameAnalysis, VideoAnalysisInput
from adforge.connectors import gemini

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


@activity.defn(name="analyze_gameplay_video")
async def analyze_gameplay_video(inp: VideoAnalysisInput) -> GameAnalysis:
    activity.heartbeat("uploading + analyzing")
    raw = gemini.analyze_video_json(
        Path(inp.video_path),
        prompt=inp.prompt or DEFAULT_PROMPT,
        schema_hint=SCHEMA,
    )
    scene = raw.get("scene") or {}
    return GameAnalysis(
        raw=raw,
        title=raw.get("title"),
        core_loop_summary=raw.get("core_loop_summary"),
        primary_input=raw.get("primary_input"),
        palette=scene.get("color_palette"),
    )
