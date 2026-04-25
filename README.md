# adforge

> Build ads for your games, faster.

You define a **project** (everything you know about a game). You pick a
**pipeline** (a recipe). You get a **run** (a self-describing folder of
artifacts). Each pipeline has named **configs** you can A/B as you iterate.

```
   PROJECT ─────────►   PIPELINE ─────────►   RUN
   (a game)             (a recipe)            (an output)

   projects/<id>/                             runs/<run_id>/
   ├ project.json       creative_forge ──┐    ├ manifest.json
   ├ video.mp4          playable_forge ──┘──► ├ brief.md
   ├ assets/                                  ├ playable.html
   └ description, …                           └ patterns.json
```

Built for VoodooHack (Paris, Apr 26–27 2026). Two pipelines today:

- `creative_forge` — Track 3, the **video-ad** pipeline (web research → market insights → storyboard → AI-generated video creative).
- `playable_forge` — Track 2, the **playable** pipeline (video + assets → single-file HTML playable + variants).

## Top-down layout

```
adforge/
├── projects/         INPUTS.   one folder per game (project.json + optional video.mp4 + assets/)
├── runs/             OUTPUTS.  one folder per execution (manifest.json + artifacts)
├── src/adforge/      FORGE.    config → connectors → activities → pipelines → cli + api
├── ui/               VIEWER.   Vite + React + Tailwind. Reads the API.
├── docs/             notes
├── .env / .env.example
└── pyproject.toml
```

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

# 5) kick off a pipeline against a project
uv run adforge run creative --project castle_clashers
uv run adforge run playable --project castle_clashers --config default
```

The UI is the friendly view. The Temporal Web UI at <http://localhost:8233>
is the orchestration debugger. Every run deep-links between the two.

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

## Pipelines + configs

Each pipeline has named **configs** — presets that swap models, prompts, or
code paths. Add new ones in `src/adforge/pipelines/__init__.py`. Pick one with
`--config` (CLI) or via the dropdown on the project detail page (UI).

```bash
uv run adforge tools pipelines              # list pipelines + their configs
uv run adforge run creative --project castle_clashers --config default
```

Iterate fast: clone `default` to `claude-prose`, swap the activity, ship a new
config. Old runs stay reproducible — their `config_id` is in the manifest.

## Standalone tools

```bash
uv run adforge tools env                              # resolved settings
uv run adforge tools projects                         # list projects
uv run adforge tools projects castle_clashers        # show one
uv run adforge tools pipelines                        # list pipelines + configs
uv run adforge tools runs                             # list runs
uv run adforge tools runs <run_id>                   # show one manifest
uv run adforge tools st-search "royal match"          # SensorTower
uv run adforge tools inline runs/<run_id>/playable.html
```

## Skills (Claude Code)

In `.claude/skills/`. Invoke with the Skill tool inside Claude Code:
`creative-forge`, `playable-forge`, `sensortower-research`, `inline-html-assets`,
`scenario-generate`.

## Hackathon rules

- Playable: ≤ 5 MB single HTML, no external deps, mobile browser
- ≥ 75% AI-written
- Test on <https://p.applov.in/playablePreview?create=1> before submitting

## Credits

Hackathon keys live in `.env` (gitignored). Provided by Voodoo: `GEMINI_API_KEY`,
`SENSORTOWER_API_KEY`, `SCENARIO_*` (via MCP OAuth). 40 USD of Anthropic credits.
Mistral credits used by `creative_forge` for cheap per-creative labeling.
