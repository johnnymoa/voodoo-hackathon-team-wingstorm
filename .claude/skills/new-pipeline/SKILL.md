---
name: new-pipeline
description: Scaffold a brand-new pipeline in adforge — workflow + activities + registry entry + runner branch. Use when the user says "/new-pipeline", "make a new pipeline", "scaffold a pipeline that does X", "build a workflow for Y", or wants a whole new shape (not just a config tweak — that's /iterate). Walks through the 6-step recipe from one-paragraph spec to running code, and tells the user to restart the worker. Pairs with the iterate skill — once the pipeline exists, /iterate is how you tune it.
---

# new-pipeline — scaffold a brand-new pipeline

`/iterate` is for tuning an existing pipeline (new config, maybe one
activity edit). This skill is for adding a whole new pipeline shape — a
new Temporal workflow with new activities. Bigger surface, more files, but
the recipe is mechanical once you know it.

The forge is small enough that a complete new pipeline is usually 3-5 new
files plus 4 small edits. The harness reads from a registry, so as soon as
you save and restart the worker, your pipeline appears in the UI, the CLI,
and the API.

## The recipe — 6 steps

### 1. Get a one-paragraph spec from the user

Before touching files, write down (in conversation):

- **What input** — does it consume a project? Does it need video,
  assets, metadata?
- **What output** — what artefacts land in `runs/<run_id>/`? (e.g.
  `storyboard.md`, `keyframes/*.png`, `voiceover.mp3`)
- **What activities** — list them, one verb per activity. Each is atomic
  and retryable.
- **Which connectors** — gemini, claude, mistral, sensortower, scenario,
  or new ones?

If any of these are vague, ask the user before scaffolding. A vague spec
produces a pipeline that doesn't compose.

### 2. Add the `PipelineSpec` to the registry

Edit `src/adforge/pipelines/__init__.py`. Add an entry to `PIPELINES`:

```python
PipelineSpec(
    id="storyboard_forge",                      # workflow name + CLI subcommand
    name="Storyboard",                           # display name
    description="Project + concept → multi-frame storyboard with shot list and key art.",
    inputs=[
        PipelineInput(id="metadata", kind="metadata", description="Game name + genre — read from project.json."),
        PipelineInput(id="concept",  kind="metadata", description="One-line creative concept (passed via config or run-time arg).", required=False),
    ],
    outputs=["storyboard.md", "shot_list.json", "frames/*.png"],
    cli="adforge run storyboard --project <id>",
    configs=[
        PipelineConfig(
            id="default",
            name="Default",
            description="Claude writes the shot list, Scenario renders 6 keyframes.",
        ),
    ],
),
```

`inputs` are the things a project needs to have for the pipeline to run.
The UI shows them as required/optional pills on the project page.

### 3. Create the workflow file

`src/adforge/pipelines/<your_pipeline>.py`. Use this template — the shape
matches `playable_forge.py` and `creative_forge.py`:

```python
"""storyboard_forge — concept + project → multi-frame storyboard."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from adforge.activities.finalize import FinalizeRunInput, FinalizeRunResult
    # import your new activity input/output types here


class StoryboardForgeInput(BaseModel):
    project_id: str
    run_id: str
    run_dir: str
    config_id: str = "default"
    concept: str | None = None


class StoryboardForgeResult(BaseModel):
    run_id: str
    manifest_path: str


_RETRY = RetryPolicy(initial_interval=timedelta(seconds=2), maximum_attempts=4)


@workflow.defn(name="storyboard_forge")
class StoryboardForge:
    @workflow.run
    async def run(self, inp: StoryboardForgeInput) -> StoryboardForgeResult:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # ... call activities here, e.g.:
        # shots = await workflow.execute_activity(
        #     "draft_shot_list",
        #     ShotListInput(concept=inp.concept, project_id=inp.project_id),
        #     start_to_close_timeout=timedelta(minutes=2),
        #     retry_policy=_RETRY,
        # )

        finalized: FinalizeRunResult = await workflow.execute_activity(
            "finalize_run",
            FinalizeRunInput(
                run_dir=inp.run_dir,
                run_id=inp.run_id,
                pipeline="storyboard_forge",
                project_id=inp.project_id,
                config_id=inp.config_id,
                started_at=started_at,
                params=inp.model_dump(),
                artifact_globs=["*.md", "*.json", "frames/*.png"],
            ),
            start_to_close_timeout=timedelta(seconds=15),
        )

        return StoryboardForgeResult(
            run_id=inp.run_id,
            manifest_path=finalized.manifest_path,
        )
```

Then register it in `src/adforge/pipelines/__init__.py`:

```python
from adforge.pipelines.storyboard_forge import StoryboardForge, StoryboardForgeInput

# ...

WORKFLOWS = [PlayableForge, CreativeForge, StoryboardForge]   # ← add yours
```

### 4. Add activities under `src/adforge/activities/`

One file per logical step. Activities are atomic and retryable; each
makes IO calls and returns a typed result. Template:

```python
# src/adforge/activities/shot_list.py
from pydantic import BaseModel
from temporalio import activity


class ShotListInput(BaseModel):
    concept: str | None
    project_id: str


class ShotListResult(BaseModel):
    shots: list[dict]


@activity.defn(name="draft_shot_list")
async def draft_shot_list(inp: ShotListInput) -> ShotListResult:
    # call connectors here — claude, gemini, mistral, scenario, sensortower
    # branch on inp.config_id later when /iterate adds a new config
    ...
    return ShotListResult(shots=[...])
```

Then register the activity in `src/adforge/activities/__init__.py`:

```python
from adforge.activities.shot_list import draft_shot_list

ALL = [
    # ... existing activities,
    draft_shot_list,    # ← add yours
]
```

The worker (`src/adforge/worker.py`) hosts whatever's in `ALL`. No worker
edit needed.

### 5. Add a launcher branch in `runner.py`

Edit `src/adforge/runner.py::_build_workflow_input`:

```python
def _build_workflow_input(pipeline_id, project, run_id, run_dir, config_id):
    if pipeline_id == "playable_forge":
        # ... existing
    if pipeline_id == "creative_forge":
        # ... existing
    if pipeline_id == "storyboard_forge":                       # ← add this branch
        from adforge.pipelines.storyboard_forge import StoryboardForgeInput
        return StoryboardForgeInput(
            project_id=project.id, run_id=run_id, run_dir=run_dir, config_id=config_id,
            # any extra fields the workflow input needs
        )
    raise StartRunError(f"unknown pipeline '{pipeline_id}'")
```

Also add the short name to `_PIPELINE_SHORT` so the run_id format stays
consistent:

```python
_PIPELINE_SHORT = {
    "creative_forge": "creative",
    "playable_forge": "playable",
    "storyboard_forge": "storyboard",        # ← add yours
}
```

### 6. Validate, restart worker, run

```bash
# Validate registry imports cleanly
uv run python -c "from adforge.pipelines import PIPELINES, WORKFLOWS; from adforge.runner import start_run; print('ok')"

# Restart the worker so it picks up the new code
# (in the worker terminal): ^C, then:
uv run adforge worker

# Run it
uv run adforge run storyboard --project castle_clashers
```

The pipeline now appears in the UI Pipelines page, has a Run button on
every project page, and shows up in `uv run adforge tools pipelines`.

## Edit checklist (what files you touched)

- [ ] `src/adforge/pipelines/__init__.py` — added `PipelineSpec` + import + `WORKFLOWS` entry
- [ ] `src/adforge/pipelines/<name>.py` — new workflow file
- [ ] `src/adforge/activities/<step>.py` — one or more new activity files
- [ ] `src/adforge/activities/__init__.py` — registered new activity in `ALL`
- [ ] `src/adforge/runner.py` — added `_build_workflow_input` branch + `_PIPELINE_SHORT` entry

That's it. Five files for a new pipeline. The CLI / API / UI all update
automatically because they read from the registry.

## Hard rules

- **Workflows don't do IO directly.** All IO goes through activities. The
  workflow is pure orchestration (call activity, await result, branch).
- **Activities are atomic and retryable.** Don't make an activity that
  does 3 unrelated things — split them. Failure recovery is per-activity.
- **Use Pydantic models** for activity inputs/outputs (Temporal's pydantic
  data converter is wired up in `runner.py` and `worker.py`). Don't pass
  raw dicts.
- **Branch on `inp.config_id`** when behavior should vary across configs.
  This is what `/iterate` exploits.
- **Always call `finalize_run` last.** It writes `manifest.json`, which
  is what makes a run visible to the UI / CLI / API.

## When NOT to add a new pipeline

If the user wants something that an existing pipeline almost does, run
`/iterate` instead — add a new `PipelineConfig` to the existing pipeline.
Rule of thumb:

- **Same inputs, same outputs, different behavior** → new config, use `/iterate`.
- **Different inputs OR different outputs OR a fundamentally different
  composition of activities** → new pipeline, use this skill.

Examples:

- "Generate a video instead of an image from this brief" — same inputs
  (project + brief), same composition (research → brief → render), different
  render activity. **Config** (with the new config branching the render
  activity).
- "Generate a storyboard instead of a single creative" — different output
  (multi-frame), different composition (storyboarding step is new).
  **New pipeline.**
- "Score creatives against historical winners" — different output
  (scores), different inputs (you need historical data). **New pipeline.**

## Hand-off back to /iterate

Once your new pipeline runs end-to-end with its `default` config, you're
back in the iteration loop. Run it, leave feedback in the UI, and
`/iterate` to ship a `claude-prose` or `gemini-vision-pass` config. The
new pipeline is now part of the forge.
