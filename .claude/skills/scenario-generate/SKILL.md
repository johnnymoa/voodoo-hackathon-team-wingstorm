---
name: scenario-generate
description: Drive Scenario MCP from inside Claude Code to generate ad creatives — both still images AND videos (image-to-video animation). Use when the user says "generate a creative for X", "render a Scenario image", "animate this still", "make a video ad from this brief", or hands you a brief.md / scenario_prompt.txt and wants the final ad asset (image or motion). Skip if Scenario MCP isn't authorized yet — point them at `/mcp` first. For full headless rendering inside a Temporal run, use `creative-forge --render-http` instead. Pairs with `video-ad-design` (the rubric for what makes a great video ad).
---

# scenario-generate

Drive Scenario from inside Claude Code. The Scenario MCP is configured in
`.mcp.json` (project-scoped). On first use, run `/mcp` and approve `scenario`.

Scenario does both **still images** and **video** (image-to-video and
text-to-video). The skill below covers both — pick the path based on what
the placement needs. When in doubt, see `video-ad-design` for the design
rubric.

## Inputs

Either:
- a `brief.md` from `creative_forge`
- a `scenario_prompt.txt` from `creative_forge`
- a `patterns.json` you'll build a prompt from
- a freeform request ("vertical 9:16 ad for Castle Clasher with a near-fail hook")

## Path A — still image (start here)

Most iteration cycles should start with stills. They're cheap, fast, and
let you validate the hook before spending video render time.

1. **Pick the prompt source.** If `<run_dir>/scenario_prompt.txt` exists, use it. Otherwise compose one (template below).
2. **Call the Scenario MCP** to render. Defaults: 9:16, 1024×1820 or 768×1366. Generate ≥ 3 variants in one batch.
3. **Save outputs** as `runs/<run_id>/creative_v1.png`, `creative_v2.png`, …
4. **Score the variants** against the brief on:
   - hook clarity (game readable in < 1 sec?)
   - thumbnail readability (legible at 50% size?)
   - palette match to the target game
   - CTA prominence
   - market-pattern fit (does it actually express the hypothesis?)

   Print a 1-paragraph rationale per variant; pick a winner.

## Path B — image-to-video (animate the winning still)

Once a still has validated, animate it. This is cheaper and more on-style
than text-to-video because the visuals are already locked.

1. **Pick the winning still** from Path A.
2. **Write a motion prompt** describing the camera, subject motion, and
   pacing. Keep it tight — 1-2 sentences. Examples:
   - *"Slow push-in on the king. He turns his head toward the falling tile,
     eyes widening. 3-second clip, ease-out."*
   - *"Tiles cascade from top to bottom in a satisfying wave. Match-3
     clear at frame 60. 4-second clip, smooth easing."*
3. **Call Scenario MCP image-to-video** with the still + motion prompt.
4. **Set duration** based on placement: 3-6s for hook tests, 8-15s for
   full-flow ads, 15-30s for broader feed placements.
5. **Save outputs** as `runs/<run_id>/creative_v1.mp4`, …
6. **Add captions / text overlays** in post (Pillow + ffmpeg, or do it as
   part of the image render and let the still drive the motion).

## Path C — text-to-video (skip the still)

Only when you have a strong concept and the visual style is well-defined
in the prompt. More expensive, harder to control. Reserve for when:

- The motion is the hook (and a still wouldn't capture it).
- You've already validated the visual style on past projects.
- Speed matters more than iteration cost.

Most of the time, Path B (image-to-video from a winning still) produces
better results faster.

## Prompt template (still)

```
Mobile game ad creative for "<game name>".
Style: <palette mood>, vibrant, 9:16 vertical, hero center-frame, bold readable type.
Scene: <opening visual> framing the <mechanic> mechanic with a <hook> hook.
       Visible UI hint inviting a tap.
Mood: high-contrast, saturated, instantly readable on a phone at 50% size.
Text overlay: a single short question or CTA, max 6 words. CTA framing: <cta>.
Constraints: no copyrighted logos, no real people, no text smaller than 24px. 9:16.
```

## Prompt template (image-to-video motion)

```
From the still: <one sentence describing the input image>.
Motion: <camera move + subject animation + timing>.
Duration: <N> seconds.
Pacing: <ease-out / linear / accelerating>.
Constraints: <what should NOT change — e.g. "background stays static",
             "no extra characters appear", "preserve text overlay">.
```

## Tips

- Short, concrete prompts beat long ones — Scenario rewards specificity, not adjectives.
- Use the project's assigned LoRA if the team has one (mention it in the prompt).
- For stills: resize for delivery with Pillow — don't re-render at smaller dimensions.
- For videos: keep clips short (≤ 6s) for hook validation before spending on longer renders.
- If the MCP isn't connected, the user must `/mcp` and authorize Scenario first.
- The `creative-forge` workflow runs this automatically when invoked with
  `--render-http`. Use this skill for ad-hoc renders or when iterating on
  prompts outside a Temporal workflow.

## Failure modes

- **Wrong subject** (still) → tighten the "Scene" line; name the entity.
- **Illegible at thumbnail** → fewer overlay words, larger font, higher contrast.
- **Looks generically AI** → add a one-line style anchor referencing the target game's actual art.
- **Motion drifts off-style** (video) → animate from a winning still rather than text-to-video.
- **Text overlay morphs in motion** → render text as a separate layer in
  post, not baked into the input still.
- **Clip too long** → users skip after 2-3s; cut to 3-6s for hook tests.
