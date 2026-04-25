---
name: full-forge
description: Run the full_forge merged workflow — game name + gameplay video → market intelligence + brief + Scenario prompt + market-informed playable HTML + market-hypothesis variants. Use this when the user wants the killer demo for the hackathon, or says "do the full pipeline", "merge tracks 2 and 3", or "do everything end-to-end". Each variant tests a different ranked market hook, not random difficulty knobs.
---

# full_forge — the merged demo

Single command, two pipelines, one cohesive output. This is the strongest demo
narrative for VoodooHack because it submits to *both* tracks with one story:

> "Tell me a game. Tell me a video. I'll pull what's winning in the market right
> now, write you a brief explaining why, generate a Scenario poster, AND build
> you a playable HTML ad whose hook, palette, and CTA are *all* informed by what
> the data says is hot. The variants aren't difficulty tweaks — they're A/B
> hypotheses testing different ranked market signals."

## Prereqs

- `temporal server start-dev` running (web UI: http://localhost:8233)
- `uv run adforge worker` running
- A gameplay video for the target game in `videos/`
- `assets/<game>/` populated (optional but recommended)

## Run

```bash
uv run adforge run full \
  --target "castle clasher" \
  --video  videos/castle_clasher.mp4 \
  --assets assets/castle_clashers \
  --network TikTok --sample 30
```

## What happens

1. **`creative_forge` child workflow:** SensorTower → patterns → brief + prompt.
2. **Hypothesis variants built** from the top-ranked hooks and palette moods —
   each variant is annotated with its `rationale` (what market signal it tests).
3. **`playable_forge` child workflow:** Gemini analyzes the gameplay video, the
   playable's CONFIG block bakes in the winning palette + CTA framing from
   `creative_forge`, then variants are emitted.

Watch in the Temporal Web UI — both child workflows stream in parallel sub-views.

## Output

```
output/full/<run_id>/
├── creative/
│   ├── target.json
│   ├── top_advertisers.json
│   ├── top_creatives.json
│   ├── patterns.json
│   ├── brief.md
│   └── scenario_prompt.txt
└── playable/
    ├── playable.html              ← market-informed base
    ├── playable__hook-near-fail-tease.html
    ├── playable__hook-satisfying-completion.html
    ├── playable__mood-neon-pop.html
    └── ...
```

## Demo script (5 minutes — same deck for both tracks)

1. **Slide 1**: target game + market context. "Castle Clasher, mid-core strategy, US, last 30 days."
2. **Slide 2**: top patterns — hooks, opening visuals, palette moods — with evidence_ids.
3. **Slide 3**: end-to-end pipeline + the final outputs. Show the Temporal UI live.
4. **Demo**: type the command, watch Temporal show both child workflows running, open the playable in a browser, then the Scenario poster, then the brief.
5. **Pitch close**: "Each variant is a market hypothesis. We don't ship a
   playable — we ship four playables that each test a different signal."

## When `full-forge` is the wrong call

- User only wants a poster → `creative-forge`.
- User only wants a playable from a video → `playable-forge`.
- User wants to debug data → `sensortower-research`.

## Stretch

- Add a `score_creatives` activity that asks Claude to rank the variants on the
  brief criteria (hook clarity, thumbnail readability, palette match) and pick a winner.
- Add a small Streamlit / FastAPI front end that calls `start_workflow` and
  displays results — lets the jury type a game name and watch the magic.
