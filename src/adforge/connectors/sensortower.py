"""Sensor Tower connector — wraps the validated endpoints documented in
.claude/skills/sensortower-research/REFERENCE.md.

All responses are cached to .cache/sensortower/ keyed by (url, params). Re-running
is free; delete the cache dir to bust.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from adforge.config import CACHE_DIR, settings

BASE = "https://api.sensortower.com"
RATE_LIMIT_QPS = 6
_CACHE_ROOT = CACHE_DIR / "sensortower"


class SensorTowerError(RuntimeError):
    pass


def _cache_path(url: str, params: dict) -> Path:
    blob = json.dumps(
        {"u": url, "p": {k: v for k, v in params.items() if k != "auth_token"}},
        sort_keys=True,
    )
    h = hashlib.sha256(blob.encode()).hexdigest()[:16]
    safe = url.replace(BASE + "/", "").replace("/", "_")
    return _CACHE_ROOT / f"{safe}__{h}.json"


_last_call_at = [0.0]


def _throttle() -> None:
    gap = 1.0 / RATE_LIMIT_QPS
    elapsed = time.time() - _last_call_at[0]
    if elapsed < gap:
        time.sleep(gap - elapsed)
    _last_call_at[0] = time.time()


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.HTTPError, requests.ConnectionError)),
    reraise=True,
)
def _get(path: str, params: dict[str, Any], *, use_cache: bool = True) -> dict:
    url = f"{BASE}{path}"
    cache_file = _cache_path(url, params)
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())

    _throttle()
    full = {"auth_token": settings().sensortower_api_key, **params}
    resp = requests.get(url, params=full, timeout=30)
    if resp.status_code == 429:
        time.sleep(5)
    if resp.status_code >= 400:
        raise SensorTowerError(f"{resp.status_code} {resp.url}\n{resp.text[:400]}")

    data = resp.json()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, indent=2))
    return data


def search_entities(
    term: str, *, os_: str = "unified", entity_type: str = "app", limit: int = 5
) -> dict:
    return _get(
        f"/v1/{os_}/search_entities",
        {"term": term, "entity_type": entity_type, "limit": limit},
    )


def app_metadata(app_ids: Iterable[str], *, os_: str = "ios") -> dict:
    if os_ == "unified":
        return _get(
            "/v1/unified/apps",
            {"app_ids": ",".join(app_ids), "app_id_type": "unified"},
        )
    return _get(f"/v1/{os_}/apps", {"app_ids": ",".join(app_ids)})


def top_advertisers(
    *,
    category: str | int = 7012,
    country: str = "US",
    network: str = "All Networks",
    period: str = "month",
    date: str | None = None,
    limit: int = 20,
) -> dict:
    if date is None:
        date = time.strftime("%Y-%m-01", time.gmtime(time.time() - 30 * 86400))
    return _get(
        "/v1/unified/ad_intel/top_apps",
        {
            "role": "advertisers",
            "category": category,
            "country": country,
            "network": network,
            "period": period,
            "date": date,
            "limit": limit,
        },
    )


def top_creatives(
    *,
    category: str | int = 7012,
    country: str = "US",
    network: str = "TikTok",
    ad_types: str = "video,video-interstitial,playable",
    period: str = "month",
    date: str | None = None,
    aspect_ratios: str | None = "9:16",
    new_creative: bool | None = None,
    limit: int = 50,
) -> dict:
    if date is None:
        date = time.strftime("%Y-%m-01", time.gmtime(time.time() - 30 * 86400))
    params: dict[str, Any] = {
        "category": category,
        "country": country,
        "network": network,
        "ad_types": ad_types,
        "period": period,
        "date": date,
        "limit": limit,
    }
    if aspect_ratios:
        params["aspect_ratios"] = aspect_ratios
    if new_creative is not None:
        params["new_creative"] = "true" if new_creative else "false"
    return _get("/v1/unified/ad_intel/creatives/top", params)


def app_creatives(
    app_ids: Iterable[str],
    *,
    countries: str = "US",
    networks: str = "TikTok,Admob,Unity,Facebook,Instagram",
    ad_types: str = "video,video-interstitial,playable,image,banner,full_screen",
    start_date: str,
    end_date: str | None = None,
    display_breakdown: bool = True,
    limit: int = 100,
) -> dict:
    params: dict[str, Any] = {
        "app_ids": ",".join(app_ids),
        "countries": countries,
        "networks": networks,
        "ad_types": ad_types,
        "start_date": start_date,
        "limit": limit,
        "display_breakdown": "true" if display_breakdown else "false",
    }
    if end_date:
        params["end_date"] = end_date
    return _get("/v1/unified/ad_intel/creatives", params)


def store_ranking(
    *,
    os_: str = "ios",
    category: str | int = 7012,
    chart_type: str = "topgrossingapplications",
    country: str = "US",
    date: str | None = None,
) -> dict:
    if date is None:
        date = time.strftime("%Y-%m-%d")
    return _get(
        f"/v1/{os_}/ranking",
        {"category": category, "chart_type": chart_type, "country": country, "date": date},
    )
