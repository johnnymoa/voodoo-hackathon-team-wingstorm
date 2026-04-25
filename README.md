# adforge

> A single forge for ad assets.

You define a **target** (everything you know about a game). You pick a
**pipeline** (a recipe). You get a **run** (a self-describing folder of
artifacts).

```
   TARGET ──────────►   PIPELINE  ──────────►   RUN
   (a game)             (a recipe)              (an output)

   targets/<id>/                                runs/<id>/
   ├ target.json        creative_forge ──┐      ├ manifest.json
   ├ video.mp4          playable_forge ──┤───►  ├ brief.md
   ├ assets/            full_forge       ──┘    ├ playable.html
   └ description, …                             └ patterns.json
```

Built for VoodooHack (Paris, Apr 26–27 2026). Track 3 is `creative_forge`.
Track 2 is `playable_forge`. The demo win is `full_forge` — the only pipeline
where the playable is *informed* by what's winning in market right now.

## Top-down layout

```
adforge/
├── targets/                INPUTS.   one folder per game (target.json + optional video.mp4 + assets/)
├── runs/                   OUTPUTS.  one folder per execution (manifest.json + artifacts)
├── src/adforge/            FORGE.    code, top-down: config → connectors → activities → pipelines → cli + api
├── ui/                     VIEWER.   Vite + React + Tailwind. Reads runs/ + targets/ via api.py.
├── docs/                   notes
├── .env / .env.example     secrets
└── pyproject.toml          uv project manifest
```

Three top-level data buckets, one idea each. There used to be a `reference/`
folder for example playables — those moved into `src/adforge/templates/examples/`
where the playable build activity uses them as in-context.

## Setup

```bash
uv sync                          # python deps
cp .env.example .env             # fill in keys
brew install temporal            # macOS — or: curl -sSf https://temporal.download/cli.sh | sh
```

## Run

You'll want five terminals (each is a long-lived process; only the last one is per-run).

```bash
# 1) Temporal local dev server          → http://localhost:8233
temporal server start-dev

# 2) adforge worker (hosts activities + workflows)
uv run adforge worker

# 3) FastAPI shim that powers the UI    → http://127.0.0.1:8765
uv run adforge api

# 4) Vite dev server                    → http://localhost:5173
cd ui && npm install && npm run dev

# 5) kick off a workflow against a target
uv run adforge run creative --target castle_clashers
uv run adforge run playable --target castle_clashers
uv run adforge run full     --target castle_clashers
```

Open <http://localhost:5173> for the **engineering log book** view of the forge.
Open <http://localhost:8233> for the raw **orchestration debugger**. Every run
is deep-linked between the two via its `run_id` (also the Temporal `workflow_id`).

## What a target looks like

`target.json` is the kitchen-sink for everything known about a game.
The pipelines auto-pull `category_id`, `country`, `description`, `name` from it
— nothing has to be re-entered on the CLI.

```json
{
  "name":        "Castle Clashers",
  "genre":       "tower-defense / clash hybrid",
  "description": "Tap-to-defend tower-defense hybrid where players defend their castle...",
  "category_id": "7012",
  "country":     "US",
  "app_id":      null,
  "store_urls":  { "ios": "...", "android": "..." },
  "notes":       "Hackathon Track 2 reference kit."
}
```

## Adding a new target

```bash
mkdir -p targets/royal_match
$EDITOR targets/royal_match/target.json    # at minimum: { "name": "Royal Match" }
# drop video.mp4 + assets/ alongside if you want to run playable / full

uv run adforge tools targets               # confirm it shows up
uv run adforge run creative --target royal_match
```

## Standalone tools (no Temporal needed)

```bash
uv run adforge tools env                              # resolved settings
uv run adforge tools targets                          # list targets
uv run adforge tools targets castle_clashers         # show one target's details
uv run adforge tools runs                             # list runs
uv run adforge tools runs <run_id>                   # show one manifest
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
