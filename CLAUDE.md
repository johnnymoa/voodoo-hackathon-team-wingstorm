# adforge — Voodoo Hack pipelines

Two composable Temporal pipelines for mobile-game ad generation:

- **`playable_forge`** — gameplay video → interactive HTML playable + variants
- **`creative_forge`** — target game → market-informed brief + Scenario prompt
- **`full_forge`** — chains both: target + video → brief + creative + market-informed playable

## Repo layout

```
pyproject.toml              uv project manifest (no requirements.txt)
.env / .env.example         API keys (Gemini, SensorTower, Claude, Mistral, Scenario)
.mcp.json                   Scenario MCP server (auth via /mcp inside Claude Code)
.claude/skills/             Skills you invoke during a session
src/adforge/
  config.py                 settings + paths
  utils.py                  small helpers (slug, run_id, data-url, size guards)
  connectors/               plain-Python clients (gemini, claude, mistral, sensortower, scenario)
  activities/               Temporal activities — atomic reusable units
  pipelines/                Temporal workflows (playable_forge, creative_forge, full_forge)
  templates/                playable_template.html (CONFIG-block driven)
  worker.py                 Temporal worker entrypoint
  cli.py                    typer CLI (`adforge worker`, `adforge run …`, `adforge tools …`)
docs/                       briefs + SensorTower API reference + Temporal setup
examples/                   reference playables (MarbleSort.html, CupHeroes.html)
assets/                     hackathon asset kits (Castle Clashers etc.)
videos/                     gameplay videos (gitignored)
output/                     generated playables, creatives, run artifacts
.cache/                     SensorTower response cache
```

## How it runs (mental model)

1. `temporal server start-dev` runs the orchestrator (single binary, no infra).
2. `uv run adforge worker` runs a long-lived worker that hosts every activity + workflow.
3. `uv run adforge run <pipeline> ...` starts a workflow execution.
4. The Temporal Web UI at http://localhost:8233 shows runs, retries, durations.

## Naming convention

We don't say "Track 2" / "Track 3" anywhere in code. The pipelines are named for
what they *do*:

| Voodoo track | adforge pipeline | Input → Output |
|---|---|---|
| Track 2 (playable ads) | `playable_forge` | `.mp4` → single-file HTML playable + variants |
| Track 3 (market intel) | `creative_forge` | game name → brief + Scenario prompt + (optional) image |
| Both, merged demo      | `full_forge`     | game + video → everything above, market-informed |

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
- **Track 3 outputs are reproducible** — every run lands in `output/creatives/<run_id>/` with `target.json`, `top_advertisers.json`, `top_creatives.json`, `patterns.json`, `brief.md`, `scenario_prompt.txt`.
- **Cached SensorTower** — `.cache/sensortower/` deduplicates calls. Bust by `rm -rf .cache/sensortower`.

## Don't do this

- Don't commit `.env` (gitignored).
- Don't load remote scripts/fonts in playables — ad networks reject them.
- Don't recreate the full game. Pick the smallest fun loop and ship it.
- Don't bypass Temporal in workflows by doing IO directly — call activities.
- Don't add a `requirements.txt` — uv owns deps via `pyproject.toml`.

## Quick commands

```bash
# install / sync deps
uv sync

# start Temporal locally (separate terminal)
temporal server start-dev   # http://localhost:8233 web UI

# run the worker (separate terminal)
uv run adforge worker

# run pipelines
uv run adforge run playable --video videos/castle_clasher.mp4 --assets assets/castle_clashers
uv run adforge run creative --target "castle clasher" --network TikTok --sample 30
uv run adforge run full     --target "castle clasher" --video videos/castle_clasher.mp4 --assets assets/castle_clashers

# standalone helpers (no Temporal needed)
uv run adforge tools env
uv run adforge tools st-search "royal match"
uv run adforge tools st-top-creatives --network TikTok --save output/top.json
uv run adforge tools inline output/playables/<run>/playable.html
```

## Useful links

- AppLovin Playable Preview: https://p.applov.in/playablePreview?create=1
- Scenario MCP install: https://mcp.scenario.com/?agent=claude-code&auth=oauth
- Temporal local dev: `temporal server start-dev` → http://localhost:8233
- SensorTower API: see `docs/sensortower_api.md`
