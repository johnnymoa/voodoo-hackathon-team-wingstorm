# adforge

AI ad pipelines for mobile games. Two composable Temporal workflows — and one that chains them.

- **`creative_forge`** — target game → market-informed brief + Scenario prompt
- **`playable_forge`** — gameplay video → single-file HTML playable + variants
- **`full_forge`** — target + video → both, where the playable is informed by the market patterns

Built for VoodooHack (Paris, Apr 26–27 2026), tracks 2 and 3.

## Top-down layout

```
adforge/
├── targets/                   ← INPUTS. One folder per game. See targets/README.md.
│   └── <target_id>/
│       ├── target.json        required — name, app_id, store_urls
│       ├── video.mp4          optional — gameplay video (gitignored)
│       ├── assets/            optional — images / audio for playables
│       └── README.md          optional — human notes
│
├── runs/                      ← OUTPUTS. One folder per execution. See runs/README.md.
│   └── <run_id>/
│       ├── manifest.json      who/what/when/status/artifacts
│       └── ...                pipeline-specific files
│
├── reference/                 ← STUDY MATERIAL. Canonical playables to learn from.
│   ├── MarbleSort.html
│   └── CupHeroes.html
│
├── src/adforge/               ← THE FORGE.
│   ├── config.py              env + path constants (TARGETS_DIR, RUNS_DIR, …)
│   ├── targets.py             load a target by id → resolved paths
│   ├── runs.py                make_run_id, run_dir helpers
│   ├── connectors/            composable: gemini, claude, mistral, sensortower, scenario
│   ├── activities/            composable: Temporal activities (atomic, retryable)
│   ├── pipelines/             workflows: creative_forge, playable_forge, full_forge
│   ├── templates/             playable_template.html
│   ├── worker.py              Temporal worker entrypoint
│   └── cli.py                 `adforge` CLI surface
│
├── docs/                      design notes, briefs, API reference
├── .env / .env.example        secrets
└── pyproject.toml             uv project manifest
```

The four top-level directories map 1:1 to four ideas:

- **targets/** = what you can run *against*
- **runs/** = what has been run
- **reference/** = what "good" looks like
- **src/adforge/** = the forge itself, top-down by layer

## Setup

Prereqs: `uv`, `temporal` CLI, Python 3.11+.

```bash
uv sync                          # install deps from pyproject.toml
cp .env.example .env             # then fill in keys
brew install temporal            # macOS — or: curl -sSf https://temporal.download/cli.sh | sh
```

## Run

Three terminals.

```bash
# terminal 1 — Temporal local dev server (single binary, web UI on :8233)
temporal server start-dev

# terminal 2 — long-lived worker hosting all activities + workflows
uv run adforge worker

# terminal 3 — kick off a workflow against a target
uv run adforge run creative --target castle_clashers
uv run adforge run playable --target castle_clashers
uv run adforge run full     --target castle_clashers
```

The Temporal Web UI at <http://localhost:8233> shows every activity, retry, and timing.
The artifacts land in `runs/<run_id>/`.

## Adding a new target

```bash
mkdir -p targets/royal_match
cat > targets/royal_match/target.json <<'EOF'
{ "name": "Royal Match", "app_id": null, "store_urls": {}, "notes": "" }
EOF
# (drop video.mp4 + assets/ alongside if you want to run playable / full)

uv run adforge tools targets             # confirm it shows up
uv run adforge run creative --target royal_match
```

## Standalone tools (no Temporal needed)

```bash
uv run adforge tools env                              # resolved settings
uv run adforge tools targets                          # list targets
uv run adforge tools targets castle_clashers         # show one target's details
uv run adforge tools runs                             # list runs
uv run adforge tools runs <run_id>                   # show one run's manifest
uv run adforge tools st-search "royal match"          # SensorTower search
uv run adforge tools st-top-creatives --network TikTok
uv run adforge tools inline runs/<run_id>/playable.html
```

## Skills (Claude Code)

Defined in `.claude/skills/`. Invoke with the Skill tool inside Claude Code.

- `creative-forge` — orchestrate the creative_forge pipeline
- `playable-forge` — orchestrate the playable_forge pipeline
- `full-forge`     — the merged demo
- `sensortower-research` — pull / cache market data without spinning up workflows
- `inline-html-assets` — collapse a multi-file playable into a single < 5 MB file
- `scenario-generate` — drive Scenario MCP from a brief

## Hackathon rules cheat-sheet

- Playable: ≤ 5 MB single HTML, no external deps, mobile browser
- ≥ 75% AI-written (Track 2 rule)
- Test on <https://p.applov.in/playablePreview?create=1> before submitting

## Credits

Hackathon keys live in `.env` (gitignored). Provided by Voodoo:
- `GEMINI_API_KEY`, `SENSORTOWER_API_KEY`
- `SCENARIO_*` provisioned at the event (auth via MCP OAuth)
- 40 USD Claude credits — use Claude Code with the Anthropic subscription
- Mistral credits — used by `creative_forge` for cheap per-creative labeling
