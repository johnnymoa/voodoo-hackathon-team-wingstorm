---
name: playable-forge
description: Run the playable_forge Temporal workflow against a project — gameplay video + assets → single-file HTML playable + parameter variants. Use when the user says "make a playable from this project", "generate a playable for Castle Clashers", "build me an interactive ad", or has a project with video.mp4 and wants the HTML out. Skip if they only want to tweak an existing playable's CONFIG block — use `inline-html-assets` and edit the file directly. Pairs with `playable-ad-design` (the design rubric) and `iterate` (turn feedback into a new config preset).
---

# playable-forge — project → playable HTML + variants

Temporal workflow that produces a single-file HTML playable < 5 MB plus N
parameter variants, driven by Gemini's structured analysis of the gameplay
video. Reads input from `projects/<id>/`, writes output to `runs/<run_id>/`.

## Prereqs (check before running)

- `temporal server start-dev` is running (Web UI: <http://localhost:8233>)
- `uv run adforge worker` is running in another terminal
- The project has a `video.mp4` (and optionally an `assets/` folder) at
  `projects/<project_id>/`. Verify with:

```bash
uv run adforge tools projects <project_id>
```

If Temporal isn't up, point the user there first. If the project is missing
a video, the workflow refuses to start with a helpful error.

## Run

From the UI Run button, or:

```bash
uv run adforge run playable --project castle_clashers --config default --variants 4
```

The default config is in `src/adforge/pipelines/__init__.py`. Add new
configs there (or use `/iterate` to do it from feedback).

## What the workflow does

1. **`analyze_gameplay_video`** — Gemini 2.5 Pro returns structured JSON
   (entities, actions, palette, configurable_parameters, asset_needs,
   first_3_seconds, cta).
2. **`build_playable_html`** — copies `templates/playable_template.html`,
   rewrites the `CONFIG` block with values from the analysis (palette,
   win/lose conditions, suggested params).
3. **`inline_html_assets`** — if the project has an `assets/` dir,
   collapses every local `<img src>`, `<audio src>`, `<link rel=stylesheet>`,
   `<script src>`, and CSS `url(...)` into base64 data URLs.
4. **`generate_variations`** — emits N HTML variants by overriding `CONFIG`.
5. **`finalize_run`** — writes `manifest.json` and stamps the run.

Watch it execute in the Temporal Web UI — retries, durations, and any
failed activity surface immediately.

## Output

```
runs/<run_id>/
├── manifest.json                      ← what the UI reads
├── playable.html                      ← base, CONFIG injected from analysis
├── playable__easy.html                ← variants from CLI defaults:
├── playable__hard.html                  cli.py::run_playable's _DEFAULT_PLAYABLE_VARIANTS
├── playable__speedrun.html
└── playable__neon.html
```

## When the size budget breaks (> 5 MB)

The build activity reports `size_mb`. If it's over 5:

- Downscale background images (use Pillow):
  ```python
  from PIL import Image
  Image.open("p.png").thumbnail((1080, 1920))
  ```
- Drop or compress audio: `ffmpeg -i in.wav -ac 1 -b:a 64k out.ogg`
- Replace inlined sprites with procedurally-drawn shapes in the canvas loop

Re-run the workflow — it's idempotent (new `run_id` per run).

## CONFIG knobs (the variant surface)

The `CONFIG` block in `templates/playable_template.html` exposes:

- **pacing**: `sessionSeconds`, `spawnEverySeconds`, `difficultyRamp`
- **entities**: `enemyCount`, `enemyHp`, `enemySpeed`
- **player**: `playerDamage`, `tapRadius`
- **win/fail**: `winScore`, `failOnEscape`
- **visuals**: `palette`
- **CTA**: `ctaText`, `showCtaAfterScore`, `showCtaAfterMs`

Variants live in `src/adforge/cli.py::_DEFAULT_PLAYABLE_VARIANTS` (and in
`src/adforge/runner.py` for UI-launched runs). Add knobs there, or use
`/iterate` to ship a new `PipelineConfig` with a different variant set
without touching the CLI.

## Test before claiming done

> Open <https://p.applov.in/playablePreview?create=1>, upload the HTML,
> scan the QR with your phone. Confirm: (a) input works on touch, (b) CTA
> fires, (c) no console errors, (d) loads in < 3s.

Then write feedback in the Run page and run `/iterate` to ship the next
config. Use `playable-ad-design` as the design rubric — it has the 5-question
quality check and the variant strategy.
