# assets/

Drop hackathon asset kits here, one subfolder per game.

```
assets/
├── castle_clashers/        # Track 2 — provided kit (PNGs, audio, .psb characters)
│   └── MANIFEST.md         # what each file is + size budget tips
└── <other_game>/
```

Pass an asset folder to `playable_forge` / `full_forge` and the pipeline will
inline every local image, audio, CSS, and JS reference it finds in the playable
HTML as base64 — no external URLs in the final file (ad networks reject them).

```bash
uv run adforge run playable --video videos/castle_clasher.mp4 --assets assets/castle_clashers
```

## Conventions

- **Lowercase, underscore-separated** filenames — easier to reference in HTML/CSS.
- **Pre-resize images** for the size budget (5 MB total inlined). Pillow:
  ```python
  from PIL import Image
  Image.open("Background.png").thumbnail((1080, 1920)); …
  ```
- **`.psb`** (Photoshop Big) files are not browser-loadable — export to PNG in
  Photopea/Photoshop or generate a substitute via Scenario.
