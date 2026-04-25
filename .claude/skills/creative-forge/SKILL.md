---
name: creative-forge
description: Run the creative_forge Temporal workflow against a project — pulls market intelligence, extracts winning patterns, writes a creative brief and a Scenario-ready prompt. Use when the user says "make me an ad creative for X", "what's working in the market for puzzle games", "generate a brief for Castle Clashers", or wants a market-informed brief. Skip if they only want raw market data — use `sensortower-research` instead. Pairs with `video-ad-design` (the design rubric for the brief), `scenario-generate` (renders the asset from the prompt), and `iterate` (turns feedback into a new config).
---

# creative-forge — project → market-informed brief + Scenario prompt

Temporal workflow. End-to-end: SensorTower → pattern extraction →
brief.md → scenario_prompt.txt. Reads input from `projects/<id>/`,
writes output to `runs/<run_id>/`.

## Prereqs

- `temporal server start-dev` running (Web UI: <http://localhost:8233>)
- `uv run adforge worker` running
- `MISTRAL_API_KEY` set (recommended — used for cheap per-creative
  labeling). Falls back to Gemini if not.
- Project exists at `projects/<project_id>/project.json` with at least
  `name`, `category_id`, `country` (good defaults: Puzzle = `7012`,
  US). Verify with: `uv run adforge tools projects <id>`.

## Run

From the UI Run button, or:

```bash
uv run adforge run creative --project castle_clashers --config default
```

Optional flags (override what's in project.json):

```bash
uv run adforge run creative --project castle_clashers \
  --network TikTok --period month --sample 30
```

To also render images headlessly via the Scenario HTTP API (instead of
hand-off to the Scenario MCP), add `--render-http`. Default: workflow
produces a prompt, you hand it to the Scenario MCP via `scenario-generate`.

## What the workflow does

1. **`resolve_target_game`** — SensorTower search → unified app metadata.
2. **`fetch_market_data`** — top advertisers + top creatives in the
   genre/country/network for the period.
3. **`extract_patterns`** — Mistral labels each creative on a fixed vocab
   (`hook`, `opening_visual`, `mechanic_shown`, `cta_framing`,
   `palette_mood`) → ranked patterns with evidence trail.
4. **`write_brief_and_prompt`** — `brief.md` + `scenario_prompt.txt`
   derived from the top-ranked patterns.
5. **`finalize_run`** — writes `manifest.json`.

## Output

```
runs/<run_id>/
├── manifest.json                ← what the UI reads
├── target.json                  ← resolved unified app
├── top_advertisers.json         ← from SensorTower
├── top_creatives.json
├── patterns.json                ← the meat — ranked patterns with evidence_ids
├── brief.md                     ← human-readable, cite-able
└── scenario_prompt.txt          ← ready for the Scenario MCP
```

## Hand-off to Scenario

Default flow (recommended for iteration):

1. Open the brief at `runs/<run_id>/brief.md` — confirm the chosen
   patterns make sense against `video-ad-design` rubric.
2. Read `scenario_prompt.txt`.
3. Invoke `scenario-generate` (or call the Scenario MCP directly) and
   render ≥ 3 variants. Save under the same `runs/<run_id>/` so the UI
   shows them next to the brief.

For full headless rendering, pass `--render-http` to skip steps 2–3
(uses `SCENARIO_API_KEY`).

## Tips

- **Sample 30–60** for pattern extraction; more is diminishing returns.
- **Network choice matters.** TikTok ≠ Admob ≠ Facebook. For breadth,
  run the workflow once per network (each becomes a separate run with
  its own `config_id` if you set one up via `/iterate`).
- **Cache is your friend.** SensorTower responses are cached to
  `.cache/sensortower/`. Re-runs are free.
- **Evidence trail.** When citing a pattern to the user/jury, mention
  2–3 entries from `evidence_ids` in `patterns.json` so the claim is
  auditable.
- **Customize the vocab** in
  `src/adforge/activities/pattern_extraction.py::LABEL_VOCAB` if you
  want genre-specific labels.

## Iteration loop

After a run lands, write feedback in the Run page (e.g. "brief is too
generic, push the labeler harder on opening hooks") and run `/iterate`
in Claude Code. The skill reads your feedback, proposes a new
`PipelineConfig` (e.g. `claude-prose-brief`), edits the registry,
restarts the worker, and ships the new config — closing the feedback
loop with a link to the addressing run.

For the design rubric — what makes a brief good vs vague — consult
`video-ad-design`. It has the 5-question quality check and the
hook/CTA framings that consistently perform.
