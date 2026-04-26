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

GENRE_TO_CATEGORY: dict[str, str] = {
    "word puzzle": "7019",
    "word": "7019",
    "solitaire": "7005",
    "match-3": "7012",
    "merge": "7012",
    "bullet heaven": "7001",
    "tower defense": "7017",
    "hyper-casual": "7003",
    "roguelike": "7014",
    "role playing": "7014",
    "rpg": "7014",
    "action": "7001",
    "adventure": "7002",
    "arcade": "7003",
    "board": "7004",
    "card": "7005",
    "casino": "7006",
    "casual": "7003",
    "dice": "7004",
    "educational": "7008",
    "family": "7009",
    "music": "7011",
    "puzzle": "7012",
    "racing": "7013",
    "simulation": "7015",
    "sports": "7016",
    "strategy": "7017",
    "trivia": "7018",
    "idle": "7015",
    "tycoon": "7015",
    "shooter": "7001",
    "survival": "7001",
    "physics": "7003",
    "destruction": "7003",
    "artillery": "7003",
}


def _genre_to_category(genre: str | None) -> str | None:
    if not genre:
        return None
    g = genre.lower().strip()
    if g in GENRE_TO_CATEGORY:
        return GENRE_TO_CATEGORY[g]
    for key, cat in GENRE_TO_CATEGORY.items():
        if key in g:
            return cat
    return None


def _extract_category_from_app(app: dict) -> str | None:
    """Pick the matched app's most-specific game subcategory from SensorTower.

    SensorTower returns `categories` like `[6014, 7002, 7001]` where 6014 is the
    "Games" top-level. The first non-6014 entry is the primary subcategory
    (Action / Puzzle / Strategy / etc.). We use that to bias top_creatives
    toward the actual genre — instead of trusting whatever category_id was
    hardcoded in project.json.
    """
    for os_key in ("ios_apps", "android_apps"):
        for entry in app.get(os_key, []) or []:
            cats = entry.get("categories") or []
            for c in cats:
                cs = str(c)
                if cs and cs != "6014" and cs != "game":
                    return cs
    return None


@activity.defn(name="resolve_target_game")
async def resolve_target_game(inp: TargetGameInput) -> TargetGame:
    """Search SensorTower for the unified app id + extract its real category.

    Fictional / unreleased games won't match — return a synthetic target so the
    rest of the pipeline can still run. Downstream activities don't depend on
    app_id but DO benefit from `category_id` if we can pull it from the match.

    When `inp.genre` is provided (from project.json or GDD), we prefer the
    genre-derived category over the SensorTower match's category — because the
    match may be a completely different game (e.g., searching "Mini Slayer"
    returns "Mighty DOOM" which is in a different subcategory).
    """
    genre_cat = _genre_to_category(inp.genre)

    res = st.search_entities(inp.term, os_="unified", entity_type="app", limit=5)
    apps = res if isinstance(res, list) else (res.get("apps") or res.get("results") or [])
    if not apps:
        activity.logger.info("no SensorTower match for %r — using synthetic target", inp.term)
        return TargetGame(
            app_id="", name=inp.term, publisher_name=None,
            category_id=genre_cat,
            raw={"synthetic": True, "term": inp.term, "genre": inp.genre},
        )
    a = apps[0]
    match_cat = _extract_category_from_app(a)
    matched_name = a.get("name", "")
    name_match = inp.term.lower().replace(" ", "") in matched_name.lower().replace(" ", "")
    effective_cat = match_cat if name_match else (genre_cat or match_cat)
    activity.logger.info(
        f"[resolve_target_game] '{inp.term}' → matched '{matched_name}', "
        f"name_match={name_match}, category_from_match={match_cat}, "
        f"genre_cat={genre_cat}, effective={effective_cat}"
    )
    return TargetGame(
        app_id=str(a.get("app_id") or a.get("id") or ""),
        name=a.get("name", inp.term),
        publisher_name=a.get("publisher_name"),
        category_id=effective_cat,
        raw={**a, "genre": inp.genre},
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
