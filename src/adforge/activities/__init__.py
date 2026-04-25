"""Temporal activities — atomic, retryable units composed by workflows."""

from adforge.activities.briefing import write_brief_and_prompt
from adforge.activities.creative_render import render_scenario_creative
from adforge.activities.finalize import finalize_run
from adforge.activities.io import write_json
from adforge.activities.market_data import fetch_market_data, resolve_target_game
from adforge.activities.pattern_extraction import extract_patterns
from adforge.activities.playable_build import build_playable_html
from adforge.activities.variations import generate_variations, inline_html_assets
from adforge.activities.video_analysis import analyze_gameplay_video

ALL = [
    analyze_gameplay_video,
    resolve_target_game,
    fetch_market_data,
    extract_patterns,
    build_playable_html,
    generate_variations,
    inline_html_assets,
    write_brief_and_prompt,
    render_scenario_creative,
    write_json,
    finalize_run,
]
