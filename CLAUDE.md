# adforge — Voodoo Hack pipelines

> A single forge for ad assets. **target → pipeline → run.**

- **`creative_forge`** — target game → market-informed brief + Scenario prompt
- **`playable_forge`** — gameplay video → interactive HTML playable + variants
- **`full_forge`** — chains both: target + video → brief + creative + market-informed playable

## Top-down layout

The repo root maps three top-level data dirs + the code dir to four ideas:

```
targets/                INPUTS.   one folder per game (target.json + optional video.mp4 + assets/)
runs/                   OUTPUTS.  one folder per execution (manifest.json + artifacts)
src/adforge/            FORGE.    code, top-down: config → connectors → activities → pipelines → cli + api
ui/                     VIEWER.   Vite + React + Tailwind. Reads runs/ + targets/ via api.py.
```

Plus `docs/`, `.env*`, `.mcp.json`, `pyproject.toml` at the root for setup/config.

There used to be a `reference/` folder with example playables. That was dead
weight — the examples now live in `src/adforge/templates/examples/` where the
playable-build activity uses them as in-context references.

## Mental model: target → pipeline → run

A **target** is the kitchen-sink folder for everything we know about a game:
display name, genre, description, store category, optional gameplay video,
optional asset kit. The schema lives in `src/adforge/targets.py` (Target model)
and is documented in the docstring there.

A **pipeline** is a Temporal workflow that consumes a target and produces a run.
The catalog lives in `src/adforge/pipelines/__init__.py` (PIPELINES list with
id / glyph / tagline / needs / produces). The CLI, API, and UI all read from it.

A **run** is one pipeline execution against one target. The folder is
`runs/<run_id>/` and always contains a `manifest.json` (the single record the
CLI / API / UI all read).

```
targets/<id>/  ──[ pipeline ]──>  runs/<run_id>/
```

`run_id` is `YYYYMMDD-HHMMSS__<pipeline>__<target_id>` — sortable, greppable,
and reused as the Temporal `workflow_id` so the UI's "View in Temporal" link
just works.

## How it runs

1. `temporal server start-dev` runs the orchestrator (single binary, no infra).
2. `uv run adforge worker` runs a long-lived worker that hosts every activity + workflow.
3. `uv run adforge run <pipeline> --target <id>` starts a workflow execution.
4. The Temporal Web UI at <http://localhost:8233> shows runs, retries, durations.

## src/adforge top-down

```
config.py             env + path constants (TARGETS_DIR, RUNS_DIR, CACHE_DIR)
targets.py            load a target id → resolved Target (paths + metadata)
runs.py               make_run_id, run_dir, list_runs
utils.py              small helpers (slug, data-url, size guards)
connectors/           plain-Python clients: gemini, claude, mistral, sensortower, scenario
activities/           Temporal activities (atomic, retryable, composable units)
  finalize.py         finalize_run — last step of every workflow, writes manifest.json
pipelines/            Temporal workflows: creative_forge, playable_forge, full_forge
  __init__.py         PIPELINES registry — single source of truth (CLI/API/UI all read it)
templates/            playable_template.html + examples/ (in-context references for the LLM)
worker.py             Temporal worker entrypoint
api.py                FastAPI shim that powers the ui/ viewer
cli.py                typer CLI: `adforge worker`, `adforge api`, `adforge run …`, `adforge tools …`
```

Read top-to-bottom: by the time you hit `pipelines/`, every dependency has been introduced.

## Naming convention

We don't say "Track 2" / "Track 3" anywhere in code. The pipelines are named for
what they *do*:

| Voodoo track | adforge pipeline | Input → Output |
|---|---|---|
| Track 3 (market intel) | `creative_forge` | target → brief + Scenario prompt + (optional) image |
| Track 2 (playable ads) | `playable_forge` | target (with video + assets) → single-file HTML playable + variants |
| Both, merged demo      | `full_forge`     | target (with video + assets) → everything above, market-informed |

## How we work with Claude (Spec → Plan → Build)

Use three conversations for non-trivial features:
1. **Spec** (Opus) — describe the goal, no code. Output: `docs/<feature>-spec.md`.
2. **Plan** (Opus) — feed spec + relevant source. Output: `docs/<feature>-plan.md`.
3. **Build** (Sonnet) — feed only the plan. Implement one task at a time.

Skip for trivial fixes, clear-repro bugs, exploratory prototypes.

## Conventions

- **Single-file HTML deliverables** for `playable_forge`. No CDNs, no external scripts. All assets inlined as base64 (or generated at runtime).
- **Size budget:** ≤ 5 MB. The activity prints size after every build; CI guard via `assert_under_size`.
- **CONFIG block at top** of every playable so variations are a 30-second edit.
- **Mobile-first.** Touch input, viewport meta, no hover.
- **Variations are part of the deliverable** — not an afterthought. `full_forge` makes them *market-hypothesis* variants (each tests a top-ranked hook / palette).
- **Reproducibility** — every run lands in `runs/<run_id>/` with a `manifest.json` that records the params used. Re-running with the same params still gets a new `run_id` (no clobbering).
- **Cached SensorTower** — `.cache/sensortower/` deduplicates calls. Bust by `rm -rf .cache/sensortower`.

## Don't do this

- Don't commit `.env` (gitignored).
- Don't load remote scripts/fonts in playables — ad networks reject them.
- Don't recreate the full game. Pick the smallest fun loop and ship it.
- Don't bypass Temporal in workflows by doing IO directly — call activities.
- Don't add a `requirements.txt` — uv owns deps via `pyproject.toml`.
- Don't hard-code paths to `targets/` or `runs/` — import `TARGETS_DIR` / `RUNS_DIR` from `config.py`, or use `targets.load()` / `runs.make_run_id()`.

## Quick commands

```bash
# install / sync deps
uv sync

# start Temporal locally (separate terminal)
temporal server start-dev   # http://localhost:8233 web UI

# run the worker (separate terminal)
uv run adforge worker

# inspect targets and runs
uv run adforge tools targets                   # list targets
uv run adforge tools targets castle_clashers   # show one target
uv run adforge tools runs                      # list runs
uv run adforge tools runs <run_id>             # show one manifest

# run pipelines (target metadata auto-fills category/country/etc; flags are just overrides)
uv run adforge run creative --target castle_clashers
uv run adforge run playable --target castle_clashers
uv run adforge run full     --target castle_clashers

# UI (optional but it's how the demo lands)
uv run adforge api           # FastAPI shim, http://127.0.0.1:8765
cd ui && npm run dev         # Vite, http://localhost:5173

# standalone helpers (no Temporal needed)
uv run adforge tools env
uv run adforge tools st-search "royal match"
uv run adforge tools st-top-creatives --network TikTok --save /tmp/top.json
uv run adforge tools inline runs/<run_id>/playable.html
```

## Useful links

- AppLovin Playable Preview: <https://p.applov.in/playablePreview?create=1>
- Scenario MCP install: <https://mcp.scenario.com/?agent=claude-code&auth=oauth>
- Temporal local dev: `temporal server start-dev` → <http://localhost:8233>
- SensorTower API: see `docs/sensortower_api.md`
