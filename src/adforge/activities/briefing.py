"""Activity: write a creative brief and a Scenario-ready prompt.

The brief threads three sources of signal into one document:

1. **Market patterns** (Sensor Tower + Claude Haiku labels) — what's
   working in the genre right now: top hook, opening visual, mechanic,
   CTA framing, palette mood, with evidence ids.

2. **Gameplay analysis** (Gemini, when the project has a video.mp4) —
   what the game ACTUALLY is: core loop, primary input, palette, juice,
   audio cues. So the recommended concept is grounded, not generic.

3. **Available assets** (project's `assets/` folder) — what the team can
   actually use. Calling assets out by name lets the Scenario prompt and
   downstream agents reference them.

The brief follows the structure from `.claude/skills/video-ad-design/`:
hook archetype, 30-second beat map, tone of voice, end-card. The
"Defending rationale" section explicitly names the patterns + game
features that justify each creative choice — this is the explanation
layer the Track 3 brief asks for.
"""

from __future__ import annotations

import time
from pathlib import Path

from temporalio import activity

from adforge.activities.types import BriefInput, BriefResult


def _top(cats: dict, name: str, n: int = 3) -> list[str]:
    return [f"{r['value']} ({int(r['share']*100)}%)" for r in (cats.get(name) or [])[:n]]


def _first(cats: dict, name: str, default: str) -> str:
    rows = cats.get(name) or []
    return rows[0]["value"] if rows else default


def _evidence(cats: dict, name: str) -> list[str]:
    rows = cats.get(name) or []
    if not rows:
        return []
    return rows[0].get("evidence_ids", [])[:5]


def _hook_blueprint(hook: str, ga: dict | None = None) -> str:
    """Generate a hook description grounded in the actual game when possible."""
    generic = {
        "near-fail tease":            "Mid-disaster moment — character/level appears about to fail. Camera close on the action; viewer wants to know if they make it.",
        "fake-fail / wrong choice":   "Deliberately wrong move on screen — viewer wants to scream the right answer.",
        "satisfying-completion":      "Almost-resolved visual — last block dropping into place, last drop filling a glass. Sound is silent or low.",
        "pull-to-aim":                "POV finger drags across the screen, trajectory line visible.",
        "puzzle-with-bad-solution":   "Puzzle on-screen with an obviously wrong solution being attempted — bait the corrector instinct.",
        "before-after-transformation":"Split-screen: ugly/broken left, beautiful/fixed right. Viewer scrolls toward the better state.",
        "rage-bait":                  "Character making a clearly wrong choice; expression is calm. Viewer's fingers itch to take over.",
        "asmr / sensory":             "Tight macro shot, satisfying particle/sound — close-up texture, no UI, no logo.",
        "narrative-reveal":           "Open on consequence — tease the outcome before revealing the cause.",
        "humor-fail":                 "Slapstick bonk in frame 1. Cartoony recoil.",
    }.get(hook, "Strong pattern-interrupt visual; one subject filling 30-60% of frame, eye contact or clear motion.")
    if not ga:
        return generic
    first_3s = ga.get("first_3_seconds") or ""
    lose = ga.get("lose_condition") or ""
    win = ga.get("win_condition") or ""
    core = ga.get("core_loop_summary") or ""
    game_hooks = {
        "near-fail tease":            f"The player is about to lose — {lose or 'health drops to zero'}. Camera close on the action.",
        "fake-fail / wrong choice":   f"A wrong move in {core[:60] or 'the core loop'}. Viewer wants to scream the right answer.",
        "satisfying-completion":      f"Almost done — {win or 'the objective is nearly complete'}. Sound silent, then satisfying pop.",
        "narrative-reveal":           f"Open on the consequence — {lose or 'the player fails'}. Then rewind to show how it happened.",
    }
    return game_hooks.get(hook, generic)


def _asl_for_genre(genre: str | None) -> str:
    g = (genre or "").lower()
    if any(k in g for k in ("hyper-casual", "hyper casual")):  return "0.6–1.0s ASL — music-video pacing"
    if any(k in g for k in ("puzzle", "match")):               return "0.8–1.2s ASL"
    if any(k in g for k in ("strategy", "mid-core", "midcore", "tycoon", "tower")): return "1.5–2.5s ASL with cinematic holds"
    if any(k in g for k in ("survival", "cinematic", "narrative")):                 return "2.0–4.0s ASL — Last War style"
    return "1.0–1.5s ASL — casual default"


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) if items else "—"


@activity.defn(name="write_brief_and_prompt")
async def write_brief_and_prompt(inp: BriefInput) -> BriefResult:
    out = Path(inp.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cats = inp.patterns.categories
    ga = inp.gameplay_analysis or {}

    # Market signal selections
    top_hook    = _first(cats, "hook",            "near-fail tease")
    top_open    = _first(cats, "opening_visual",  "level-overview")
    top_mech    = _first(cats, "mechanic_shown",  ga.get("primary_input") or "core gameplay")
    top_cta     = _first(cats, "cta_framing",     "imperative-verb")
    top_palette = _first(cats, "palette_mood",    "saturated-cartoon")
    ev_hook     = _evidence(cats, "hook")
    ev_palette  = _evidence(cats, "palette_mood")

    # Game-grounded fields (only meaningful when video analysis ran)
    game_title       = ga.get("title") or inp.target.name
    core_loop        = ga.get("core_loop_summary") or "—"
    primary_input    = ga.get("primary_input") or "tap"
    win_cond         = ga.get("win_condition") or "—"
    lose_cond        = ga.get("lose_condition") or "—"
    first_3s_in_game = ga.get("first_3_seconds") or "—"
    cta_in_game      = ga.get("cta") or "Install Now"
    juice            = ga.get("juice") or []
    audio_cues       = ga.get("audio_cues") or []
    palette_in_game  = (ga.get("scene") or {}).get("color_palette") or []
    art_style        = (ga.get("scene") or {}).get("art_style") or ""
    asset_list       = inp.assets or []

    asl_advice = _asl_for_genre(inp.target.raw.get("genre") if isinstance(inp.target.raw, dict) else None)

    # Mechanic in plain English for the exec TL;DR (mirrors the prompt mapping below)
    _mech_human_brief = {
        "match-3": "match-3", "merge": "merge", "physics-drop": "physics drop",
        "pull-pin": "pull-pin", "tower-defense": "tower defense", "runner": "runner",
        "shoot-aim": "aim-and-shoot", "stack": "stack", "color-sort": "color sort",
        "rope-cut": "rope cut", "draw-path": "draw-path", "tap-rhythm": "tap-rhythm",
        "build-place": "build-and-place", "conquer-territory": "territory conquest",
    }.get(top_mech, top_mech.replace("-", " "))
    rationale_one_liner = (
        f"`{top_hook}` is the #1 hook in {inp.patterns.creative_count} working "
        f"creatives this period; `{top_palette}` palette dominates; CTA in "
        f"`{top_cta}` framing converts best."
    )
    risk_one_liner = (
        "Seedance won't render legible game-name text on-screen — keep the title to a clean rectangle for compositing, and the visible CTA to ≤ 3 words."
    )

    # ── brief.md ─────────────────────────────────────────────────────────
    brief = f"""# Creative brief — {inp.target.name}

> **TL;DR.** {top_hook} hook → {_mech_human_brief} mechanic → {top_palette} palette → {top_cta} CTA. **6s Seedance render, 9:16 / 720p / audio.**

## ⚡ At a glance

| | |
|---|---|
| **Concept in one line** | {top_hook} opener of {_mech_human_brief}, ending on `{cta_in_game}` |
| **Why it works** | {rationale_one_liner} |
| **Game grounding** | {core_loop[:140]}{'…' if len(core_loop) > 140 else ''} |
| **Risk** | {risk_one_liner} |
| **Asset reuse** | {len(asset_list)} project assets available to composite over Seedance output |

---

**App ID**: {inp.target.app_id}
**Publisher**: {inp.target.publisher_name or "(unknown)"}
**Format**: 9:16 vertical, 6s Seedance render (master); cuts down for TikTok / Reels / Shorts.

## 1. Market signals — what's winning in the genre

Sample size: **{inp.patterns.creative_count} top creatives**, ranked by working-creative signal (top advertiser × longevity).

| Category | Top values (% share) |
|---|---|
| Hooks | {", ".join(_top(cats, "hook")) or "—"} |
| Opening visuals | {", ".join(_top(cats, "opening_visual")) or "—"} |
| Mechanics shown | {", ".join(_top(cats, "mechanic_shown")) or "—"} |
| CTA framings | {", ".join(_top(cats, "cta_framing")) or "—"} |
| Palette mood | {", ".join(_top(cats, "palette_mood")) or "—"} |

Hook evidence (creative ids from SensorTower): `{", ".join(ev_hook) or "—"}`
Palette evidence: `{", ".join(ev_palette) or "—"}`

## 2. The game (from gameplay video analysis)

{"_No video.mp4 was provided — falling back to genre-only context._" if not ga else ""}

- **Title**: {game_title}
- **Core loop**: {core_loop}
- **Primary input**: {primary_input}
- **Win**: {win_cond}
- **Lose**: {lose_cond}
- **In-game palette**: {", ".join(palette_in_game) or "—"}
- **Art style**: {art_style or "—"}
- **First 3 seconds the game shows the player**: {first_3s_in_game}
- **Juice cues we can echo**:
{_bullet(juice[:6])}
- **Audio beats we can sync to**:
{_bullet([f"{a.get('trigger', '?')}: {a.get('feel', '?')}" for a in audio_cues[:6]])}

## 3. Available assets

The project's `assets/` folder ships:

{_bullet(asset_list[:30]) if asset_list else "_No assets folder — Seedance must invent everything visually._"}

The Scenario prompt below references these by name where possible so a future agent step (or human) can swap inlined assets into the rendered shots.

## 4. The concept

A **{top_hook}** opener using a **{top_open}** framing of the
**{top_mech}** mechanic, ending on a **{top_cta}** CTA in a
**{top_palette}** palette.

Frame 1 blueprint: {_hook_blueprint(top_hook, ga)}

## 5. Beat map (30s master, with 6s cutdown for the Seedance render)

```
0:00–0:02  HOOK             {top_hook} — {_hook_blueprint(top_hook, ga).split('.')[0]}.
0:02–0:05  SETUP / TENSION  Show the stakes — {win_cond if win_cond != "—" else "what the player wants"}.
0:05–0:10  THE MOMENT       Single most photogenic 5s of the {top_mech}; juice peaks ({", ".join(juice[:2]) or "particles, sting"}).
0:10–0:20  MONTAGE          4–8 quick cuts of variety (other levels, other facets of the same loop).
0:20–0:25  EMOTIONAL PEAK   Biggest reveal — {first_3s_in_game if first_3s_in_game != "—" else "the satisfying win"}.
0:25–0:28  CTA SETUP        Logo appears, character does final beat.
0:28–0:30  END CARD         Logo + "{cta_in_game}" + store badges. 2s static hold, screenshot-worthy.
```

ASL target: **{asl_advice}**.
Audio: cuts on beat. Open silent or with a low sting (≤ 200ms), build during montage, peak at 0:20.
On-screen text: ≤ 5 words on frame 1, max 6 words anywhere else, ≥ 64 px equivalent.
End-card holds 2s, no motion (loop-friendly).

## 6. Defending rationale

Why these specific creative choices:

- **Hook = `{top_hook}`** — #1 hook ({_top(cats, 'hook')[0] if _top(cats, 'hook') else 'n/a'}) across the working-creative-ranked sample. Evidence ids: `{", ".join(ev_hook[:3]) or "—"}`.
- **Palette = `{top_palette}`** — dominates this genre's top performers. {"Echoes the in-game palette " + str(palette_in_game[:3]) if palette_in_game else "Game palette unknown — defer to market."}
- **CTA framing = `{top_cta}`** — strongest convertor in the labeled set. In-game CTA copy: "{cta_in_game}".
- **Beat structure** follows `.claude/skills/video-ad-design/SKILL.md` §4 (the canonical 30s casual-game beat map). Front-loaded because Meta data shows 47% of value is delivered in the first 3s and TikTok drop-off begins at 1.7s.
- **Mechanic shown = `{top_mech}`** — dominates genre working creatives AND matches what the player actually does in {game_title}: {primary_input} → {win_cond}.

— generated {time.strftime("%Y-%m-%d %H:%M")}
"""
    brief_p = out / "brief.md"
    brief_p.write_text(brief)

    # ── scenario_prompt.txt — what we feed Seedance ──────────────────────
    # Lead with VISUAL DNA from the gameplay analysis. The previous version
    # opened with format meta-instructions and ended with style hints; the
    # signal got crowded out by the noise and Seedance produced generic
    # "mobile-game-ad-looking" video that didn't look like the actual game.
    # Now: visual signature first, hook second, format constraints last.
    # Also: NO literal game name in the rendered prompt (Seedance can't render
    # text reliably — we just shipped "Spellitaire" → "Spelletaire").

    scene_block = ga.get("scene") or {}
    setting = scene_block.get("setting") or ""
    perspective = scene_block.get("perspective") or ""

    # Compose a dense, specific visual signature from the gameplay analysis.
    visual_signature_lines = []
    if setting:
        visual_signature_lines.append(f"SETTING: {setting}")
    if perspective:
        visual_signature_lines.append(f"PERSPECTIVE: {perspective}")
    if art_style:
        visual_signature_lines.append(f"ART STYLE: {art_style}")
    if palette_in_game:
        visual_signature_lines.append(
            f"EXACT PALETTE (use these hex values, no others): {', '.join(palette_in_game[:6])}"
        )
    if juice:
        visual_signature_lines.append(
            "VFX TO INCLUDE: " + "; ".join(juice[:5])
        )
    if audio_cues:
        visual_signature_lines.append(
            "SOUND DESIGN: " + "; ".join(
                f"{a.get('trigger', '?')} → {a.get('feel', '?')}"
                for a in audio_cues[:3]
            )
        )
    if asset_list:
        _VISUAL_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".psb", ".psd"}
        visual_assets = [a for a in asset_list if any(a.lower().endswith(ext) for ext in _VISUAL_EXTS)]
        if visual_assets:
            visual_signature_lines.append(
                "VISIBLE CHARACTERS/PROPS (named after project assets): "
                + ", ".join(a.rsplit(".", 1)[0].replace("_", " ") for a in visual_assets[:8])
            )

    visual_signature = "\n".join(visual_signature_lines) if visual_signature_lines else (
        f"GENRE STYLE: {top_palette}, vibrant cartoon stylization."
    )

    # Mechanic in plain English, not the labeler's vocab term
    mechanic_human = {
        "match-3":         "matching colored tiles in groups of three",
        "merge":           "merging two of the same item to upgrade",
        "physics-drop":    "dropping a piece and watching physics resolve",
        "pull-pin":        "pulling pins and rerouting flow",
        "tower-defense":   "defending a base from incoming waves",
        "runner":          "running and dodging obstacles",
        "shoot-aim":       "aiming and shooting at targets",
        "stack":           "stacking pieces precisely",
        "color-sort":      "sorting colored liquids between vials",
        "rope-cut":        "cutting ropes to deliver an object",
        "draw-path":       "drawing paths to guide characters",
        "tap-rhythm":      "tapping in rhythm with the beat",
        "build-place":     "placing buildings on a grid",
        "conquer-territory": "conquering territory by clashing armies",
    }.get(top_mech, top_mech.replace("-", " "))

    prompt = f"""# VISUAL SIGNATURE (replicate exactly — this is what the game looks like)
{visual_signature}

# OPENING HOOK ({_hook_blueprint(top_hook, ga)})
{top_open.upper()} framing of {mechanic_human}. One subject fills 30-60% of frame, eye-line center.

# BEAT MAP for {inp.target.raw.get('genre', 'casual mobile') if isinstance(inp.target.raw, dict) else 'casual mobile'} game ad
0-2s: hook beat — pattern interrupt visual, no text yet
2-5s: {mechanic_human} in action, juice peaks ({juice[0] if juice else 'screen shake + particles'})
5-8s: emotional payoff — biggest reveal of the {mechanic_human} (juice + sound peak together)
8-10s: clean end card — bold logo placeholder + a single CTA word

# TONE
{", ".join(palette_in_game[:4]) + " — " if palette_in_game else ""}{top_palette}, instantly readable at phone-thumbnail size.
Audio cuts on beats. Low-pitch sting in first 200ms.

# CTA word to display ({top_cta} framing — pick ONE, ≤ 3 words)
"PLAY NOW"

# HARD CONSTRAINTS — read carefully
9:16 vertical only. No real people. No copyrighted logos.
DO NOT render any literal game title text on screen — leave a clean rectangle for the logo to be composited later.
Any displayed words must be ≤ 6 words and ≥ 64px equivalent — keep them to the CTA only.

# STAY-ON-SEED RULES (when an input/seed image is provided — i2v mode)
This is THE most important rule. The seed image IS the scene.
- ANIMATE the existing characters/props/UI in the seed; do not introduce new ones.
- DO NOT add: dragons, weapons, enemies, projectiles, explosions, words/letters,
  numbers, currency icons, characters, or any object that is NOT visible in the
  seed image. The previous run added a dragon that doesn't exist in this game,
  and it made up letters in the spelling game — both unacceptable.
- DO NOT render or stylize any TEXT that wasn't visible in the seed. If the
  game is a word/letter/spelling game, the only legible text on screen is the
  end-card CTA word ("PLAY NOW"). All other letters in the seed must remain
  pixel-stable (no morphing, no replacement, no new letters appearing).
- The MOTION should be: existing elements moving, UI counters incrementing,
  particle/juice effects ON existing geometry, light camera push.
- DURATION: stretch the available frames. Hold beats. Slow zooms. Don't
  cram new scenes — extend what's there.
"""
    prompt_p = out / "scenario_prompt.txt"
    prompt_p.write_text(prompt)

    activity.logger.info(f"brief → {brief_p}")
    return BriefResult(brief_path=str(brief_p), scenario_prompt_path=str(prompt_p))
