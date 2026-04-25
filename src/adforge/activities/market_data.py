"""Activities: target-game resolution + market data fetch."""

from __future__ import annotations

from temporalio import activity

from adforge.activities.types import (
    MarketData,
    MarketDataInput,
    TargetGame,
    TargetGameInput,
)
from adforge.connectors import sensortower as st


@activity.defn(name="resolve_target_game")
async def resolve_target_game(inp: TargetGameInput) -> TargetGame:
    """Search SensorTower for the unified app id.

    Fictional / unreleased games won't match — return a synthetic target so the
    rest of the pipeline (market data by category, brief, Scenario prompt) can
    still run. Downstream activities don't depend on app_id.
    """
    res = st.search_entities(inp.term, os_="unified", entity_type="app", limit=5)
    apps = res if isinstance(res, list) else (res.get("apps") or res.get("results") or [])
    if not apps:
        activity.logger.info("no SensorTower match for %r — using synthetic target", inp.term)
        return TargetGame(app_id="", name=inp.term, publisher_name=None, raw={"synthetic": True, "term": inp.term})
    a = apps[0]
    return TargetGame(
        app_id=str(a.get("app_id") or a.get("id") or ""),
        name=a.get("name", inp.term),
        publisher_name=a.get("publisher_name"),
        raw=a,
    )


@activity.defn(name="fetch_market_data")
async def fetch_market_data(inp: MarketDataInput) -> MarketData:
    activity.heartbeat("top_advertisers")
    advertisers = st.top_advertisers(
        category=inp.category,
        country=inp.country,
        network="All Networks",
        period=inp.period,
    )
    activity.heartbeat("top_creatives")
    creatives = st.top_creatives(
        category=inp.category,
        country=inp.country,
        network=inp.network,
        period=inp.period,
        limit=inp.limit,
    )
    return MarketData(top_advertisers=advertisers, top_creatives=creatives)
