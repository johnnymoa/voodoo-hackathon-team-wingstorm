# output/

All pipeline artifacts land here, partitioned by pipeline + run ID.

```
output/
├── playables/<run_id>/                  ← playable_forge
│   ├── playable.html                    base playable, CONFIG injected from analysis
│   ├── playable__easy.html              variant
│   ├── playable__hard.html
│   └── …
├── creatives/<run_id>/                  ← creative_forge
│   ├── target.json                      resolved unified app metadata
│   ├── top_advertisers.json             SensorTower
│   ├── top_creatives.json
│   ├── patterns.json                    ranked hooks/CTAs/palettes + evidence_ids
│   ├── brief.md                         human-readable brief
│   └── scenario_prompt.txt              copy-paste prompt for Scenario MCP
└── full/<run_id>/                       ← full_forge (merged pipeline)
    ├── creative/                        ⤴ same as creatives/<run_id>/
    └── playable/                        ⤴ market-informed playable + hypothesis variants
```

Run IDs are timestamped, e.g. `playable-20260426-141500`. Cleanup is manual —
delete old runs you don't need.
