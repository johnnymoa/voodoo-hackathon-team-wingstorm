"""Temporal activities — atomic, retryable units composed by workflows."""

from adforge.activities.briefing import write_brief_and_prompt
from adforge.activities.creative_render import render_seedance
from adforge.activities.finalize import finalize_run
from adforge.activities.io import extract_seed_frame, list_assets, write_json
from adforge.activities.market_data import fetch_market_data, resolve_target_game
from adforge.activities.pattern_extraction import extract_patterns
from adforge.activities.playable_build import build_playable_html
from adforge.activities.project_intel import analyze_project_docs
from adforge.activities.variations import generate_variations, inline_html_assets
from adforge.activities.video_analysis import analyze_gameplay_video
from adforge.activities.keyframes import extract_keyframes
from adforge.activities.intel import (
    gather_project_context,
    infer_genre,
    analyze_competitors,
    write_storyboards,
    render_slide_deck,
)

ALL = [
    # video / analysis
    analyze_gameplay_video,
    # market intelligence
    resolve_target_game,
    fetch_market_data,
    # GDD-aware project intel (reads .docx → genre/title for SensorTower lookup)
    analyze_project_docs,
    # pattern extraction (Claude Haiku + working-creative ranker)
    extract_patterns,
    # playable build (Claude Sonnet authors the loop body)
    build_playable_html,
    generate_variations,
    inline_html_assets,
    # creative brief + Scenario Seedance video render
    write_brief_and_prompt,
    render_seedance,
    # io / finalize
    write_json,
    list_assets,
    extract_seed_frame,
    finalize_run,
    # market intel (keyframes + Claude vision analysis + slide deck)
    extract_keyframes,
    gather_project_context,
    infer_genre,
    analyze_competitors,
    write_storyboards,
    render_slide_deck,
]
