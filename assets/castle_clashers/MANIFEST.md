# Castle Clashers — provided assets

Hackathon asset kit for Track 2. Total ~3 MB unpacked.

## Images (PNG, ready to inline)

| File | Purpose | Approx size |
|---|---|---|
| `Background.png` | Battlefield backdrop | 1.1 MB |
| `red_castle.png` | Player castle | 180 KB |
| `blue_castle.png` | Enemy castle | 185 KB |
| `Weapon_1.png` | Weapon variant A | 14 KB |
| `Weapon_2.png` | Weapon variant B | 13 KB |
| `Projectile_1.png` | Arrow / fireball A | 25 KB |
| `Projectile_2.png` | Arrow / fireball B | 41 KB |

## Audio (inlineable but heavy — drop or compress for size budget)

| File | Purpose | Approx size |
|---|---|---|
| `Music.ogg` | Background loop | 216 KB |
| `Sfx.wav` | Hit / impact SFX | 489 KB — compress to OGG before inlining |

## Characters (Photoshop Big format — NOT browser-loadable)

`Character_Cyclop.psb`, `Character_Orc.psb`, `Character_Skeleton.psb`.

`.psb` is a layered Photoshop file. Browsers can't render it. Options:

1. **Export to PNG** in Photoshop / Photopea (open file → File → Export As → PNG).
   Each psb likely has multiple layers — export the silhouette/idle frame for the
   prototype.
2. **Generate a substitute** via Scenario MCP using a prompt like
   `"orc warrior side-view sprite, transparent background, pixel art, 256x256"`.
3. **Use simple shapes** in canvas if visual fidelity isn't load-bearing for the
   slice.

For the 30-second playable, option 2 (Scenario substitute) or option 3 (canvas
shapes) is usually the fastest path. The .psb files are kept here for reference
and for the export-by-hand fallback.

## Notes on size

Inlining everything as base64 takes ~4 MB before any code, leaving very little
headroom under the 5 MB cap. Pick a subset:

- **Lean kit** (recommended starting point): `Background` (downscaled to 1080×1920),
  one castle, one projectile, one weapon, no audio. ~600 KB.
- **Polished kit**: full PNG set + compressed `Music.ogg` only (drop the WAV).
  ~1.7 MB after Pillow downscale.

```bash
# downscale Background to 1080-wide and re-save:
python -c "from PIL import Image; im=Image.open('assets/castle_clashers/Background.png'); im.thumbnail((1080,1920)); im.save('assets/castle_clashers/Background_1080.png', optimize=True)"

# convert WAV → OGG @ 64kbps mono (saves ~80%):
ffmpeg -i assets/castle_clashers/Sfx.wav -ac 1 -b:a 64k assets/castle_clashers/Sfx.ogg
```
