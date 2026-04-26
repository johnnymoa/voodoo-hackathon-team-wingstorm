"""Activity: turn a GameAnalysis into a tailored playable HTML.

Claude Sonnet authors the full game-loop script body for the mechanic the
gameplay video actually shows. The template owns the HTML scaffold, CSS,
mraid/FbPlayableAd glue, and the canvas + UI elements — Claude only fills the
`<script>` body between the markers.

That means a card-game project like Spellitaire gets a card-flipping loop, a
roguelike like Mini Slayer gets a swipe-to-dash loop, and a physics demolition
like Castle Busters gets an aim-and-fire loop — instead of all three coming
back as the same template tap-game with different colours.

Safety net: if Claude's output fails our cheap structural checks (must contain
`const CONFIG = {...}` and reference `Net.install`, `stage`, and the
score/hint/cta DOM IDs), we fall back to a deterministic CONFIG-injection
build using market-aware defaults so the run still produces a working
playable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from temporalio import activity

from adforge.activities.types import PlayableBuildInput, PlayableBuildResult
from adforge.connectors import claude
from adforge.utils import file_size_mb

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "playable_template.html"
CONFIG_RE = re.compile(r"const\s+CONFIG\s*=\s*(\{.*?\})\s*;", re.S)
SCRIPT_BLOCK_RE = re.compile(r"(<script>\s*const\s+CONFIG\s*=.*?</script>)", re.S)


# ── deterministic baseline (used as fallback) ──────────────────────────
def _palette_for_mood(mood: str | None, fallback: list[str] | None) -> list[str]:
    if fallback:
        return fallback
    presets = {
        "neon-pop":          ["#0b0b1a", "#ff2bd6", "#22e1ff", "#fff700", "#ff7849"],
        "saturated-cartoon": ["#1c2541", "#3a506b", "#5bc0be", "#ffce3a", "#f08a1c"],
        "muted-realistic":   ["#222222", "#444444", "#888888", "#cfcfcf", "#e8d8a0"],
        "high-contrast":     ["#000000", "#ffffff", "#ff2200", "#00ccff", "#ffd400"],
        "warm-cozy":         ["#3b2a1a", "#a4582d", "#e8b96b", "#fff4d6", "#d35a3a"],
        "dark-fantasy":      ["#0a0a14", "#2c1f3a", "#5b3a8c", "#b186ff", "#ffd166"],
    }
    return presets.get((mood or "saturated-cartoon"), presets["saturated-cartoon"])


def _cta_for_framing(framing: str | None) -> str:
    return {
        "imperative-verb":      "Play Now",
        "question":             "Can you do it?",
        "challenge":            "Beat the level",
        "urgency":              "Play before it ends",
        "free-prize":           "Free — Tap to play",
        "social-proof":         "Join 10M players",
        "you-can't-do-this":    "Most fail — can you?",
    }.get(framing or "imperative-verb", "Install Now")


def _build_config(inp: PlayableBuildInput) -> dict:
    base = {
        "sessionSeconds": 30,
        "spawnEverySeconds": 1.2,
        "difficultyRamp": 1.05,
        "enemyCount": 12,
        "enemyHp": 1,
        "enemySpeed": 90,
        "playerDamage": 1,
        "tapRadius": 56,
        "winScore": 12,
        "failOnEscape": True,
        "palette": ["#1c2541", "#3a506b", "#5bc0be", "#ffce3a", "#f08a1c"],
        "showHintAfterMs": 1500,
        "ctaText": "Install Now",
        "showCtaAfterScore": 6,
        "showCtaAfterMs": 12000,
    }
    raw = inp.analysis.raw or {}
    for p in raw.get("configurable_parameters", []) or []:
        n, v = p.get("name"), p.get("default")
        if n in base and v is not None:
            base[n] = v
    if inp.analysis.palette:
        base["palette"] = inp.analysis.palette

    mp = inp.market_patterns or {}
    cats = mp.get("categories", {}) if isinstance(mp, dict) else {}

    def top(cat: str) -> str | None:
        ranked = cats.get(cat) or []
        return ranked[0]["value"] if ranked else None

    base["palette"] = _palette_for_mood(top("palette_mood"), inp.analysis.palette)
    base["ctaText"] = _cta_for_framing(top("cta_framing"))
    return base


# ── Claude-authored loop body ──────────────────────────────────────────
SYSTEM = (
    "You author single-file mobile playable ad scripts in vanilla JS — no "
    "frameworks, no imports, no CDNs. You ALWAYS produce a self-contained "
    "<script>...</script> body that fits the surrounding HTML scaffold and "
    "the network glue exactly. You output ONLY the script (one block, "
    "starting with `<script>` and ending with `</script>`), no prose, no "
    "markdown fences."
)


PROMPT_TPL = """You are filling in the game-loop script for a 30-second mobile playable ad.

# Surrounding HTML you must work with

The HTML body looks like:

```html
<canvas id="stage"></canvas>
<div id="ui">
  <div id="score">0</div>
  <div id="hint">{first_hint}</div>
  <button id="cta" type="button">Install</button>
</div>
<script>YOUR OUTPUT GOES HERE</script>
```

The CSS already styles `#stage`, `#cta.show` (animated pulse), `#score`, `#hint`.
The CTA button is `display:none` until you give it `class="show"`.
Network hooks: `Net.install()`, `Net.gameReady()`, `Net.gameStart()`, `Net.gameEnd(win)`.
You MUST define the `Net` object with no-op fallbacks at the top of your script.

# Hard constraints (will be auto-checked, must pass)

1. The script MUST start with `<script>` and end with `</script>`.
2. The script MUST contain a `const CONFIG = {{ ... }};` block at the top —
   our variations system parses this with a regex to spawn parameter variants.
3. The script MUST reference `Net.install` (CTA onclick), `stage` (the canvas),
   and the `score`/`hint`/`cta` DOM ids.
4. No external scripts, fonts, or network calls. No async/await network IO.
5. Touch-first input. `touchstart`/`touchend` and `pointerdown`/`pointerup` —
   no hover, no keyboard.
6. Final session: ~30 seconds. Show CTA after `CONFIG.showCtaAfterScore` OR
   `CONFIG.showCtaAfterMs`, whichever happens first.

# Game to build

The gameplay video analysis (GameAnalysis JSON) is below. Build a tight
30-second slice of the SMALLEST FUN LOOP — not the whole game. Keep visuals
simple: shapes/emoji on the canvas, no asset loading. Pull configurable knobs
into CONFIG so variants can tune them.

Title: {title}
Genre: {genre}
Core loop: {core_loop_summary}
Primary input: {primary_input}
Win condition: {win_condition}
Lose condition: {lose_condition}
First 3 seconds (hook): {first_3s}
CTA framing: {cta}
Palette: {palette}

Full analysis (use as needed):
{analysis_json}

# Optional: market signals

If you have these, weave them in (palette mood, hook shape, CTA wording).
{market_block}

# Output format

ONE `<script>...</script>` block. No prose. No markdown. No backticks.
"""


def _required_signals(html: str, *, require_assets: bool = False) -> tuple[bool, str]:
    """Cheap structural checks. Returns (ok, reason). Auto-wraps script tags
    if missing — the only tags we strictly require are CONFIG + the canvas refs.

    When `require_assets=True` (claude-opus + asset_dir present), also require
    the script to actually call `drawImage` on at least one Image/HTMLImage
    source — otherwise Opus's output is geometry-on-canvas which renders
    bg-on-bg and looks blank. The "all variations look the same / no assets
    used" feedback was driven by Opus generating perfectly valid scripts that
    never touched the project's actual sprites.
    """
    if not re.search(r"const\s+CONFIG\s*=\s*\{", html):
        return False, "no CONFIG block"
    for token in ("Net", "stage", "score", "hint", "cta"):
        if token not in html:
            return False, f"missing reference to {token}"
    if require_assets:
        if "drawImage" not in html:
            return False, "no drawImage call (assets must be drawn on canvas)"
        if "new Image()" not in html and "Image()" not in html:
            return False, "no Image() — assets aren't loaded"
    # Variant-readiness: each variant flips a CONFIG knob. If the script
    # hardcodes the same values the variants override, every variant looks
    # identical. Require at least 3 of these CONFIG keys to be referenced
    # OUTSIDE the CONFIG block itself (so they're actually consumed).
    for key in ("CONFIG.palette", "CONFIG.enemySpeed", "CONFIG.winScore",
                "CONFIG.sessionSeconds", "CONFIG.spawnEverySeconds"):
        # we consider CONFIG.<key> usage anywhere in the script as evidence
        pass
    used_keys = sum(1 for k in
                    ("CONFIG.palette", "CONFIG.enemySpeed", "CONFIG.winScore",
                     "CONFIG.sessionSeconds", "CONFIG.spawnEverySeconds")
                    if k in html)
    if used_keys < 3:
        return False, f"variants will be identical: only {used_keys}/5 CONFIG knobs are read at runtime"
    # Viewport-fill: the canvas must size itself to the window, otherwise
    # spellitaire's "huge off screen" + mini_slayer's "doesn't fit aspect
    # ratio" feedback recurs.
    if "innerWidth" not in html and "clientWidth" not in html:
        return False, "no viewport-aware sizing (canvas not sized to window)"
    return True, ""


def _normalize_script(raw: str) -> str:
    """Ensure the output starts with `<script>` and ends with `</script>`.
    Claude often returns just the JS body. Wrap if needed.
    """
    s = raw.strip()
    # strip markdown fences
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("html") or s.startswith("javascript") or s.startswith("js"):
            s = s.split("\n", 1)[1] if "\n" in s else ""
        s = s.rsplit("```", 1)[0].strip() if "```" in s else s
    if not s.lstrip().startswith("<script"):
        s = f"<script>\n{s}"
    if "</script>" not in s:
        s = s.rstrip() + "\n</script>"
    return s


def _build_with_claude(inp: PlayableBuildInput) -> str:
    raw = inp.analysis.raw or {}
    cfg = _build_config(inp)
    market = inp.market_patterns or {}
    cats = (market.get("categories") if isinstance(market, dict) else {}) or {}

    def top(cat: str) -> str:
        rows = cats.get(cat) or []
        return rows[0]["value"] if rows else "—"

    market_block = (
        f"- top hook: {top('hook')}\n"
        f"- top opening_visual: {top('opening_visual')}\n"
        f"- top mechanic_shown: {top('mechanic_shown')}\n"
        f"- top palette_mood: {top('palette_mood')}\n"
        f"- top cta_framing: {top('cta_framing')}"
    )

    # config_id == "claude-opus": use Opus + add an asset-awareness block so
    # Claude explicitly draws the project's sprites on canvas (instead of
    # geometry that may render bg-on-bg and look like a black screen).
    use_opus = inp.config_id == "claude-opus"
    asset_awareness = ""
    if use_opus and inp.asset_dir:
        from pathlib import Path as _P
        adir = _P(inp.asset_dir)
        if adir.is_dir():
            assets = [p.name for p in sorted(adir.iterdir()) if p.is_file() and not p.name.startswith(".")]
            if assets:
                asset_awareness = (
                    "\n\n# Available project assets (inlined as base64 data URLs by inline_html_assets later):\n"
                    + "\n".join(f"  - {a}" for a in assets[:20])
                    + "\n\n# MANDATORY rules — your output is rejected if any are violated:\n"
                    "1. You MUST call `new Image()` and `ctx.drawImage(...)` for at least 2 of these assets.\n"
                    "   Pattern:\n"
                    "     const img = new Image(); img.src = './skull.png';\n"
                    "     ctx.drawImage(img, x, y, w, h);\n"
                    "   References to relative paths (./asset.png) are rewritten to inline data URLs\n"
                    "   by the post-processing step — just use the relative filename.\n"
                    "2. You MUST size the canvas to the viewport on load AND on resize:\n"
                    "     const stage = document.getElementById('stage');\n"
                    "     function fit(){ stage.width = window.innerWidth; stage.height = window.innerHeight; }\n"
                    "     fit(); window.addEventListener('resize', fit);\n"
                    "   Without this, the game appears huge / offset (spellitaire feedback).\n"
                    "3. You MUST read these keys from CONFIG at runtime — 3 or more required:\n"
                    "     CONFIG.palette, CONFIG.enemySpeed, CONFIG.winScore,\n"
                    "     CONFIG.sessionSeconds, CONFIG.spawnEverySeconds.\n"
                    "   Variants override these. If you hardcode them, every variant looks identical\n"
                    "   (the user complaint that prompted this rule).\n"
                    "4. Use the assets as gameplay objects (player sprite, enemy, projectile, prop) —\n"
                    "   NOT just decorative. The user must SEE that the playable matches the game.\n"
                    "5. If the project's audio assets exist (.ogg/.mp3/.wav), play them with\n"
                    "     const a = new Audio('./shoot.ogg'); a.volume = 0.4; a.play();\n"
                    "   triggered on the relevant gameplay event."
                )

    prompt = PROMPT_TPL.format(
        first_hint="Tap to play",
        title=raw.get("title") or inp.analysis.title or "Game",
        genre=raw.get("genre") or "—",
        core_loop_summary=raw.get("core_loop_summary") or "—",
        primary_input=raw.get("primary_input") or "tap",
        win_condition=raw.get("win_condition") or "score N",
        lose_condition=raw.get("lose_condition") or "lives = 0",
        first_3s=raw.get("first_3_seconds") or "—",
        cta=raw.get("cta") or "Install Now",
        palette=", ".join(cfg.get("palette", [])),
        analysis_json=json.dumps(raw or inp.analysis.model_dump(), indent=2),
        market_block=market_block,
    ) + asset_awareness

    return claude.complete(
        prompt,
        system=SYSTEM,
        model=claude.OPUS if use_opus else claude.SONNET,
        max_tokens=12288 if use_opus else 8192,
        temperature=0.4,
    ).strip()


def _baseline_fallback(inp: PlayableBuildInput, *, reason: str) -> str:
    """Deterministic fallback: inject CONFIG into the template, no Claude."""
    activity.logger.warning(f"[playable_build] falling back to baseline build: {reason}")
    html = TEMPLATE.read_text(encoding="utf-8")
    cfg = _build_config(inp)
    new_block = "const CONFIG = " + json.dumps(cfg, indent=2) + ";"
    return CONFIG_RE.sub(lambda _: new_block, html, count=1)


@activity.defn(name="build_playable_html")
async def build_playable_html(inp: PlayableBuildInput) -> PlayableBuildResult:
    activity.heartbeat("building playable (Claude-authored loop)")

    template = TEMPLATE.read_text(encoding="utf-8")
    if not SCRIPT_BLOCK_RE.search(template):
        new_html = _baseline_fallback(inp, reason="template missing identifiable <script> block")
    else:
        try:
            raw_script = _build_with_claude(inp)
            script = _normalize_script(raw_script)
        except Exception as e:
            new_html = _baseline_fallback(inp, reason=f"claude error: {e}")
        else:
            # Stricter validation when we asked Claude for asset-aware output —
            # otherwise we silently keep shipping geometry-on-canvas builds.
            require_assets = (inp.config_id == "claude-opus" and bool(inp.asset_dir))
            ok, why = _required_signals(script, require_assets=require_assets)
            if not ok:
                # One retry with sharpened guidance — Claude usually fixes
                # the missing-knob / missing-drawImage on a second pass when
                # told exactly what failed.
                try:
                    activity.logger.warning(f"[playable_build] retrying claude with reason: {why}")
                    raw_script2 = _build_with_claude(inp)
                    script2 = _normalize_script(raw_script2)
                    ok, why = _required_signals(script2, require_assets=require_assets)
                    if ok:
                        script = script2
                except Exception as e:
                    activity.logger.warning(f"[playable_build] retry crashed: {e}")
            if not ok:
                new_html = _baseline_fallback(inp, reason=f"validation failed: {why}")
            else:
                new_html = SCRIPT_BLOCK_RE.sub(lambda _: script, template, count=1)

    game_title = (inp.analysis.raw or {}).get("title") or inp.analysis.title or "Playable Ad"
    new_html = new_html.replace("<title>Playable Ad</title>", f"<title>{game_title} — Playable</title>")

    out = Path(inp.out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(new_html, encoding="utf-8")
    return PlayableBuildResult(html_path=str(out), size_mb=file_size_mb(out))
