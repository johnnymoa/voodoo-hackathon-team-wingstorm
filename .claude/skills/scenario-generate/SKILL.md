---
name: scenario-generate
description: Turn a creative brief or pattern set into a Scenario MCP image generation. Use when the user says "generate a creative for X", "render a Scenario image", or hands you a brief.md / scenario_prompt.txt and wants the final ad asset. Skip if Scenario MCP isn't authorized yet — point them at `/mcp` first. For full headless rendering inside a Temporal run, use `creative-forge --render-http` or `full-forge --render-http` instead.
---

# scenario-generate

Drive Scenario from inside Claude Code. The Scenario MCP is configured in
`.mcp.json` (project-scoped). On first use, run `/mcp` and approve `scenario`.

## Inputs

Either:
- a `brief.md` from `creative_forge`
- a `scenario_prompt.txt` from `creative_forge`
- a `patterns.json` you'll build a prompt from
- a freeform request ("vertical 9:16 ad for Castle Clasher with a near-fail hook")

## Workflow

1. **Pick the prompt source.** If `<run_dir>/scenario_prompt.txt` exists, use it. Otherwise compose one (template below).
2. **Call the Scenario MCP** to render. Defaults: 9:16, 1024×1820 or 768×1366. Generate ≥ 3 variants in one batch.
3. **Save outputs** as `output/creatives/<run_id>/creative_v1.png`, `creative_v2.png`, …
4. **Score the variants.** Ask Claude to compare each against the brief on:
   - hook clarity (game readable in < 1 sec?)
   - thumbnail readability
   - palette match to the target game
   - CTA prominence

   Print a 1-paragraph rationale per variant; pick a winner.

## Prompt template

```
Mobile game ad creative for "<game name>".
Style: <palette mood>, vibrant, 9:16 vertical, hero center-frame, bold readable type.
Scene: <opening visual> framing the <mechanic> mechanic with a <hook> hook.
       Visible UI hint inviting a tap.
Mood: high-contrast, saturated, instantly readable on a phone at 50% size.
Text overlay: a single short question or CTA, max 6 words. CTA framing: <cta>.
Constraints: no copyrighted logos, no real people, no text smaller than 24px. 9:16.
```

## Tips

- Short, concrete prompts beat long ones — Scenario rewards specificity, not adjectives.
- Use the project's assigned LoRA if the team has one (mention it in the prompt).
- Resize for delivery with Pillow — don't re-render at smaller dimensions.
- If the MCP isn't connected, the user must `/mcp` and authorize Scenario first.

## Failure modes

- Wrong subject → tighten the "Scene" line; name the entity.
- Illegible at thumbnail → fewer overlay words, larger font, higher contrast.
- Looks generically AI → add a one-line style anchor referencing the target game's actual art.
