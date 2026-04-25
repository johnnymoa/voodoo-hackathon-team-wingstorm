# adforge

AI ad pipelines for mobile games. Two composable Temporal workflows — and one that chains them.

- **`playable_forge`** — gameplay video → single-file HTML playable + variants
- **`creative_forge`** — target game → market-informed brief + Scenario prompt
- **`full_forge`** — target + video → both, where the playable is informed by the market patterns

Built for VoodooHack (Paris, Apr 26–27 2026), tracks 2 and 3.

## Setup

Prereqs: `uv`, `temporal` CLI, Python 3.11+.

```bash
# install Python deps from pyproject.toml
uv sync

# fill in keys (already populated for the hackathon)
cp .env.example .env

# (optional) Scenario MCP — open Claude Code, run /mcp, authorize Scenario
```

Install the Temporal CLI if you don't have it:

```bash
brew install temporal      # macOS
# or: curl -sSf https://temporal.download/cli.sh | sh
```

## Run

You'll need three terminals.

```bash
# terminal 1 — Temporal local dev server (single binary, no docker)
temporal server start-dev
#   web UI: http://localhost:8233

# terminal 2 — adforge worker (hosts activities + workflows)
uv run adforge worker

# terminal 3 — kick off a workflow
uv run adforge run playable --video videos/castle_clasher.mp4 --assets assets/castle_clashers
uv run adforge run creative --target "castle clasher"
uv run adforge run full     --target "castle clasher" --video videos/castle_clasher.mp4 --assets assets/castle_clashers
```

Watch the run in the Temporal Web UI — every activity, retry, and duration is visible.

## What you get

```
output/
├── playables/<run_id>/
│   ├── playable.html              base playable (CONFIG injected from analysis + market)
│   ├── playable__easy.html        variants (CONFIG overrides)
│   ├── playable__hard.html
│   └── ...
├── creatives/<run_id>/
│   ├── target.json                resolved unified app metadata
│   ├── top_advertisers.json       SensorTower data
│   ├── top_creatives.json
│   ├── patterns.json              Mistral/Gemini-labeled hooks/CTAs/palettes
│   ├── brief.md                   creative brief w/ rationale
│   └── scenario_prompt.txt        copy-paste prompt for Scenario MCP / API
└── full/<run_id>/
    ├── creative/                  ⤴ same as above
    └── playable/                  ⤴ same as above, with market-informed CONFIG + variants
```

## Standalone tools (no Temporal needed)

```bash
uv run adforge tools env                                 # check resolved settings
uv run adforge tools st-search "royal match"             # SensorTower search
uv run adforge tools st-top-creatives --network TikTok --save output/top.json
uv run adforge tools inline output/playables/<run>/playable.html   # collapse external assets
uv run adforge tools gemini-models
```

## Layout

```
src/adforge/
├── config.py             settings (env, paths)
├── utils.py
├── connectors/           plain-Python: gemini, claude, mistral, sensortower, scenario
├── activities/           Temporal activities — atomic, retryable
├── pipelines/            Temporal workflows: playable_forge, creative_forge, full_forge
├── templates/            playable_template.html
├── worker.py             Temporal worker entrypoint
└── cli.py                typer CLI
```

## Skills (Claude Code)

Defined in `.claude/skills/`. Invoke with the Skill tool inside Claude Code.

- `playable-forge` — orchestrate the playable_forge pipeline
- `creative-forge` — orchestrate the creative_forge pipeline
- `full-forge`     — the merged demo
- `sensortower-research` — pull / cache market data without spinning up workflows
- `inline-html-assets` — collapse a multi-file playable into a single < 5 MB file
- `scenario-generate` — drive Scenario MCP from a brief

## Hackathon rules cheat-sheet

- Playable: ≤ 5 MB single HTML, no external deps, mobile browser
- ≥ 75% AI-written (Track 2 rule)
- Test on https://p.applov.in/playablePreview?create=1 before submitting

## Credits

Hackathon keys live in `.env` (gitignored). Provided by Voodoo:
- `GEMINI_API_KEY`, `SENSORTOWER_API_KEY`
- `SCENARIO_*` provisioned at the event (auth via MCP OAuth)
- 40 USD Claude credits — use Claude Code with the Anthropic subscription
- Mistral credits — used by `creative_forge` for cheap per-creative labeling
