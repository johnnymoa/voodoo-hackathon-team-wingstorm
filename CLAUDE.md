# adforge — Voodoo Hack pipelines

Two composable Temporal pipelines for mobile-game ad generation, plus one that chains them:

- **`creative_forge`** — target game → market-informed brief + Scenario prompt
- **`playable_forge`** — gameplay video → interactive HTML playable + variants
- **`full_forge`** — chains both: target + video → brief + creative + market-informed playable

## Top-down layout

The repo root maps four directories to four ideas:

```
targets/                INPUTS.   One folder per game. target.json + optional video.mp4 + assets/
runs/                   OUTPUTS.  One folder per execution. manifest.json + artifacts.
reference/              STUDY.    Canonical playables to learn from (NOT generated, NOT consumed).
src/adforge/            FORGE.    The code. Top-down: config → connectors → activities → pipelines → cli.
```

Plus `docs/`, `.env*`, `.mcp.json`, `pyproject.toml` at the root for setup/config.

## Mental model: target → run

A **target** is a named bundle of inputs (game name, optional video, optional assets).
A **run** is one pipeline execution against a target. Everything else is plumbing.

```
targets/<id>/  ──[ pipeline ]──>  runs/<run_id>/
```

`run_id` is `YYYYMMDD-HHMMSS__<pipeline>__<target_id>` — sortable, greppable,
also used as the Temporal workflow_id so you can deep-link to the orchestration view.

Every run folder has a `manifest.json` with status + artifacts. That's the
single record the CLI / future UI / any tool reads.

## How it runs

1. `temporal server start-dev` runs the orchestrator (single binary, no infra).
2. `uv run adforge worker` runs a long-lived worker that hosts every activity + workflow.
3. `uv run adforge run <pipeline> --target <id>` starts a workflow execution.
4. The Temporal Web UI at <http://localhost:8233> shows runs, retries, durations.

## src/adforge top-down

```
config.py             env + path constants (TARGETS_DIR, RUNS_DIR, REFERENCE_DIR, CACHE_DIR)
targets.py            load a target id → resolved Target (paths + metadata)
runs.py               make_run_id, run_dir, list_runs
utils.py              small helpers (slug, data-url, size guards)
connectors/           plain-Python clients: gemini, claude, mistral, sensortower, scenario
activities/           Temporal activities (atomic, retryable, composable units)
  finalize.py         finalize_run — last step of every workflow, writes manifest.json
pipelines/            Temporal workflows: creative_forge, playable_forge, full_forge
templates/            playable_template.html (CONFIG-block driven)
worker.py             Temporal worker entrypoint
cli.py                typer CLI: `adforge worker`, `adforge run …`, `adforge tools …`
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

# run pipelines
uv run adforge run creative --target castle_clashers
uv run adforge run playable --target castle_clashers
uv run adforge run full     --target castle_clashers

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
