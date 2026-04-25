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

## 12. Troubleshooting

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
