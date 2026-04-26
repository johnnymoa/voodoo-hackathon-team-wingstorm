# adforge

> A forge for AI-driven ad pipelines, built live at the Voodoo x Anthropic hackathon.

```
   PROJECT ─────►   PIPELINE ─────►   RUN ─────►   FEEDBACK ─────►   /iterate ─────►   …
   (a game)         (a recipe)        (an output)   (your notes)       (a new config)
```

You drop a game into `projects/`, run a pipeline, look at the artefacts in
`runs/<run_id>/`, write feedback in the UI, then ask Claude Code to
**`/iterate`** — it ships a new `PipelineConfig` that addresses the feedback
and runs it. You compare. You repeat. Each pipeline is a Temporal workflow;
each config is a labeled experiment with a hypothesis you can `git log`.

## What we built

adforge is an **AI-native ad production system** built in 48 hours. The idea:
instead of manually briefing artists and iterating through Slack, you describe
a game, point the forge at market data, and let AI pipelines produce playable
ads and video creatives — then iterate on them conversationally.

**Two pipelines ship by default:**

- **`creative_forge`** — pulls real SensorTower market intelligence, extracts
  winning creative patterns, generates an AI brief with charts and rationale,
  then drives Scenario's Seedance model to render video ad scenes.
- **`playable_forge`** — analyzes gameplay video with Gemini, authors a
  single-file HTML5 playable ad (< 5 MB, no external deps, mobile-first),
  inlines all assets as base64, and generates CONFIG-based parameter
  variations for A/B testing.

The whole system is orchestrated by **Temporal** (durable workflows, automatic
retries, observable state) and wrapped in a **Vite + React UI** for inspecting
runs, viewing artefacts, and writing feedback that drives the next iteration.

## AI-built disclaimer

This project was built almost entirely with AI assistance. The codebase,
pipelines, skills, playable ads, video creatives, briefs, and this README
were authored collaboratively between the team and Claude Code (Anthropic).
Scenario's Seedance 2.0 generated the video ad content. Gemini 2.5 Pro
analyzed gameplay footage. SensorTower provided the market intelligence data.

The playable HTML files are AI-generated single-file applications — they
represent a compressed creative interpretation of each game, not the actual
game. The forge is the scaffold; the AI is the craftsperson.

## Layout

```
adforge/
├── projects/         INPUTS.    one folder per game (gitignored — add your own)
├── runs/             OUTPUTS.   manifest.json + artefacts + feedback.md per run
├── src/adforge/      FORGE.     Python — config → connectors → activities → pipelines → cli + api
├── ui/               VIEWER.    Vite + React + Tailwind — inspect runs and write feedback
├── .claude/skills/   KNOWLEDGE. domain skills + iteration recipes Claude Code loads on demand
├── .env.example
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
uv run adforge run creative --project <your_game>
uv run adforge run playable --project <your_game> --config default
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
uv run adforge feedback close <run_id> --by-run <new> --by-config <cfg>
```

## Adding a project

A project is a folder with a `project.json` inside. The minimum is one line:

```bash
mkdir -p projects/my_game
echo '{"name":"My Game"}' > projects/my_game/project.json
```

Optional fields help pipelines do better work — none are required:

```json
{
  "name":        "My Game",
  "genre":       "puzzle",
  "description": "A puzzle game with satisfying chain reactions.",
  "category_id": "7012",
  "country":     "US"
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
- `sensortower-research` — raw market intelligence (full API reference bundled).
- `inline-html-assets` — collapse a multi-file playable into one self-contained file.

**STEER** — the design rubrics Claude consults when designing or judging:
- `playable-ad-design` — full playbook for high-performing playables
  (hooks, beat map, juice, technical constraints, case studies, checklist).
- `video-ad-design` — full playbook for high-performing video ads
  (1.7-second rule, beat map, tone, sound, end-card, variation, case studies).

## Hackathon context

Built for the Voodoo x Anthropic hackathon (April 2026). The challenge: use
AI to produce ad creatives — playable ads and video ads — grounded in real
market intelligence.

**Tracks we targeted:**
- **Track 2 — Playable Ads**: Single-file HTML, < 5 MB, mobile browser,
  no external deps. Test on [AppLovin Preview](https://p.applov.in/playablePreview?create=1).
- **Track 3 — Market Intelligence → Creative**: Use SensorTower data to
  inform creative decisions, then produce the ad with AI.

**Stack:** Claude Code (orchestration + code generation), Gemini 2.5 Pro
(video analysis), Scenario Seedance 2.0 (video generation), SensorTower
(market data), Temporal (workflow engine), FastAPI + Vite/React (UI).

## Team

Team Wingstorm. Built with vibes, caffeine, and an unreasonable number of
Claude Code context windows.

## License

MIT
