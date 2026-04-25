# targets/

Pipeline **inputs**. Each subfolder is one target (a game) the pipelines can run against.

```
targets/
└── <target_id>/
    ├── target.json     # required — name, app_id, store_urls, notes
    ├── video.mp4       # optional — gameplay video (gitignored, used by playable_forge / full_forge)
    ├── assets/         # optional — images / audio to inline in playables
    └── README.md       # optional — human notes about the kit
```

## Adding a target

1. Create `targets/<id>/` (lowercase, underscores). The folder name **is** the id you pass to `--target`.
2. Drop in `target.json`:
   ```json
   {
     "name": "Royal Match",
     "app_id": null,
     "store_urls": {"ios": "https://apps.apple.com/...", "android": "..."},
     "notes": "Anything useful."
   }
   ```
3. Add `video.mp4` and/or `assets/` if the pipelines you want to run need them.

## Which pipeline needs what

| Pipeline         | Needs `video.mp4` | Needs `assets/` |
|------------------|-------------------|-----------------|
| `creative_forge` | no                | no              |
| `playable_forge` | yes               | recommended     |
| `full_forge`     | yes               | recommended     |

## Running a target

```bash
uv run adforge tools targets                  # list everything
uv run adforge tools targets castle_clashers  # show one target's resolved paths

uv run adforge run creative --target castle_clashers
uv run adforge run playable --target castle_clashers
uv run adforge run full     --target castle_clashers
```
