---
name: creative-forge
description: Run the creative_forge Temporal workflow. Take a target game, pull market data from SensorTower, extract winning patterns, and produce a creative brief + Scenario-ready prompt. Use when the user says "make me an ad creative for X", "what's working in the market for puzzle games", "generate an ad concept for Castle Clasher", or wants a market-informed brief. Skip if they only need raw data — use `sensortower-research` instead.
---

# creative_forge — game name → market-informed brief + Scenario prompt

Temporal workflow. End-to-end: SensorTower → pattern extraction → brief → Scenario prompt.

## Prereqs

- `temporal server start-dev` running
- `uv run adforge worker` running
- `MISTRAL_API_KEY` set (recommended — used for cheap per-creative labeling).
  Falls back to Gemini if not.

## Run

```bash
uv run adforge run creative \
  --target "castle clasher" \
  --category 7012 --country US --network TikTok --period month \
  --sample 30
```

To also render images headlessly via the Scenario HTTP API (instead of the MCP),
add `--render-http`. Default path is: workflow produces a prompt, you hand it to
the Scenario MCP inside Claude Code.

## What the workflow does

1. **`resolve_target_game`** — SensorTower search → unified app metadata.
2. **`fetch_market_data`** — top advertisers + top creatives in the genre/country/network for the period.
3. **`extract_patterns`** — Mistral labels each creative on a fixed vocab (`hook`, `opening_visual`, `mechanic_shown`, `cta_framing`, `palette_mood`) → ranked patterns with evidence trail.
4. **`write_brief_and_prompt`** — `brief.md` + `scenario_prompt.txt` derived from the top-ranked patterns.

Outputs in `output/creatives/<run_id>/`:
```
target.json                   # resolved unified app
top_advertisers.json          # SensorTower
top_creatives.json
patterns.json                 # the meat — ranked patterns with evidence_ids
brief.md                      # human-readable, cite-able
scenario_prompt.txt           # ready for the Scenario MCP
```

## Hand-off to Scenario

Default flow:
1. Open the brief in `output/creatives/<run_id>/brief.md` — confirm the chosen patterns make sense.
2. Read `scenario_prompt.txt`.
3. Call the Scenario MCP inside Claude Code (the MCP is wired in `.mcp.json`). Generate ≥ 3 variants.
4. Save the resulting images as `creative_v1.png`, `creative_v2.png`, … inside the same run dir.

Or in fully headless mode pass `--render-http` to skip step 2–4 (uses `SCENARIO_API_KEY`).

## Tips

- **Sample 30–60** for pattern extraction; more is diminishing returns.
- **Network choice matters.** TikTok ≠ Admob ≠ Facebook. For breadth, run the workflow once per network.
- **Cache is your friend.** SensorTower responses are cached to `.cache/sensortower/`. Re-runs are free.
- **Evidence trail.** When citing a pattern to the user/jury, mention 2–3 entries from `evidence_ids` in `patterns.json` so the claim is auditable.
- **Customize the vocab** in `src/adforge/activities/pattern_extraction.py::LABEL_VOCAB` if you want genre-specific labels.

## Pair with `playable-forge`

For the merged Voodoo demo (market-informed playable), use `full-forge` — it runs
this pipeline and feeds its `patterns.json` into `playable_forge` automatically.
