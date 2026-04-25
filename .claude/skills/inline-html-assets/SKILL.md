---
name: inline-html-assets
description: Take an HTML playable that references local images/audio/scripts/CSS and rewrite all of them as inline base64 / data URLs so the result is a single self-contained file. Use when the user says "make this a single file", "inline the assets", or hands you a playable + folder and wants one file under 5 MB. Skip if the file already has no external references.
---

# inline-html-assets

Turn a multi-file prototype into a single-file playable that meets ad-network rules.
This is also called automatically by the `playable_forge` workflow when `--assets`
is passed — only invoke this skill standalone for one-offs.

## Run

```bash
uv run adforge tools inline path/to/playable.html
```

In-place rewrite. Idempotent — re-running is safe.

## What it does

- inlines every local `src=`, `href=`, and `-src` attribute
- replaces `<link rel=stylesheet>` with `<style>` blocks (rewriting CSS `url(...)` too)
- replaces external `<script src>` with inline `<script>`
- warns on any `http://` / `https://` reference (ad networks reject them)
- prints final file size

## After running

If size > 5 MB:
- Downscale images with Pillow:
  ```python
  from PIL import Image
  im = Image.open("assets/Background.png"); im.thumbnail((1080, 1920))
  im.save("assets/Background_1080.png", optimize=True)
  ```
- Convert WAV → OGG: `ffmpeg -i in.wav -ac 1 -b:a 64k out.ogg`
- Replace inlined sprites with procedurally-drawn canvas shapes for non-key art
- Re-run the inliner

## When to choose this over manual base64

Always. By hand you'll miss `data-src`, CSS `url()`, and inline-style references.
