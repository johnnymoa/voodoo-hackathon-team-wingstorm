---
name: playable-forge
description: Run the playable_forge Temporal workflow. Turn a gameplay video into a single-file HTML playable + variants. Use when the user says "make a playable from this video", "generate a playable for Castle Clasher", "build me an interactive ad", or hands you an mp4 and asks for an ad. Skip if they only want to tweak an existing playable's CONFIG — use `inline-html-assets` and edit the file directly.
---

# playable_forge — video → playable HTML

Temporal workflow that produces a single-file HTML playable < 5 MB plus N variations,
driven by Gemini's structured analysis of the gameplay video.

## Prereqs (check before running)

- `temporal server start-dev` is running (web UI at http://localhost:8233)
- `uv run adforge worker` is running in another terminal
- A gameplay video at `videos/<file>.mp4`

If Temporal isn't up, point the user there first.

## Run

```bash
uv run adforge run playable \
  --video videos/castle_clasher.mp4 \
  --assets assets/castle_clashers \
  --variants 4
```

Outputs land in `output/playables/<run_id>/`:
- `playable.html` (base, CONFIG injected from analysis)
- `playable__easy.html`, `playable__hard.html`, `playable__speedrun.html`, `playable__neon.html`

## What the workflow does

1. **`analyze_gameplay_video`** — Gemini 2.5 Pro returns structured JSON (entities, actions, palette, configurable_parameters, asset_needs, first_3_seconds, cta).
2. **`build_playable_html`** — copies `templates/playable_template.html`, rewrites the `CONFIG` block with values from the analysis (palette, win/lose conditions, suggested params).
3. **`inline_html_assets`** — if `--assets` was given, collapses every local `<img src>`, `<audio src>`, `<link rel=stylesheet>`, `<script src>`, and CSS `url(...)` into base64 data URLs.
4. **`generate_variations`** — emits N HTML variants by overriding `CONFIG`.

Watch it execute in the Temporal Web UI — retries, durations, and any failed activity surface immediately.

## When the size budget breaks (> 5 MB)

The build activity reports `size_mb`. If it's over 5:
- Downscale background images: `python -c "from PIL import Image; Image.open('p.png').thumbnail((1080,1920)); ..."`
- Drop or compress audio (`ffmpeg -i in.wav -ac 1 -b:a 64k out.ogg`)
- Replace inlined sprites with procedurally-drawn shapes in the canvas loop

Re-run the workflow — it's idempotent.

## Variants — what knobs work

The CONFIG block in `templates/playable_template.html` exposes:
- pacing: `sessionSeconds`, `spawnEverySeconds`, `difficultyRamp`
- entities: `enemyCount`, `enemyHp`, `enemySpeed`
- player: `playerDamage`, `tapRadius`
- win/fail: `winScore`, `failOnEscape`
- visuals: `palette`
- CTA: `ctaText`, `showCtaAfterScore`, `showCtaAfterMs`

Pass new variants by editing the CLI defaults (in `src/adforge/cli.py::run_playable`) or
by writing a JSON file and feeding it via the worker (extend the CLI if needed).

## Test before claiming done

> Open https://p.applov.in/playablePreview?create=1, upload the HTML, scan the QR
> with your phone. Confirm: (a) input works on touch, (b) CTA fires, (c) no
> console errors, (d) loads in < 3s.

## Pair with `creative-forge` for the killer demo

If the user wants the merged Voodoo demo (market-informed playable), don't run this
directly — run `full-forge` instead. It runs `creative_forge` first, then feeds the
top-ranked hook / palette / CTA into this pipeline as `market_patterns`.
