# videos/

Drop gameplay videos here. Used as input to `playable_forge` and `full_forge`.

```
videos/
├── castle_clasher.mp4    # Track 2 reference
└── <other>.mp4
```

Video files (.mp4, .mov, .webm, .gif) are gitignored — they're large and we
don't want them in history. The directory itself is tracked via `.gitkeep`.

Run a pipeline against one:

```bash
uv run adforge run playable --video videos/castle_clasher.mp4 --assets assets/castle_clashers
uv run adforge run full     --video videos/castle_clasher.mp4 --target "castle clasher" --assets assets/castle_clashers
```
