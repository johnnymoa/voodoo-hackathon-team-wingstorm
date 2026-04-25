---
name: sensortower-research
description: Pull and cache mobile-game ad intelligence from Sensor Tower — top advertisers, top creatives, app metadata, store rankings — without spinning up a Temporal workflow. Use when the user says "what are the top creatives on TikTok for puzzle games", "look up this app", "find the top advertisers in X", or wants raw data fast. Skip if they want the full creative pipeline — use `creative-forge` instead.
---

# sensortower-research

Standalone helper — no Temporal needed. Calls go through the SensorTower connector
which caches every response to `.cache/sensortower/`. Re-running is free.

## Common moves

### Resolve a game name → unified ID
```bash
uv run adforge tools st-search "castle clasher"
```

### Top creatives in a genre on a network
```bash
uv run adforge tools st-top-creatives \
  --category 7012 --country US --network TikTok --period month --limit 50 \
  --save output/top.json
```

iOS category IDs in `docs/sensortower_api.md` §9.1. Common: Puzzle=7012, Strategy=7017,
Casual=7003, RPG=7014, Simulation=7015.

**Note:** `network=All Networks` is REJECTED on `creatives/top` — pick one network
per call. Iterate {TikTok, Admob, Facebook, Unity, Mintegral} for breadth.

### Direct Python (richer queries)
```python
from adforge.connectors import sensortower as st

st.search_entities("royal match", limit=5)
st.top_advertisers(category=7012, country="US", network="All Networks", period="month")
st.top_creatives(category=7012, network="TikTok", aspect_ratios="9:16", new_creative=True)
st.app_creatives(["5f16a8019f7b275235017614"], start_date="2026-02-01", networks="TikTok,Admob")
st.store_ranking(os_="ios", category=7012, chart_type="topgrossingapplications")
```

## Tips

- **422 errors** — `ad_types` or `network` value not in the allowed list. Check `docs/sensortower_api.md` §9.3 / §9.4.
- **Rate limit** is 6 QPS, throttled automatically.
- **Cache busting** — `rm -rf .cache/sensortower/`.
- **Date defaults** to first of previous month for monthly queries — override with `date="2026-MM-DD"` for weekly/quarterly.

## Hand-off

Typical next step is to feed `top_creatives.json` into `creative-forge` for
pattern extraction:

```bash
uv run adforge run creative --target "castle clasher" --network TikTok
```
