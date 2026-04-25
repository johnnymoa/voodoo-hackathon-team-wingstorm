# adforge

> A forge for AI ad pipelines — open it in Claude Code and enter the loop.

```
   PROJECT ─────►   PIPELINE ─────►   RUN ─────►   FEEDBACK ─────►   /iterate ─────►   …
   (a game)         (a recipe)        (an output)   (your notes)       (a new config)
```

You drop a game into `projects/`, run a pipeline, look at the artefacts in
`runs/<run_id>/`, write feedback in the UI, then ask Claude Code to
**`/iterate`** — it ships a new `PipelineConfig` that addresses the feedback
and runs it. You compare. You repeat. Each pipeline is a Temporal workflow;
each config is a labeled experiment with a hypothesis you can `git log`.

## Layout

```
adforge/
├── projects/         INPUTS.    one folder per game
├── runs/             OUTPUTS.   manifest.json + artefacts + feedback.md per run
├── src/adforge/      FORGE.     Python — config → connectors → activities → pipelines → cli + api
├── ui/               VIEWER.    Vite + React + Tailwind — also where you write feedback
├── .claude/skills/   KNOWLEDGE. domain skills + iteration recipes Claude Code loads on demand
├── .env / .env.example
└── pyproject.toml
```

That's the whole repo. No `docs/` — the knowledge lives in skills.

## Setup

```bash
uv sync                          # python deps
cp .env.example .env             # fill in keys
brew install temporal            # macOS — or: curl -sSf https://temporal.download/cli.sh | sh
```

## Run

```bash
# 1) Temporal local dev          → http://localhost:8233
temporal server start-dev

# 2) adforge worker (hosts activities + workflows)
uv run adforge worker

# 3) FastAPI shim (powers the UI) → http://127.0.0.1:8765
uv run adforge api

# 4) Vite UI                      → http://localhost:5173
cd ui && npm install && npm run dev

# 5) kick off a pipeline (or use the Run button in the UI)
uv run adforge run creative --project castle_clashers
uv run adforge run playable --project castle_clashers --config default
```

The UI is the friendly view. The Temporal Web UI at <http://localhost:8233>
is the orchestration debugger. Every run deep-links between the two.

## The iteration loop

```
run → inspect artefacts → write feedback → /iterate → compare → repeat
```

1. **Run** a pipeline (UI button or CLI).
2. **Inspect** the artefacts in `runs/<run_id>/`.
3. **Leave feedback** in the Run page — saves to `runs/<run_id>/feedback.md`
   with frontmatter (`status: open`, `created_at`, …).
4. In Claude Code, run **`/iterate`**. The skill reads open feedback, proposes
   a new `PipelineConfig`, edits the registry (and optionally one activity),
   runs it, marks the feedback fulfilled with a link to the addressing run.
5. **Compare** the original and new runs in the UI.

Need a brand-new pipeline (not just a config tweak)? Run **`/new-pipeline`**
and Claude scaffolds the workflow + activities + registry entry.

```bash
uv run adforge feedback ls               # what's open across runs
uv run adforge feedback show <run_id>    # full body + frontmatter
uv run adforge feedback close <run_id> --by-run <new> --by-config <cfg>  # /iterate calls this
```

## Adding a project

A project is a folder with a `project.json` inside. The minimum is one line:

```bash
mkdir -p projects/royal_match
echo '{"name":"Royal Match"}' > projects/royal_match/project.json
```

Optional fields help pipelines do better work — none are required:

```json
{
  "name":        "Royal Match",
  "genre":       "match-3",
  "description": "Match-3 puzzle with king-saving meta-narrative.",
  "category_id": "7012",
  "country":     "US",
  "store_urls":  { "ios": "https://apps.apple.com/..." }
}
```

Drop `video.mp4` and `assets/` next to it if you want to run `playable_forge`.

## Skills (the knowledge layer)

`.claude/skills/` is where the intelligence lives. Three verbs run the
forge — **make** new pipelines, **iterate** on them, **run** them — plus
a fourth class of skills that **steer** Claude's design choices.

**MAKE** — scaffold new pipelines:
- `new-pipeline` — from a one-paragraph spec, scaffolds workflow + activities
  + registry entry + runner branch.

**ITERATE** — turn feedback into the next config:
- `iterate` — reads open `feedback.md`, ships a new `PipelineConfig` (and
  optionally one activity-file branch), runs it, closes the feedback.

**RUN** — the pipelines and their helpers:
- `creative-forge` — project → market patterns → brief + Scenario prompt.
- `playable-forge` — project (with video) → single-file HTML playable + variants.
- `scenario-generate` — drive Scenario MCP for images AND image-to-video.
- `sensortower-research` — raw market intelligence (full API reference bundled inside the skill).
- `inline-html-assets` — collapse a multi-file playable into one self-contained file.

**STEER** — the design rubrics Claude consults when designing or judging:
- `playable-ad-design` — full playbook for high-performing playables
  (hooks, beat map, juice, technical constraints, case studies, checklist).
- `video-ad-design` — full playbook for high-performing video ads
  (1.7-second rule, beat map, tone, sound, end-card, variation, case studies).

A skill is a folder with a `SKILL.md`. To add one:

```bash
mkdir .claude/skills/<name>
$EDITOR .claude/skills/<name>/SKILL.md
```

Frontmatter format:

```yaml
---
name: <skill-name>
description: <one paragraph — be specific about WHEN this skill applies>
---
```

## Hackathon rules

- Playable: ≤ 5 MB single HTML, no external deps, mobile browser
- ≥ 75% AI-written
- Test on <https://p.applov.in/playablePreview?create=1> before submitting

## Credits

Hackathon keys live in `.env` (gitignored). Provided by Voodoo: `GEMINI_API_KEY`,
`SENSORTOWER_API_KEY`, `SCENARIO_*` (via MCP OAuth). 40 USD of Anthropic credits.
Mistral credits used by `creative_forge` for cheap per-creative labeling.
