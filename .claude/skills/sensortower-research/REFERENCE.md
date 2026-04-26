# Sensor Tower API Context: Ad Intelligence Creatives

This file documents the Sensor Tower API pieces needed to gather mobile game
advertising data: app lookup, app metadata, top advertisers, top creatives,
app-specific creatives, media URLs, and store rankings.

It is intentionally limited to Sensor Tower API behavior.

## 1. Basics

| Thing | Value |
|---|---|
| Base URL | `https://api.sensortower.com` |
| Auth | Add `auth_token=<your_token>` as a query parameter on every request. |
| Rate limit | 6 requests per second |
| Response format | JSON |
| Usage headers | `x-api-usage-limit`, `x-api-usage-count` |
| API docs | `https://app.sensortower.com/api` requires login |

Common `{os}` path values:

```text
ios
android
unified
```

Search also supports:

```text
both_stores
```

Use `unified` for ad-intelligence creative endpoints when you want one app ID
that groups iOS and Android variants of the same game.

Common errors:

| Status | Meaning |
|---|---|
| `401` | Invalid or missing `auth_token` |
| `403` | Token is valid but the organization lacks product access |
| `422` | Missing or invalid query parameter |
| `429` | Rate limit exceeded |

## 2. Validated Endpoint Notes

These were validated from this workspace with the provided API token:

- `GET /v1/unified/search_entities`
- `GET /v1/both_stores/search_entities`
- `GET /v1/ios/apps`
- `GET /v1/android/apps`
- `GET /v1/unified/apps?app_id_type=unified`
- `GET /v1/unified/ad_intel/top_apps`
- `GET /v1/unified/ad_intel/creatives/top`
- `GET /v1/unified/ad_intel/creatives`
- `GET /v1/ios/ranking`
- `GET /v1/android/ranking`

Important observed differences:

- `top_apps` accepts `network=All Networks`.
- `creatives/top` rejected `network=All Networks`; use one network per request.
- `creatives/top` uses singular `network`.
- `creatives` uses plural `networks`.
- `creatives/top` uses `date` and `period`.
- `creatives` uses `start_date` and optional `end_date`.
- `/v1/unified/apps` requires `app_id_type`.
- The plain ad type `other` was rejected; use `image-other` or `video-other`.

## 3. Search Entities

```text
GET /v1/{os}/search_entities
```

Resolve a game or publisher search term to Sensor Tower IDs.

| Param | Required | Notes |
|---|---|---|
| `os` | yes | `ios`, `android`, `both_stores`, `unified` |
| `entity_type` | yes | `app` or `publisher` |
| `term` | yes | Search string |
| `limit` | no | Result limit |
| `auth_token` | yes | API token |

Example:

```text
GET https://api.sensortower.com/v1/unified/search_entities
  ?entity_type=app&term=royal%20match&limit=5&auth_token=XXX
```

With `os=unified`, top-level `app_id` is the unified app ID. Unified app results
can include nested `ios_apps` and `android_apps`.

## 4. App Metadata

Endpoints:

```text
GET /v1/ios/apps
GET /v1/android/apps
GET /v1/unified/apps
```

iOS / Android params:

| Param | Required | Notes |
|---|---|---|
| `app_ids` | yes | Comma-separated iOS app IDs or Android package IDs |
| `country` | no | Defaults to `US` |
| `auth_token` | yes |  |

Unified params:

| Param | Required | Notes |
|---|---|---|
| `app_ids` | yes | Comma-separated IDs |
| `app_id_type` | yes | `unified`, `android`, `itunes`, or `cohorts` |
| `auth_token` | yes |  |

## 5. Top Advertisers or Publishers

```text
GET /v1/{os}/ad_intel/top_apps
```

Top advertising apps or publishers ranked by Share of Voice.

| Param | Required | Notes |
|---|---|---|
| `role` | yes | `advertisers` or `publishers` |
| `date` | yes | Period start, `YYYY-MM-DD` |
| `period` | yes | `week`, `month`, `quarter` |
| `category` | yes | iOS category ID, e.g. Puzzle = `7012` |
| `country` | yes | ISO-2 |
| `network` | yes | Single network or `All Networks` |
| `limit` | no | Max 250 |
| `auth_token` | yes |  |

## 6. Top Market-Wide Creatives

```text
GET /v1/{os}/ad_intel/creatives/top
```

| Param | Required | Notes |
|---|---|---|
| `date` | yes | Period start |
| `period` | yes | `week` / `month` / `quarter` |
| `category` | yes | category ID |
| `country` | yes | ISO-2 |
| `network` | yes | **Single network only — `All Networks` is rejected** |
| `ad_types` | yes | comma-separated |
| `limit` | no | max 250 |
| `aspect_ratios`, `video_durations`, `placements`, `banner_dimensions`, `new_creative` | no | optional filters |

Response: `count`, `available_networks`, `ad_units[]`. Each ad unit has
`creatives[]` with `creative_url`, `preview_url`, `thumb_url`, `video_duration`,
`width`, `height`, `message`, `button_text`. Order = ranking.

## 7. Creatives for Specific Apps

```text
GET /v1/{os}/ad_intel/creatives
```

| Param | Required | Notes |
|---|---|---|
| `app_ids` | yes | comma-separated; for `unified` use unified IDs |
| `start_date` | yes |  |
| `end_date` | no | defaults to today |
| `countries` | yes | comma-separated ISO-2 |
| `networks` | yes | **plural**, comma-separated |
| `ad_types` | yes | comma-separated |
| `limit` | no | max 100 |
| `display_breakdown` | no | `true` includes `breakdown` and `top_publishers` |

Sort by `share` desc among the selected apps.

## 8. Store Rankings

```text
GET /v1/ios/ranking
GET /v1/android/ranking
```

| Param | Required | Notes |
|---|---|---|
| `category` | yes | iOS numeric or Android string (e.g. `game_puzzle`) |
| `chart_type` | yes |  |
| `country` | yes |  |
| `date` | yes | YYYY-MM-DD |
| `auth_token` | yes |  |

iOS chart types: `topfreeapplications`, `toppaidapplications`, `topgrossingapplications`.
Android example chart: `topselling_free`.

## 9. Reference Values

### 9.1 iOS Game Category IDs

| ID | Category |
|---|---|
| `6014` | Games |
| `7001` | Action |
| `7002` | Adventure |
| `7003` | Casual |
| `7004` | Board |
| `7005` | Card |
| `7006` | Casino |
| `7009` | Family |
| `7011` | Music |
| `7012` | Puzzle |
| `7013` | Racing |
| `7014` | Role Playing |
| `7015` | Simulation |
| `7016` | Sports |
| `7017` | Strategy |
| `7018` | Trivia |
| `7019` | Word |

### 9.2 Networks

```
Adcolony, Admob, Applovin, BidMachine, Chartboost, Digital Turbine, Facebook,
InMobi, Instagram, Line, Meta Audience Network, Mintegral, Moloco, Mopub,
Pangle, Pinterest, Smaato, Snapchat, Supersonic, Tapjoy, TikTok, Twitter, Unity,
Verve, Vungle, Youtube
```

Endpoint-specific behavior:

```
top_apps      network=All Networks accepted
creatives/top network=All Networks rejected — pick one
creatives     uses networks=<comma-separated>
```

### 9.3 Ad Types

```
image, image-banner, image-interstitial, image-other,
banner, full_screen,
video, video-rewarded, video-interstitial, video-other,
playable, interactive-playable, interactive-playable-rewarded, interactive-playable-other
```

Plain `other` is rejected.

### 9.4 Optional Creative Filters

- `placements`
- `video_durations` — `:3`, `10:30`, `60:` syntax
- `aspect_ratios` — `9:16`, `4:5`, `1:1`, `16:9`
- `banner_dimensions` — `320x50`, `350x110`, `728x90`, `970x250`
- `new_creative` — `true` for first-seen-in-range

## 10. Media Asset URLs

`creative_url`, `preview_url`, `thumb_url` typically point to
`https://x-ad-assets.s3.amazonaws.com/...`. No `auth_token` needed. Inspect with
`curl -I` first if they could be large.

## 11. Common Query Patterns

### Top puzzle advertisers on TikTok

```
GET /v1/unified/ad_intel/top_apps
  ?role=advertisers&date=2026-03-01&period=month
  &category=7012&country=US&network=TikTok&limit=20&auth_token=XXX
```

### Top puzzle creatives on TikTok

```
GET /v1/unified/ad_intel/creatives/top
  ?date=2026-03-01&period=month&category=7012&country=US
  &network=TikTok&ad_types=video,video-interstitial,playable&limit=50&auth_token=XXX
```

### Creatives for known unified app IDs

```
GET /v1/unified/ad_intel/creatives
  ?app_ids=5f16a8019f7b275235017614,55c5028802ac64f9c0001faf
  &start_date=2026-01-24&end_date=2026-04-23&countries=US
  &networks=Admob,TikTok,Unity
  &ad_types=video,video-interstitial,playable,image,banner,full_screen
  &display_breakdown=true&limit=100&auth_token=XXX
```

## 12. Network Analysis (SOV Time Series)

`GET /v1/{os}/ad_intel/network_analysis`

Share of Voice impressions time series for specific apps. Shows how an app's
ad visibility changes over time across networks and countries.

| Param | Required | Type | Notes |
|---|---|---|---|
| `os` | yes | path | `ios`, `android`, `unified` |
| `app_ids` | yes | array[string] | Comma-separated unified/os-specific IDs |
| `start_date` | yes | string | `YYYY-MM-DD`, min 2018-01-01 |
| `end_date` | yes | string | `YYYY-MM-DD` |
| `period` | yes | string | `day`, `week`, `month` |
| `networks` | no | array[string] | Filter to specific networks |
| `countries` | no | array[string] | Filter to specific countries |

Response: array of `{app_id, country, network, date, sov}` objects.

```json
[
  {"app_id": "55d3a1a8...", "country": "US", "network": "Applovin", "date": "2023-01-01", "sov": 0.04},
  {"app_id": "55d3a1a8...", "country": "US", "network": "Youtube",  "date": "2023-01-01", "sov": 0.01}
]
```

### Example: Track a competitor's ad spend ramp

```
GET /v1/unified/ad_intel/network_analysis
  ?app_ids=5f16a8019f7b275235017614
  &start_date=2026-01-01&end_date=2026-04-01
  &period=week&countries=US
  &auth_token=XXX
```

## 13. Network Analysis Rank

`GET /v1/{os}/ad_intel/network_analysis/rank`

Daily/weekly advertising rank of apps by network and country.

| Param | Required | Type | Notes |
|---|---|---|---|
| `os` | yes | path | `ios`, `android`, `unified` |
| `app_ids` | yes | array[string] | Comma-separated |
| `start_date` | yes | string | `YYYY-MM-DD`, min 2018-01-01 |
| `end_date` | yes | string | `YYYY-MM-DD` |
| `period` | yes | string | `day`, `week` (no `month`) |
| `networks` | no | array[string] | |
| `countries` | no | array[string] | |

Response: array of `{app_id, country, network, date, rank}`.

```json
[
  {"app_id": "55d3a1a8...", "country": "US", "network": "Facebook", "date": "2023-05-08", "rank": 3},
  {"app_id": "55d3a1a8...", "country": "US", "network": "Admob",    "date": "2023-05-08", "rank": 127}
]
```

## 14. Download Channels

`GET /v1/{os}/downloads_by_sources`

Breaks down an app's downloads by acquisition source: organic browse,
organic search, paid ads, paid search, and browser.

**Important**: Always requires **unified** `app_ids` regardless of `os` param.
The `os` param only filters which platform's data is included.

| Param | Required | Type | Notes |
|---|---|---|---|
| `os` | yes | path | `ios`, `android`, `unified` |
| `app_ids` | yes | array[string] | **Unified IDs only** |
| `countries` | yes | array[string] | Use `WW` for worldwide |
| `start_date` | yes | string | `YYYY-MM-DD` |
| `end_date` | yes | string | `YYYY-MM-DD` |
| `date_granularity` | no | string | `daily` or `monthly` (default) |

Response fields per breakdown entry:

| Field | Description |
|---|---|
| `organic_browse_abs` / `_frac` | Featured / category browsing installs |
| `organic_search_abs` / `_frac` | Store search installs |
| `paid_abs` / `_frac` | Paid ad-driven installs |
| `paid_search_abs` / `_frac` | Paid search (Apple Search Ads, etc.) |
| `browser_abs` / `_frac` | Browser-referral installs |
| `organic_abs` / `_frac` | Legacy: sum of browse + search |

### Example: Paid vs organic split for a competitor

```
GET /v1/unified/downloads_by_sources
  ?app_ids=55c5027502ac64f9c0001fa6
  &countries=US&start_date=2026-01-01&end_date=2026-03-31
  &date_granularity=monthly&auth_token=XXX
```

## 15. Install Base & Penetration (Facets)

`GET /v1/facets/metrics` with query type `install_base`

Estimates current install base and market penetration. Uses the facets
endpoint pattern (different from ad_intel endpoints).

Required params: `breakdown`, `date_granularity`, `start_date`, `end_date`,
exactly one `metric`, and exactly one entity filter (`app_ids` or
`category` + `country`).

## 16. SDK Analysis (Facets)

`GET /v1/facets/metrics` with query type `sdk_analysis`

Shows which SDKs an app uses (analytics, monetization, attribution, etc.).
Useful for understanding a competitor's tech stack.

`GET /v1/facets/metrics` with query type `sdk_list_of_apps` returns apps
using a specific SDK.

`GET /v1/sdk/summary_metrics` provides SDK-level aggregate metrics.

## 17. Troubleshooting

If `creatives/top` returns 422:
- `network` must be a single valid network (not `All Networks`).
- `ad_types` must contain accepted values.
- `date`, `period`, `category`, `country` must all be present.

If `creatives` returns 422:
- Check `app_ids` are valid for the selected `{os}` (unified IDs for unified).
- `start_date`, `countries`, `networks`, `ad_types` are all required.

If `creatives` returns zero `ad_units`:
- Expand the date range, add more networks/ad-types/countries.

If `/v1/unified/apps` returns 422:
- Add `app_id_type=unified` (or `android` / `itunes` / `cohorts`).
