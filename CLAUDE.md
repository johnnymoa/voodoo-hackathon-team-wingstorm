# adforge — Voodoo Hack pipelines

> **project → pipeline → run.** Three nouns, one mental model.

- **`creative_forge`** — Track 3. Project → web research → market insights → storyboard → video ad creative.
- **`playable_forge`** — Track 2. Project (with video + assets) → single-file HTML playable + variants.

Each pipeline has named **configs** (PipelineConfig presets) so we can A/B model
choices, prompts, and code paths without forking. The forge is the scaffold;
configs are how we iterate scientifically.

## Top-down layout

```
projects/         INPUTS.   one folder per game
runs/             OUTPUTS.  one folder per execution (manifest.json + artifacts)
src/adforge/      FORGE.    code, top-down: config → connectors → activities → pipelines → cli + api
ui/               VIEWER.   Vite + React + Tailwind. Reads the API.
```

Plus `docs/`, `.env*`, `.mcp.json`, `pyproject.toml` at root.

## Mental model

A **project** is the kitchen-sink folder for everything we know about a game
(name, genre, description, category, optional video + assets). Schema lives
in `src/adforge/projects.py`.

A **pipeline** is a Temporal workflow that consumes a project and produces a
run. Catalog lives in `src/adforge/pipelines/__init__.py` (`PIPELINES` registry
with id / glyph / tagline / needs / produces / configs). The CLI, API, and UI
all read from it.

A **run** is one pipeline execution against one project, captured at
`runs/<run_id>/` with `manifest.json` describing what was produced. The CLI,
API, and UI all read manifests.

```
projects/<id>/  ──[ pipeline + config ]──>  runs/<run_id>/
```

`run_id` = `YYYYMMDD-HHMMSS__<pipeline>__<project_id>`. Sortable, greppable,
and reused as the Temporal `workflow_id` (deep-link from the UI works).

## src/adforge top-down

```
config.py             env + path constants (PROJECTS_DIR, RUNS_DIR, CACHE_DIR)
projects.py           load a project id → resolved Project (paths + metadata)
runs.py               make_run_id, run_dir, list_runs
utils.py              small helpers
connectors/           plain-Python clients: gemini, claude, mistral, sensortower, scenario
activities/           Temporal activities (atomic, retryable)
  finalize.py         finalize_run — writes manifest.json (with project_id, config_id)
pipelines/            Temporal workflows
  __init__.py         PIPELINES + CONFIGS registry — single source of truth
  creative_forge.py   the video-ad pipeline
  playable_forge.py   the playable pipeline
templates/            playable_template.html + examples/ (in-context refs for the LLM)
worker.py             Temporal worker entrypoint
api.py                FastAPI shim (powers ui/)
cli.py                typer CLI
```

## How to iterate on a pipeline

The fast loop:

1. Add a new `PipelineConfig` entry in `pipelines/__init__.py` for the
   pipeline you're tuning (e.g. `claude-prose-brief` for `creative_forge`).
2. Branch in the relevant activity on `inp.config_id` to swap behavior.
3. `uv run adforge run creative --project castle_clashers --config claude-prose-brief`
4. Compare runs side-by-side in the UI — config_id is on every row.

Old runs stay reproducible because the manifest captures the `config_id`.

## How it runs

1. `temporal server start-dev` — orchestrator (single binary).
2. `uv run adforge worker` — long-lived worker hosting activities + workflows.
3. `uv run adforge api` — FastAPI shim, powers the UI.
4. `cd ui && npm run dev` — Vite dev server.
5. `uv run adforge run <pipeline> --project <id> [--config <id>]` — kick off a run.

Temporal Web UI at <http://localhost:8233> for raw orchestration.
adforge UI at <http://localhost:5173> for the friendly product view.

## Conventions

- **Single-file HTML deliverables** for `playable_forge`. No CDNs, no external
  scripts. All assets inlined as base64 (or generated at runtime).
- **5 MB size budget** — `assert_under_size` guards every build.
- **CONFIG block at top** of every playable so variants are a 30-second edit.
- **Mobile-first.** Touch input, viewport meta, no hover.
- **Reproducibility** — every run captures its `params` + `config_id` in
  manifest.json. New `run_id` per execution, no clobbering.
- **Cached SensorTower** — `.cache/sensortower/`. Bust by `rm -rf .cache/sensortower`.

## Don't do this

- Don't commit `.env` (gitignored).
- Don't load remote scripts/fonts in playables — ad networks reject them.
- Don't recreate the full game. Smallest fun loop wins.
- Don't bypass Temporal in workflows. Call activities for IO.
- Don't add `requirements.txt` — uv owns deps via `pyproject.toml`.
- Don't hard-code paths to `projects/` or `runs/`. Import `PROJECTS_DIR` /
  `RUNS_DIR` from `config.py`, or use `projects.load()` / `runs.make_run_id()`.

## Quick commands

```bash
uv sync
temporal server start-dev
uv run adforge worker
uv run adforge api
cd ui && npm run dev

uv run adforge tools projects
uv run adforge tools projects castle_clashers
uv run adforge tools pipelines
uv run adforge tools runs

uv run adforge run creative --project castle_clashers
uv run adforge run playable --project castle_clashers --config default
```

## Useful links

- AppLovin Playable Preview: <https://p.applov.in/playablePreview?create=1>
- Scenario MCP install: <https://mcp.scenario.com/?agent=claude-code&auth=oauth>
- Temporal local dev: `temporal server start-dev` → <http://localhost:8233>
- SensorTower API: see `docs/sensortower_api.md`
