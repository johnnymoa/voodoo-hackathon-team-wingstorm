---
name: iterate
description: Read open feedback under runs/, propose a new PipelineConfig that addresses it, edit src/adforge/pipelines/__init__.py (and optionally one activity file), kick off the new config against the same project, and mark the feedback fulfilled. Use when the user says "/iterate", "iterate on this run", "address my feedback", "propose a new config", or wants to scientifically improve a pipeline based on saved feedback notes. The iteration loop in adforge: run → inspect → leave feedback in the UI → /iterate in Claude Code → compare.
---

# iterate — turn feedback into a new PipelineConfig

You're picking up where the user left off. They ran a pipeline, looked at the
artefacts, and wrote feedback in the Run page's Feedback panel — saved as
`runs/<run_id>/feedback.md` with `status: open`. Your job is to ship a new
`PipelineConfig` that addresses one open feedback item, kick off a comparison
run, and mark the feedback fulfilled.

This is the iteration loop. Keep it tight, scientific, and reversible.

## The recipe

### 1. Find open feedback

```bash
uv run adforge feedback ls
```

If the user named a specific run, use that. If multiple are open, pick the
most recent unless the user steers you. If `feedback ls` is empty, ask the
user what they want to iterate on — don't invent feedback.

### 2. Gather context

Read just enough to form a hypothesis. Don't dump the whole repo into
context.

- The pipeline source: `src/adforge/pipelines/<pipeline_id>.py`
- The registry: `src/adforge/pipelines/__init__.py`
- The activity file most likely related to the feedback (one or two —
  start with the one whose output the feedback complains about)
- The run's manifest: `runs/<run_id>/manifest.json`
- One key text artefact: the brief (`brief.md`), the playable HTML's
  `CONFIG` block, or `patterns.json` summary — whichever is most diagnostic
- The feedback body — `uv run adforge feedback show <run_id>`
- Connector inventory: `src/adforge/connectors/` (gemini, claude, mistral,
  sensortower, scenario)

### 3. Form a hypothesis

One sentence. Examples:

- *"Brief is too generic — using Claude instead of Mistral for pattern labeling should produce more specific, evocative hooks."*
- *"Playable's CONFIG produces too-easy waves — bumping `enemySpeed` by 40% and tightening `spawnEverySeconds` should match the video's pacing."*
- *"Patterns extraction misses opening-hook structure — adding a Gemini second-pass that looks specifically at the first 2s of each ad should surface it."*

Write the hypothesis verbatim into the new config's `description`. That's
the paper trail — future-you will compare runs and read those descriptions
to decide what worked.

### 4. Edit `src/adforge/pipelines/__init__.py`

Add ONE new `PipelineConfig` to the relevant `PipelineSpec.configs` list.

- `id`: short, encodes what's different. `claude-prose-brief`,
  `aggressive-cta`, `gemini-opening-hook-pass`. Avoid generic names like
  `v2` or `experimental`.
- `name`: short display label.
- `description`: your hypothesis (one sentence).
- `params`: the override dict the activity will read.

Don't touch `default`. Don't delete existing configs.

### 5. Optionally edit ONE activity file

If `params` alone aren't enough, branch on `inp.config_id` inside one
activity under `src/adforge/activities/`. Pattern:

```python
if inp.config_id == "claude-prose-brief":
    # new behavior
else:
    # existing default
```

Keep edits minimal. Don't rewrite functions; add a branch. Don't touch the
workflow file in `src/adforge/pipelines/<name>.py`.

### 6. Validate

```bash
uv run python -c "from adforge.pipelines import PIPELINES, find_config; assert find_config('<pipeline_id>', '<new_config_id>') is not None; print('ok')"
```

If it fails, fix and re-validate before moving on.

### 7. Restart the worker

The worker has the OLD pipelines loaded in memory. The user must restart it
for activity-branch edits to take effect:

```bash
# in the worker terminal:
^C
uv run adforge worker
```

Tell the user. If you only added a config (no activity edit), the worker
restart is still needed because the registry is read on import.

### 8. Run the new config

```bash
uv run adforge run <pipeline-short> --project <project_id> --config <new_config_id>
```

Where `<pipeline-short>` is `creative` or `playable`. Capture the run_id
this prints (or get it from `uv run adforge tools runs | head`).

### 9. Close the feedback

```bash
uv run adforge feedback close <original_run_id> \
  --by-run <new_run_id> \
  --by-config <new_config_id>
```

This sets `status: fulfilled` and links the iteration. The original
feedback file becomes the audit record of what changed and why.

### 10. Summarize for the user

In ~5 lines:

- Hypothesis (one sentence)
- What you changed (file paths + a one-line diff summary)
- The new run_id, with a link to inspect: `http://localhost:5173/runs/<run_id>`
- "Restart the worker if you haven't" — explicit reminder
- Suggest a comparison: open the original run and the new run side-by-side

## Edit safety — hard rules

- **Touchable:** `src/adforge/pipelines/__init__.py` and ONE file under
  `src/adforge/activities/`. Nothing else.
- **Don't touch** workflows in `src/adforge/pipelines/<name>.py`. Activity
  swapping is the surface; workflow changes are out of scope.
- **Don't delete** existing configs or rewrite existing logic. Add, don't
  rewrite.
- **One config per iteration.** If the feedback wants two unrelated changes,
  do two iteration cycles.
- Always validate the registry imports cleanly before stopping.

## Finish the job — or escalate, don't fake-fulfill

This is the most important rule of the loop:

**Closing a feedback as `fulfilled` is a contract** that the new run actually
delivers what the feedback asked for. If you can't deliver that, **leave the
feedback `open`** and tell the user what's missing. Half-fixes that get
closed as fulfilled poison the lab notebook — every future search for "what
worked for X" will surface a config that didn't actually work for X.

Concrete rules:

1. **Re-read the feedback before closing.** Did the user ask for video? Did
   you ship video? Did the user ask for "specific opening hooks"? Did your
   patterns.json actually contain specific opening hooks? If the answer to
   the literal ask isn't yes, do not close.
2. **The new run must complete successfully** before you close. A run that
   crashed mid-way doesn't fulfill anything. Watch the worker log; check
   the manifest's `status` field is `completed`.
3. **Visually inspect the output.** Don't just trust that the activity ran
   — open the artefact (brief.md, playable.html, the rendered image/video)
   and confirm it matches the feedback's intent.

If the feedback can't be fulfilled within iterate's edit surface (registry
+ one activity), **escalate**:

- **Wants behavior the pipeline can't express** (e.g. *"generate a video"*
  when the workflow has no video step) → run **`/new-pipeline`** to scaffold
  a new pipeline that does. Or explicitly add it as a new activity + a
  workflow edit (call this out — workflow edits are normally off-limits).
- **Wants a new connector** (service not yet wired up) → flag it; stop;
  ask the user whether to add the connector first.
- **Wants something the connector doesn't currently do** (e.g. Scenario
  text-to-image is wired but the user wants image-to-video) → extend the
  connector + add the activity branch + close *only if the new run
  produces what was asked*.

In all cases, **tell the user before you ship**: "this iteration needs to
exceed scope — I'm going to add a new activity + edit the workflow once /
spin up a new pipeline / extend the connector. ETA N minutes." Don't
silently expand scope.

## When to push back instead of editing

- Feedback is too vague (*"make it better"*, *"this is bad"*) — ask the user
  to sharpen it. What specifically failed? What would good look like?
- The default config already does what the feedback asks for — say so.
  Don't create a redundant config; suggest what to tune in the project or
  the prompt instead.

## Useful one-liners

```bash
uv run adforge feedback ls                      # open feedback across runs
uv run adforge feedback ls --all                # include closed
uv run adforge feedback show <run_id>           # full body + frontmatter
uv run adforge tools pipelines                  # registry summary
uv run adforge tools runs <run_id>              # one run's manifest
```

The Run page in the UI (`http://localhost:5173/runs/<run_id>`) shows
artefacts and lets the user write more feedback if you ask follow-up
questions.
