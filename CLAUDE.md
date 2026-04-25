# adforge — a forge for AI ad pipelines, made for Claude Code

> **project → pipeline → run → feedback → /iterate.** A loop, not a checklist.

This repo is designed to be opened in Claude Code and used as a vibe-coding
forge for AI ad pipelines. The harness is small. The intelligence lives in
the **skills** under `.claude/skills/` — domain knowledge (what makes a good
playable, how to drive Scenario, when to call SensorTower) plus the recipes
that drive the iteration loop (`/iterate`, `/new-pipeline`).

Open it in Claude Code and you're in the loop:

1. Pick or add a project under `projects/`.
2. Run a pipeline (UI button, or `uv run adforge run …`).
3. Look at the artefacts in `runs/<run_id>/`. Write feedback in the UI Feedback
   panel — saves to `runs/<run_id>/feedback.md`.
4. Back in Claude Code, run **`/iterate`**. The iterate skill reads open
   feedback and ships a new `PipelineConfig` (and optionally one activity
   edit) that addresses it.
5. Compare runs in the UI. Repeat.

When you want a brand-new pipeline shape (not just a config tweak), run
**`/new-pipeline`** and Claude scaffolds the workflow + activities + registry
entry.

Two pipelines ship by default:

- **`creative_forge`** — Project → market intelligence → storyboard → Scenario-rendered creative (image or video).
- **`playable_forge`** — Project (with video + assets) → single-file HTML playable + parameter variants.

Each pipeline has named **configs** (`PipelineConfig` presets) so you A/B
model choices, prompts, and code paths without forking. The forge is the
scaffold; configs are how we iterate scientifically.

## Top-down layout

```
projects/         INPUTS.    one folder per game (project.json + optional video + assets)
runs/             OUTPUTS.   one folder per execution (manifest.json + artefacts + feedback.md)
src/adforge/      FORGE.     Python — config → connectors → activities → pipelines → cli + api
ui/               VIEWER.    Vite + React + Tailwind. Reads the API. Where you write feedback.
.claude/skills/   KNOWLEDGE. Domain expertise + iteration recipes Claude Code loads on demand.
```

Plus `.env*`, `.mcp.json`, `pyproject.toml` at root. Nothing else.

## Mental model

A **project** is the kitchen-sink folder for everything we know about a game
(name, genre, description, category, optional video + assets). Schema lives
in `src/adforge/projects.py`.

A **pipeline** is a Temporal workflow that consumes a project and produces a
run. Catalog lives in `src/adforge/pipelines/__init__.py` (`PIPELINES` registry
with id / name / description / inputs / outputs / configs). The CLI, API, and
UI all read from it.

A **run** is one pipeline execution against one project, captured at
`runs/<run_id>/` with `manifest.json` describing what was produced, plus an
optional `feedback.md` you write after inspecting the artefacts. The CLI, API,
and UI all read manifests; the `/iterate` skill reads feedback.

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
runner.py             start_run — shared Temporal workflow launcher (CLI + API)
feedback.py           per-run feedback.md read/write/list (drives /iterate)
utils.py              small helpers
connectors/           plain-Python clients: gemini, claude, mistral, sensortower, scenario
activities/           Temporal activities (atomic, retryable)
  finalize.py         finalize_run — writes manifest.json (with project_id, config_id)
pipelines/            Temporal workflows
  __init__.py         PIPELINES registry — single source of truth
  creative_forge.py   the video-ad pipeline
  playable_forge.py   the playable pipeline
templates/            playable_template.html + examples/ (in-context refs for the LLM)
worker.py             Temporal worker entrypoint
api.py                FastAPI shim (powers ui/)
cli.py                typer CLI
```

## The iteration loop

This is the heart of the repo. Build it into your habits:

```
run → inspect artefacts → write feedback → /iterate → compare → repeat
```

1. **Run** a pipeline on a project (UI Run button or `uv run adforge run …`).
2. **Inspect** the artefacts in `runs/<run_id>/`.
3. **Leave feedback** on the Run page — the textarea writes
   `runs/<run_id>/feedback.md` with frontmatter (`status: open`,
   `created_at`, …). Be specific: what failed, what good looks like, your
   hypothesis if you have one.
4. **`/iterate`** in Claude Code. The `iterate` skill
   (`.claude/skills/iterate/SKILL.md`) reads open feedback, proposes a new
   `PipelineConfig` (and optionally an activity-file branch), validates,
   tells you to restart the worker, kicks off the new run, and closes the
   feedback by linking the run that addressed it.
5. **Compare** the original and new runs in the UI — `config_id` is on
   every row so it's easy to keep track.

Old runs stay reproducible because the manifest captures `config_id`.

### Feedback file format

```markdown
---
status: open                       # open | fulfilled | wontfix
created_at: 2026-04-25T13:42:00+00:00
updated_at: 2026-04-25T13:42:00+00:00
addressed_in_run: null             # filled when an iteration ships
addressed_by_config: null          # config_id that addressed it
---
The brief is too generic. Push the labeler harder on opening hooks.
Try Claude instead of Mistral for pattern extraction.
```

Feedback files are checked into git — they're the iteration paper trail.
Each new `PipelineConfig.description` should be the hypothesis the
iteration tests; reading the registry over time is reading the lab notebook.

### Feedback CLI

```bash
uv run adforge feedback ls                         # list open feedback across runs
uv run adforge feedback ls --all                   # include fulfilled / wontfix
uv run adforge feedback show <run_id>              # full body + frontmatter
uv run adforge feedback close <run_id> \
    --by-run <new_run_id> --by-config <new_cfg>    # mark fulfilled (the /iterate skill calls this)
uv run adforge feedback wontfix <run_id>           # decided not to address it
uv run adforge feedback reopen <run_id>            # back to open
```

### Iteration ground rules (also encoded in `/iterate`)

- **One config per iteration.** If feedback wants two unrelated changes, do
  two cycles.
- **Edit surface:** `src/adforge/pipelines/__init__.py` and ONE activity file
  under `src/adforge/activities/`. Off-limits: workflow files in
  `src/adforge/pipelines/<name>.py`, anything outside `src/adforge/`.
- **Don't delete or rewrite** existing configs / logic. Add a config, branch
  the activity on `inp.config_id`, leave defaults alone.
- **Restart `uv run adforge worker`** after every iteration so it picks up
  the new code (the registry is read on import, and activities load fresh).
- **The new config's `description` is the hypothesis.** That's the audit trail.

### Adding a brand-new pipeline (vs iterating on an existing one)

Adding a config = `/iterate`. Adding a whole new pipeline is bigger and not
in scope for `/iterate` — it's a manual three-step:

1. Add a `PipelineSpec` to `PIPELINES` in `src/adforge/pipelines/__init__.py`.
2. Drop a new workflow class next to it (`src/adforge/pipelines/<name>.py`)
   wired up to existing or new activities.
3. Add a launcher branch in `src/adforge/runner.py::_build_workflow_input`.

The CLI / API / UI all read the registry, so the new pipeline appears
everywhere as soon as you save and restart the worker.

## How it runs

1. `temporal server start-dev` — orchestrator (single binary).
2. `uv run adforge worker` — long-lived worker hosting activities + workflows.
3. `uv run adforge api` — FastAPI shim, powers the UI.
4. `cd ui && npm run dev` — Vite dev server.
5. `uv run adforge run <pipeline> --project <id> [--config <id>]` — kick off a run.

Temporal Web UI at <http://localhost:8233> for raw orchestration.
adforge UI at <http://localhost:5173> for the friendly product view.

## Skills — the knowledge layer (`.claude/skills/`)

Skills are how Claude Code knows what to do in this repo. Each skill is a
folder with a `SKILL.md` (frontmatter `name` + `description` + body). Claude
loads them on demand based on what you ask.

The whole forge runs on three verbs: **MAKE** new pipelines, **ITERATE** on
existing ones, **RUN** them. A fourth class — **STEER** — is the domain
knowledge that helps Claude make good calls inside the other three.

### MAKE — scaffold new pipelines

- **`new-pipeline`** — given a one-paragraph spec, scaffolds a Temporal
  workflow + activities + `PipelineSpec` registry entry + runner branch.
  Five files, mechanical. Restart the worker and the new pipeline appears
  in the UI / CLI / API automatically.

### ITERATE — turn feedback into the next config

- **`iterate`** — reads open feedback under `runs/`, proposes a new
  `PipelineConfig` (and optionally one activity-file branch) that addresses
  it, validates the registry, runs the new config, and closes the feedback
  by linking the addressing run. The hypothesis it's testing goes into the
  config's `description` — that's the lab notebook.

### RUN — invoke the pipelines

- **`creative-forge`** — `creative_forge` Temporal workflow against a
  project: SensorTower → ranked patterns → `brief.md` + `scenario_prompt.txt`.
- **`playable-forge`** — `playable_forge` Temporal workflow: project's
  gameplay video + assets → single-file HTML playable + parameter variants.
- **`scenario-generate`** — drive Scenario MCP for ad assets (still images
  AND image-to-video animation). Pairs with the brief from `creative-forge`.
- **`sensortower-research`** — standalone helper for raw market intelligence
  (top advertisers, top creatives, app metadata). Bundles the API reference
  as `REFERENCE.md` next to the skill so it's self-contained.
- **`inline-html-assets`** — collapse a multi-file HTML playable's external
  references into a single self-contained file under 5 MB.

### STEER — the domain rubrics

- **`playable-ad-design`** — full playbook for what makes a great playable
  (hook archetypes, beat map, juice, audio, palette, CTA, variation
  strategy, technical constraints, case studies, the 15-point checklist).
  Consult before designing or judging a playable.
- **`video-ad-design`** — full playbook for what makes a great video ad
  (1.7-second rule, beat map, pacing, tone of voice, sound, on-screen
  text, end-card, variation, production tiers, case studies, the
  20-point checklist). Consult before designing or judging a brief.

### Adding a skill

```bash
mkdir .claude/skills/<name>
$EDITOR .claude/skills/<name>/SKILL.md
```

Frontmatter format:

```yaml
---
name: <skill-name>
description: <one-paragraph trigger — be specific about WHEN this skill applies>
---
```

Claude Code re-reads `.claude/skills/` on each session, so a new skill is
live the next time you reload. Use the `skill-creator` skill if you want
guided help authoring one.

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

# Iteration loop
uv run adforge feedback ls                         # open feedback across runs
# ...then in Claude Code: /iterate
```

## Useful links

- AppLovin Playable Preview: <https://p.applov.in/playablePreview?create=1>
- Scenario MCP install: <https://mcp.scenario.com/?agent=claude-code&auth=oauth>
- Temporal local dev: `temporal server start-dev` → <http://localhost:8233>
- SensorTower API reference: `.claude/skills/sensortower-research/REFERENCE.md`
