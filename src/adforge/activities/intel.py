"""Activities for the market_intel pipeline.

All LLM/vision work goes through Claude (Sonnet) — no Gemini, no Veo.
Frames already exist on disk (extract_keyframes ran first); this file:

  - gather_project_context      reads GDD/text docs + lists assets
  - infer_genre                 Claude vision: frames + text → genre/subgenre/category
  - analyze_competitors         Claude: project context vs SensorTower data
  - write_storyboards           Claude: playable + non-interactive video boards
  - render_slide_deck           assembles a single-file HTML deck (no external assets)
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from temporalio import activity

from adforge.config import PROJECTS_DIR, settings
from adforge.utils import strip_json_fences


# ── shared models ────────────────────────────────────────────────────────────


class ProjectContext(BaseModel):
    project_id: str
    name: str
    genre_hint: str | None = None
    description: str | None = None
    docs_text: str = ""
    asset_names: list[str] = Field(default_factory=list)
    frame_paths: list[str] = Field(default_factory=list)
    category_id: str = "7012"
    country: str = "US"


class GenreResult(BaseModel):
    genre: str
    subgenre: str
    category_id: str
    search_terms: list[str] = Field(default_factory=list)
    rationale: str = ""


class CompetitiveAnalysis(BaseModel):
    closest_competitors: list[dict[str, Any]] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    positioning: str = ""
    key_features: list[str] = Field(default_factory=list)
    genre_competitors: list[dict[str, Any]] = Field(default_factory=list)  # icon_url + meta from SensorTower search
    # v3: pre-shortened copy + enriched competitor data so the deck doesn't truncate
    challenges_short: list[str] = Field(default_factory=list)
    opportunities_short: list[str] = Field(default_factory=list)
    key_features_short: list[str] = Field(default_factory=list)
    positioning_short: str = ""
    competitor_data: list[dict[str, Any]] = Field(default_factory=list)
    # v4: per-competitor takeaway so the merged competitor slide carries Claude's
    # "what to steal" line on every card, not just the top 4.
    genre_competitor_takeaways: list[dict[str, Any]] = Field(default_factory=list)
    competitor_ad_insights: list[dict[str, Any]] = Field(default_factory=list)


class Storyboards(BaseModel):
    playable_md: str
    video_md: str
    # v3: structured beats with low-fi SVG sketches the deck renders inline
    playable_visual: dict[str, Any] | None = None
    video_visual: dict[str, Any] | None = None


# ── 1. gather_project_context ────────────────────────────────────────────────


def _strip_rtf(text: str) -> str:
    plain = re.sub(r"\\[a-z]+\-?\d* ?", " ", text)
    plain = re.sub(r"[\\{}]", " ", plain)
    plain = re.sub(r"\s+", " ", plain)
    return plain.strip()


def _read_docs(project_dir: Path) -> str:
    doc_paths = [
        p for p in project_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() in (".rtf", ".txt", ".md")
        and not any(part.startswith(".") for part in p.relative_to(project_dir).parts)
    ]
    doc_paths.sort(
        key=lambda p: (
            0 if re.search(r"\b(gdd|game.?design|rules|design.?doc)\b", p.name, re.I) else 1,
            len(p.relative_to(project_dir).parts),
            str(p.relative_to(project_dir)).lower(),
        )
    )

    snippets: list[str] = []
    for p in doc_paths[:6]:
        raw = p.read_text(errors="replace")
        text = _strip_rtf(raw) if p.suffix.lower() == ".rtf" else raw
        rel = p.relative_to(project_dir)
        snippets.append(f"=== {rel} ===\n{text[:12000]}")
    return "\n\n".join(snippets)


class GatherContextInput(BaseModel):
    project_id: str
    frame_paths: list[str] = Field(default_factory=list)


@activity.defn(name="intel_gather_context")
async def gather_project_context(inp: GatherContextInput) -> ProjectContext:
    from adforge import projects as projects_mod

    project = projects_mod.load(inp.project_id)
    project_dir = Path(project.project_dir)

    docs = _read_docs(project_dir)
    asset_names: list[str] = []
    if project.asset_dir:
        asset_root = Path(project.asset_dir)
        if asset_root.exists():
            asset_names = sorted(
                f.name for f in asset_root.iterdir() if not f.name.startswith(".")
            )

    return ProjectContext(
        project_id=project.id,
        name=project.name,
        genre_hint=project.genre,
        description=project.description,
        docs_text=docs,
        asset_names=asset_names,
        frame_paths=inp.frame_paths,
        category_id=project.category_id,
        country=project.country,
    )


# ── 2. infer_genre (Claude vision) ──────────────────────────────────────────


def _claude_client():
    from anthropic import Anthropic

    key = settings().anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")
    return Anthropic(api_key=key)


def _image_block(path: str) -> dict:
    data = base64.standard_b64encode(Path(path).read_bytes()).decode()
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": data},
    }


def _claude_json(
    user_blocks: list[dict],
    *,
    system: str,
    schema_hint: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2000,
) -> dict:
    """Call Claude with a multimodal user message and parse the JSON reply."""
    client = _claude_client()
    blocks = list(user_blocks) + [
        {
            "type": "text",
            "text": (
                "Return ONLY a valid JSON object — no markdown fences, no commentary.\n"
                f"Schema:\n{schema_hint}"
            ),
        }
    ]
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0.2,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": blocks}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return json.loads(strip_json_fences(raw))


def _claude_text(
    user_blocks: list[dict],
    *,
    system: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2500,
    temperature: float = 0.4,
) -> str:
    client = _claude_client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_blocks}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


@activity.defn(name="intel_infer_genre")
async def infer_genre(ctx: ProjectContext) -> GenreResult:
    activity.heartbeat("infer_genre: building prompt")

    images = [_image_block(p) for p in ctx.frame_paths[:6]]
    text = (
        f"Game name: {ctx.name}\n"
        f"Project-supplied genre hint: {ctx.genre_hint or '(none)'}\n"
        f"Description: {ctx.description or '(none)'}\n\n"
        f"Visual assets in folder: {', '.join(ctx.asset_names[:30]) or '(none)'}\n\n"
        f"Game design / context docs:\n{ctx.docs_text or '(none)'}\n\n"
        f"Above are {len(images)} keyframes from a gameplay video (if any).\n\n"
        "Determine the game's genre, subgenre, and the closest App Store / SensorTower "
        "category id for competitive lookups. Use the visuals + docs as primary evidence."
    )

    schema = """{
  "genre": "primary genre, e.g. 'arcade roguelike'",
  "subgenre": "specific niche, e.g. 'top-down survivor / bullet-heaven'",
  "category_id": "App Store category id used by SensorTower, default '7012' (Games)",
  "search_terms": ["3-5 search terms to find direct competitors on SensorTower"],
  "rationale": "1-2 sentences on why this classification fits"
}"""

    activity.heartbeat("infer_genre: calling Claude vision")
    result = _claude_json(
        images + [{"type": "text", "text": text}],
        system=(
            "You are a mobile game market analyst. "
            "You classify games into the App Store / SensorTower category taxonomy "
            "using visual evidence (gameplay frames) and design docs."
        ),
        schema_hint=schema,
    )
    return GenreResult(
        genre=str(result.get("genre", ctx.genre_hint or "unknown")),
        subgenre=str(result.get("subgenre", "")),
        category_id=str(result.get("category_id", ctx.category_id)),
        search_terms=list(result.get("search_terms", [])),
        rationale=str(result.get("rationale", "")),
    )


# ── 3. analyze_competitors (Claude text) ─────────────────────────────────────


class AnalyzeInput(BaseModel):
    config_id: str = "default"
    context: ProjectContext
    genre: GenreResult
    market: dict[str, Any]


def _condense_advertisers(market: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    apps = (market.get("top_advertisers") or {}).get("apps") or (
        market.get("top_advertisers") or {}
    ).get("results") or []
    if not apps and isinstance(market.get("top_advertisers"), list):
        apps = market["top_advertisers"]
    for a in apps[:limit]:
        out.append(
            {
                "name": a.get("name") or a.get("humanized_name"),
                "publisher": a.get("publisher_name"),
                "share_of_voice": a.get("share_of_voice") or a.get("sov") or a.get("aiv"),
                "app_id": a.get("app_id") or a.get("id"),
            }
        )
    return out


def _condense_creatives(market: dict[str, Any], limit: int = 15) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    units = (market.get("top_creatives") or {}).get("ad_units") or []
    seen: set[str] = set()
    for au in units:
        app_name = (au.get("app_info") or {}).get("name")
        for cr in au.get("creatives", []) or []:
            cid = cr.get("id") or cr.get("creative_id")
            if cid in seen:
                continue
            seen.add(cid)
            out.append(
                {
                    "app": app_name,
                    "message": cr.get("message"),
                    "duration_s": cr.get("video_duration"),
                    "ad_type": au.get("ad_type"),
                    "network": au.get("network"),
                }
            )
            if len(out) >= limit:
                return out
    return out


def _fetch_genre_competitors(genre: GenreResult, limit_per_term: int = 4) -> list[dict[str, Any]]:
    """Use the inferred subgenre search terms to find specific competitor apps via
    SensorTower search_entities — sidesteps the broad-category top-charts problem
    where unrelated chart-toppers (e.g. 'That's My Seat') drown out genre matches.
    """
    from adforge.connectors import sensortower as st

    seen: dict[str, dict[str, Any]] = {}
    for term in (genre.search_terms or [])[:5]:
        if not term:
            continue
        try:
            res = st.search_entities(term, os_="unified", entity_type="app", limit=limit_per_term)
        except Exception as e:
            activity.logger.warning(f"search_entities({term!r}) failed: {e}")
            continue
        apps = res if isinstance(res, list) else (res.get("apps") or res.get("results") or [])
        for a in apps:
            app_id = str(a.get("app_id") or a.get("id") or "")
            if not app_id or app_id in seen:
                continue
            release = a.get("release_date") or ""
            if isinstance(release, str) and len(release) >= 10:
                release = release[:10]
            seen[app_id] = {
                "app_id": app_id,
                "name": a.get("name") or a.get("humanized_name"),
                "publisher": a.get("publisher_name"),
                "icon_url": a.get("icon_url"),
                "rating_count": int(a.get("global_rating_count") or 0),
                "categories": list(a.get("categories") or [])[:3],
                "release_date": release,
                "found_via": term,
            }
    return list(seen.values())[:20]


def _download_image_b64(url: str, *, timeout: float = 8.0) -> str | None:
    """Fetch a small image (e.g. app icon) and return as base64 data URL."""
    if not url:
        return None
    import requests

    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None
        media_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
        b = base64.standard_b64encode(resp.content).decode()
        return f"data:{media_type};base64,{b}"
    except Exception:
        return None


def _extract_palette(frame_paths: list[str], n_colors: int = 5) -> list[str]:
    """Pull dominant hex colors from the first few keyframes using PIL quantize.

    Returns up to n_colors deduped hex strings ordered by frequency.
    """
    if not frame_paths:
        return []
    try:
        from PIL import Image
    except ImportError:
        return []

    counts: dict[str, int] = {}
    for p in frame_paths[:4]:
        try:
            img = Image.open(p).convert("RGB").resize((128, 128))
            q = img.quantize(colors=n_colors * 2, method=Image.Quantize.MEDIANCUT)
            palette = q.getpalette() or []
            color_counts = q.getcolors() or []
            for cnt, idx in color_counts:
                r = palette[idx * 3]
                g = palette[idx * 3 + 1]
                b = palette[idx * 3 + 2]
                hex_c = f"#{r:02x}{g:02x}{b:02x}"
                counts[hex_c] = counts.get(hex_c, 0) + cnt
        except Exception as e:
            activity.logger.warning(f"palette extraction failed for {p}: {e}")
            continue
    sorted_colors = sorted(counts.items(), key=lambda kv: -kv[1])
    out: list[str] = []
    for hex_c, _ in sorted_colors:
        if hex_c not in out:
            out.append(hex_c)
        if len(out) >= n_colors:
            break
    return out


@activity.defn(name="intel_analyze_competitors")
async def analyze_competitors(inp: AnalyzeInput) -> CompetitiveAnalysis:
    activity.heartbeat("condensing market data")
    advertisers = _condense_advertisers(inp.market)
    creatives = _condense_creatives(inp.market)

    # v2+: fetch genre-specific competitors via SensorTower search instead of
    # relying on the broad category top-charts (which leak unrelated games).
    is_v5 = inp.config_id == "intel-presentation-v5"
    is_v6 = inp.config_id == "intel-presentation-v6"
    is_v7 = inp.config_id == "intel-presentation-v7"
    is_v4 = inp.config_id == "intel-presentation-v4"
    is_v4_plus = is_v4 or is_v5 or is_v6 or is_v7
    is_v3_or_v4 = inp.config_id in ("intel-presentation-v3", "intel-presentation-v4")
    is_v3_plus = inp.config_id in (
        "intel-presentation-v3", "intel-presentation-v4",
        "intel-presentation-v5", "intel-presentation-v6", "intel-presentation-v7",
    )
    is_v2_plus = inp.config_id in (
        "intel-presentation-v2", "intel-presentation-v3",
        "intel-presentation-v4", "intel-presentation-v5",
        "intel-presentation-v6", "intel-presentation-v7",
    )
    is_v3 = is_v3_or_v4  # legacy alias used below
    is_v2_or_v3 = is_v2_plus  # legacy alias used below
    genre_competitors: list[dict[str, Any]] = []
    if is_v2_plus:
        activity.heartbeat("fetching genre-specific competitors")
        # Wider competitor net at higher tiers — v5 widest so the merged
        # competitor slide can show 10–12 ranked cards.
        per_term = 8 if (is_v5 or is_v6 or is_v7) else (6 if is_v4 else 4)
        genre_competitors = _fetch_genre_competitors(inp.genre, limit_per_term=per_term)
        activity.logger.info(f"genre-specific competitors: {len(genre_competitors)} apps")

    genre_match_block = ""
    if genre_competitors:
        genre_match_block = (
            "\n## Genre-specific competitor apps (SensorTower search, scoped to this game's subgenre)\n"
            "PREFER these over the broad top-advertisers list when picking 'closest competitors' — "
            "the top-advertisers list contains unrelated chart-toppers (e.g. casual puzzlers) that "
            "happen to dominate the broader category but aren't real competition for this game.\n"
            f"{json.dumps([{k: v for k, v in g.items() if k != 'icon_url'} for g in genre_competitors], indent=2)}\n"
        )

    user_text = f"""## Project under analysis
Name: {inp.context.name}
Genre: {inp.genre.genre} / {inp.genre.subgenre}
Description: {inp.context.description or '(none)'}
Visual assets: {', '.join(inp.context.asset_names[:30]) or '(none)'}
Design doc summary:
{inp.context.docs_text[:12000] or '(none)'}

## Top advertisers in this category (SensorTower — broad category, may include unrelated games)
{json.dumps(advertisers, indent=2)}

## Top winning creatives in this category
{json.dumps(creatives, indent=2)}
{genre_match_block}
## Your task
Compare the project to this competitive landscape and produce a structured market analysis.
Be specific — name actual games and creatives. Avoid generic platitudes.
When picking closest_competitors, prioritize genre-matched games over unrelated chart-toppers.
"""

    if is_v4_plus:
        # v4+: like v3 short copy, plus per-genre-competitor takeaway lines so
        # the merged competitor slide carries Claude's "what to steal" on every
        # card. v5+ asks for takeaways on a wider set so the bigger card grid is
        # fully labelled (the genre_competitors list with names + app_ids is
        # already in `user_text`).
        n_takeaways = 12 if (is_v5 or is_v6 or is_v7) else 8
        per_genre_block = ""
        if genre_competitors:
            per_genre_block = (
                "\n\n## Genre-matched competitors needing per-card takeaways\n"
                + json.dumps(
                    [
                        {"app_id": g.get("app_id"), "name": g.get("name"), "rating_count": g.get("rating_count")}
                        for g in genre_competitors[:n_takeaways]
                    ],
                    indent=2,
                )
            )
        user_text = user_text + per_genre_block
        if is_v6 or is_v7:
            user_text += """

V6/V7 PRESENTATION REQUIREMENTS:
- Slides 4 and 5 will show your full challenge/opportunity text, not just headlines.
- Make every challenge/opportunity a useful executive note: state the market problem, why it matters for advertising, and a concrete action path.
- Slide 6 will show the full positioning, so make it concrete: who to outflank, what ad promise to own, what visual proof to lead with, and what to avoid.
- Competitor takeaways should focus on how each Solid+ competitor advertises or what their ad angle teaches us, not generic product lessons.
"""
        if is_v7:
            user_text += """

V7 STRATEGIC CONSISTENCY RULES:
- Challenges and opportunities must NOT be the same fact phrased two ways.
- A challenge is an external obstacle or risk that blocks adoption.
- An opportunity is a concrete unfair advantage, wedge, or exploitable creative opening.
- If a niche has "low awareness", that is a challenge; do not also call the same low awareness "wide open" unless the opportunity explains a different proof-backed wedge.
- For competitor insights, privilege ad activity, share-of-voice, creative messages, hooks, and observed trends over raw ratings.
"""
        schema = """{
  "closest_competitors": [
    {"name": "Game name", "why": "1 short sentence", "what_to_steal": "1 short sentence"}
  ],
  "challenges":      ["full sentence", "..."],
  "challenges_short":      ["≤10 words, punchy headline", "..."],
  "opportunities":   ["full sentence", "..."],
  "opportunities_short":   ["≤10 words, punchy headline", "..."],
  "positioning":       "one paragraph: how this game should be positioned in market",
  "positioning_short": "1 sentence ≤25 words — the core positioning idea",
  "key_features":       ["full description: feature - why it matters for marketing", "..."],
  "key_features_short": ["3-7 word headline of the marketable feature", "..."],
  "genre_competitor_takeaways": [
    {"app_id": "matches the input list", "takeaway": "≤14 words — what this game teaches us about the category"}
  ]
}

CRITICAL: every '_short' value MUST already be short — do NOT pad them. They are rendered verbatim as card titles.
For v6-style output, each full challenge/opportunity should be 2 sentences: sentence 1 = context/diagnosis; sentence 2 = "Action path: ..." with a concrete marketing move.
Provide exactly 3 challenges, 3 opportunities, 4 key_features, and one genre_competitor_takeaways entry per app in the genre-matched list above."""
    elif is_v3:
        # v3: ask Claude for BOTH headline + detail. Deck shows headlines (no truncation).
        schema = """{
  "closest_competitors": [
    {"name": "Game name", "why": "1 short sentence", "what_to_steal": "1 short sentence"}
  ],
  "challenges":      ["full sentence", "..."],
  "challenges_short":      ["≤10 words, punchy headline", "..."],
  "opportunities":   ["full sentence", "..."],
  "opportunities_short":   ["≤10 words, punchy headline", "..."],
  "positioning":       "one paragraph: how this game should be positioned in market",
  "positioning_short": "1 sentence ≤25 words — the core positioning idea",
  "key_features":       ["full description: feature - why it matters for marketing", "..."],
  "key_features_short": ["3-7 word headline of the marketable feature", "..."]
}

CRITICAL: every '_short' value MUST already be short — do NOT pad them. They are rendered verbatim onto presentation slides.
Provide exactly 3 challenges, 3 opportunities, 4 key_features."""
    else:
        schema = """{
  "closest_competitors": [
    {"name": "Game name", "why": "what makes them comparable", "what_to_steal": "the lesson"}
  ],
  "challenges": ["specific challenge to overcome", "..."],
  "opportunities": ["specific gap or angle this project can own", "..."],
  "positioning": "one paragraph: how this game should be positioned in market",
  "key_features": ["specific feature/asset that should be leveraged in marketing", "..."]
}"""

    activity.heartbeat("calling Claude for analysis")
    images = [_image_block(p) for p in inp.context.frame_paths[:4]]
    result = _claude_json(
        images + [{"type": "text", "text": user_text}],
        system=(
            "You are a senior mobile games market strategist. "
            "You write specific, evidence-based analyses that name competitor games, "
            "identify concrete opportunities, and translate visual/gameplay evidence "
            "into marketing positioning. No generic advice."
        ),
        schema_hint=schema,
        max_tokens=3500,
    )
    # v2+: download icons once so render is offline-fast.
    if is_v2_plus:
        activity.heartbeat("downloading competitor icons")
        for comp in genre_competitors:
            url = comp.get("icon_url")
            if url:
                comp["icon_b64"] = _download_image_b64(url)

    # v3+: enrich with rating count / categories / publisher / release_date so the deck
    # can show real competitive data points, not just names.
    competitor_data: list[dict[str, Any]] = []
    if is_v3_plus and genre_competitors:
        activity.heartbeat("fetching competitor app metadata")
        max_apps = 12 if (is_v5 or is_v6 or is_v7) else 8
        competitor_data = _fetch_competitor_metadata(genre_competitors, max_apps=max_apps)
        if is_v5 or is_v6 or is_v7:
            # v5+: add Scale tier (proxy for users from public rating count) and
            # cross-reference Share-of-Voice from the broad-category top advertisers
            # already fetched above (real spend signal where the genre app appears).
            sov_by_name: dict[str, float] = {}
            for a in advertisers or []:
                nm = (a.get("name") or "").strip().lower()
                sov = a.get("share_of_voice")
                if nm and sov is not None:
                    try:
                        sov_by_name[nm] = float(sov)
                    except (TypeError, ValueError):
                        pass
            for d in competitor_data:
                d["scale_tier"] = _scale_tier(int(d.get("rating_count") or 0))
                nm = (d.get("name") or "").strip().lower()
                if nm in sov_by_name:
                    d["share_of_voice"] = sov_by_name[nm]
                else:
                    for adv_nm, sov in sov_by_name.items():
                        if nm and (nm in adv_nm or adv_nm in nm):
                            d["share_of_voice"] = sov
                            break
            if is_v6 or is_v7:
                activity.heartbeat("v6: fetching competitor creative activity")
                _enrich_competitor_ad_activity(competitor_data)

    return CompetitiveAnalysis(
        closest_competitors=list(result.get("closest_competitors", [])),
        challenges=list(result.get("challenges", [])),
        opportunities=list(result.get("opportunities", [])),
        positioning=str(result.get("positioning", "")),
        key_features=list(result.get("key_features", [])),
        genre_competitors=genre_competitors,
        challenges_short=list(result.get("challenges_short", [])),
        opportunities_short=list(result.get("opportunities_short", [])),
        positioning_short=str(result.get("positioning_short", "")),
        key_features_short=list(result.get("key_features_short", [])),
        competitor_data=competitor_data,
        genre_competitor_takeaways=list(result.get("genre_competitor_takeaways", [])),
        competitor_ad_insights=[
            {
                "app_id": d.get("app_id"),
                "name": d.get("name"),
                "scale_tier": d.get("scale_tier"),
                "ad_activity": d.get("ad_activity"),
                "creative_examples": d.get("creative_examples", []),
            }
            for d in competitor_data
            if d.get("ad_activity") or d.get("creative_examples")
        ],
    )


def _normalize_name(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def _first_previous_month() -> str:
    return time.strftime("%Y-%m-01", time.gmtime(time.time() - 30 * 86400))


def _creative_examples(payload: dict[str, Any], *, limit: int = 3) -> tuple[int, list[str], list[str]]:
    units = payload.get("ad_units") or payload.get("results") or []
    networks: set[str] = set()
    examples: list[str] = []
    count = 0
    if isinstance(units, list):
        for unit in units:
            network = unit.get("network")
            if network:
                networks.add(str(network))
            creatives = unit.get("creatives") or []
            if creatives:
                count += len(creatives)
                for cr in creatives:
                    msg = (cr.get("message") or "").strip()
                    if msg and msg not in examples:
                        examples.append(msg[:120])
                    if len(examples) >= limit:
                        break
            else:
                count += 1
            if len(examples) >= limit:
                continue
    return count, sorted(networks), examples[:limit]


def _enrich_competitor_ad_activity(competitor_data: list[dict[str, Any]]) -> None:
    """For v6, augment Solid+ genre competitors with their own recent ad activity.

    Ratings tell us scale; this tells us whether the game is actively buying
    attention and what messages appear in its current creatives.
    """
    from adforge.connectors import sensortower as st

    candidates = [
        d for d in competitor_data
        if (d.get("scale_tier") in {"Mega Hit", "Hit", "Solid"} or int(d.get("rating_count") or 0) >= 10_000)
        and d.get("app_id")
    ][:8]
    start_date = _first_previous_month()
    for d in candidates:
        try:
            payload = st.app_creatives(
                [str(d["app_id"])],
                start_date=start_date,
                networks="TikTok,Admob,Unity,Facebook,Instagram,Mintegral",
                ad_types="video,video-interstitial,playable,image,banner,full_screen",
                limit=40,
            )
        except Exception as e:
            activity.logger.warning(f"app_creatives({d.get('name')}) failed: {e}")
            continue
        count, networks, examples = _creative_examples(payload)
        if count or networks or examples:
            d["ad_activity"] = {
                "creative_count": count,
                "networks": networks[:5],
                "active": count > 0,
            }
            d["creative_examples"] = examples


def _scale_tier(rating_count: int) -> str:
    """Public-data proxy for "users / downloads" — derived from the global
    cumulative review count search_entities returns. Conservative buckets so
    the badge is meaningful, not flattering: very few games clear 1M reviews.
    """
    if rating_count >= 1_000_000:
        return "Mega Hit"
    if rating_count >= 100_000:
        return "Hit"
    if rating_count >= 10_000:
        return "Solid"
    if rating_count >= 1_000:
        return "Niche"
    return "Long Tail"


def _fetch_competitor_metadata(
    genre_competitors: list[dict[str, Any]], *, max_apps: int = 8,
) -> list[dict[str, Any]]:
    """search_entities already returns rich app fields (rating_count, categories,
    release_date) inline. We just project + sort here — no extra API calls.
    The /v1/unified/apps endpoint is sparse (only IDs), so it's not worth a follow-up.
    """
    enriched: list[dict[str, Any]] = []
    for comp in genre_competitors[:max_apps]:
        if not comp.get("app_id"):
            continue
        enriched.append(
            {
                "app_id": comp["app_id"],
                "name": comp.get("name"),
                "publisher": comp.get("publisher"),
                "icon_b64": comp.get("icon_b64"),
                "icon_url": comp.get("icon_url"),
                "rating_count": int(comp.get("rating_count") or 0),
                "categories": list(comp.get("categories") or [])[:3],
                "release_date": comp.get("release_date") or "",
                "found_via": comp.get("found_via"),
            }
        )
    enriched.sort(key=lambda d: d.get("rating_count") or 0, reverse=True)
    return enriched


# ── 4. write_storyboards (Claude text) ───────────────────────────────────────


class StoryboardsInput(BaseModel):
    config_id: str = "default"
    context: ProjectContext
    genre: GenreResult
    analysis: CompetitiveAnalysis


_PLAYABLE_PROMPT = """\
Write a playable-ad storyboard. Format the output as Markdown with these sections:

# Playable Ad Storyboard — {name}

## Concept (1 paragraph)
The hook archetype, the "smallest fun loop", and the emotional payoff.

## CONFIG block (parameters a developer would tune)
List 8–12 named parameters with proposed default values (e.g. enemySpeed: 80, spawnEverySeconds: 1.2).
Each one should be tied to a specific gameplay or pacing decision.

## Beat-by-beat (each beat = 1–2 seconds, total 12–18s)
For each beat: visual, player action prompted, system response, and on-screen text.
Use the actual character/enemy/item names from the assets — never placeholders.

## End-card
One sentence + the CTA.

## Variants to A/B test (3 short bullets)
Each variant changes ONE config knob and explains the hypothesis.
"""

_VIDEO_PROMPT = """\
Write a non-interactive video ad storyboard (8 seconds, 9:16 vertical). Format as Markdown:

# Video Ad Storyboard — {name}

## Hook archetype
One of: near-fail/cliffhanger, visual-anomaly, POV/first-person, text-overlay-question,
narrative-cliffhanger, rage-bait, satisfying-completion, status-fantasy. Justify in one line.

## Frame 1 (0.0s)
The single most arresting visual using this game's actual characters/colors.

## Beat map (8s, second-by-second)
- 0–2s Hook
- 2–5s Gameplay reveal
- 5–7s Escalation / payoff
- 7–8s CTA card with exact overlay text

Each beat: visual + on-screen text + audio cue.

## Variants to A/B test (3 bullets)
Different hook archetype each, same payoff.
"""


_PLAYABLE_PRINCIPLES = """\
PLAYABLE AD PLAYBOOK (distilled):
• 3-second rule — frame 1 must answer: what am I looking at? what can I do? why care?
• ONE hook archetype, not blended: near-fail tease, fake-fail/wrong-choice, satisfying-completion,
  puzzle-with-bad-solution, before-after-transformation, pull-to-aim, rage-bait, asmr/sensory,
  narrative-reveal, humor-fail.
• ONE input — tap, drag, or hold. Two inputs = installs lost.
• Self-evident — figure out without tutorial in <2s.
• 30-second slice: one mechanic, repeatable wins. Not the whole game.
• Juice everywhere — every tap returns particles, color shift, sound.
• End-card: hero + win-state + single short CTA verb."""


def _structured_storyboard_prompt(kind: str, name: str, palette: list[str], principles: str) -> str:
    pal = ", ".join(palette[:5]) or "#0b0b10, #f0f1f5, #ff8866"
    return f"""Produce a structured storyboard JSON for a {kind} ad for "{name}".

Use this exact schema:
{{
  "archetype": "the single hook archetype, name it",
  "concept": "one short sentence — the core idea",
  "beats": [
    {{
      "time": "0-2s",
      "label": "Hook" (or 'Reveal' / 'Escalation' / 'CTA'),
      "visual": "what's on screen — ≤14 words, concrete and specific",
      "text": "exact on-screen text overlay (or empty string for none) — ≤6 words",
      "audio": "sound design cue — ≤8 words",
      "svg": "<see SVG rules>"
    }},
    ... exactly 4 beats covering Hook → Reveal → Escalation/Payoff → CTA ...
  ],
  "cta": "exact CTA copy — ≤5 words"
}}

SVG RULES (critical):
- The 'svg' value is the INNER content of an <svg viewBox="0 0 200 356"> (do NOT include the <svg> wrapper).
- Use ONLY these elements: <rect>, <circle>, <ellipse>, <line>, <path>, <polygon>, <text>, <g>.
- NO filters, NO gradients, NO <image>, NO external refs.
- Use ONLY these palette colors as fill/stroke (extracted from the actual game): {pal}.
- Style: rough storyboard sketch — 6-15 simple shapes. Suggest the composition, do not render the game.
- Each beat's SVG should look visually distinct from the others — different framing, subjects.
- Include 1 short label as <text> (max ~3 words) when it adds clarity, font-family Arial sans-serif.

{principles}

CRITICAL: Every text field has a hard word cap. Do NOT exceed it. The deck renders these verbatim.
Output ONLY the JSON object."""


def _v4_storyboard_prompt(kind: str, name: str, principles: str) -> str:
    """v4: rich text per beat, no SVG. Snake-flow text-heavy storyboards.
    Each beat carries enough copy that the reader understands the moment without an image.
    """
    beats_n = 4 if kind == "non-interactive video" else 5
    return f"""Produce a structured storyboard JSON for a {kind} ad for "{name}".

Use this exact schema:
{{
  "archetype": "the ONE hook archetype, named precisely",
  "concept": "1 sentence ≤20 words — the core idea the ad delivers",
  "beats": [
    {{
      "time": "e.g. '0–2s' for video, or '0–4s' for playable",
      "label": "Hook | Reveal | Mechanic | Escalation | Payoff | CTA",
      "visual": "2 short sentences describing what's on screen, naming actual game characters/colors/UI",
      "text": "exact on-screen text overlay (or empty string)",
      "audio": "1 line — sound design cue, ≤10 words",
      "why": "1 sentence — playbook rationale (why this beat earns the next, in playbook terms)"
    }},
    ... exactly {beats_n} beats covering the full arc, ordered ...
  ],
  "cta": "exact CTA copy ≤6 words"
}}

CONSTRAINTS:
- NO SVG, no images. Plain text only. The deck renders these beats as text cards in a snake (left-to-right) layout.
- Reference the actual game's characters, enemies, items, ability names by their real names.
- 'visual' must be specific and visualizable — a director should be able to storyboard from your words alone.
- 'why' must reference a specific playbook concept (the 1.7-second rule, hook archetype, beat principle, etc.).

{principles}

Output ONLY the JSON object."""


@activity.defn(name="intel_write_storyboards")
async def write_storyboards(inp: StoryboardsInput) -> Storyboards:
    is_v3 = inp.config_id == "intel-presentation-v3"
    # v5+ inherit v4's text-heavy snake storyboard format (no SVG, rich beats).
    is_v4 = inp.config_id in (
        "intel-presentation-v4", "intel-presentation-v5",
        "intel-presentation-v6", "intel-presentation-v7",
    )

    activity.heartbeat("writing storyboards")
    base_user = (
        f"## Game\n{inp.context.name} — {inp.genre.genre} / {inp.genre.subgenre}\n\n"
        f"## Description\n{inp.context.description or '(none)'}\n\n"
        f"## Visual assets to leverage\n{', '.join(inp.context.asset_names[:30]) or '(none)'}\n\n"
        f"## Design doc excerpt\n{inp.context.docs_text[:10000] or '(none)'}\n\n"
        f"## Positioning\n{inp.analysis.positioning}\n\n"
        f"## Key features to leverage\n- " + "\n- ".join(inp.analysis.key_features) + "\n\n"
        f"## Closest competitors (lessons)\n"
        + "\n".join(
            f"- {c.get('name', '?')}: {c.get('what_to_steal', '')}"
            for c in inp.analysis.closest_competitors[:5]
        )
    )

    images = [_image_block(p) for p in inp.context.frame_paths[:4]]

    # Always produce the markdown storyboards (existing behavior, used by v0/v1 decks).
    playable_md = _claude_text(
        images
        + [
            {
                "type": "text",
                "text": base_user
                + "\n\n"
                + _PLAYABLE_PROMPT.format(name=inp.context.name),
            }
        ],
        system=(
            "You are a senior mobile playable ad designer. "
            "You write storyboards that read like dev specs — concrete enough to build from. "
            "You always reference the actual game's characters, enemies, and visuals by name."
        ),
        max_tokens=2500,
    )

    activity.heartbeat("writing video storyboard")
    video_md = _claude_text(
        images
        + [
            {
                "type": "text",
                "text": base_user
                + "\n\n"
                + _VIDEO_PROMPT.format(name=inp.context.name),
            }
        ],
        system=(
            "You are a senior mobile video ad creative director. "
            "You write storyboards grounded in the game's actual visual language. "
            "First 1.7 seconds is everything. Reference real characters by name."
        ),
        max_tokens=2000,
    )

    # v3: structured JSON beats WITH inline SVG sketches per beat.
    # v4: structured JSON beats with richer text (visual + on-screen + audio + playbook rationale), NO SVGs.
    playable_visual: dict[str, Any] | None = None
    video_visual: dict[str, Any] | None = None
    if is_v3 or is_v4:
        palette = _extract_palette(inp.context.frame_paths, n_colors=5)

        if is_v4:
            playable_prompt_body = _v4_storyboard_prompt("playable", inp.context.name, _PLAYABLE_PRINCIPLES)
            video_prompt_body = _v4_storyboard_prompt("non-interactive video", inp.context.name, _VIDEO_AD_PRINCIPLES_INLINE)
            tag = "v4"
        else:
            playable_prompt_body = _structured_storyboard_prompt(
                "playable", inp.context.name, palette, _PLAYABLE_PRINCIPLES
            )
            video_prompt_body = _structured_storyboard_prompt(
                "non-interactive video", inp.context.name, palette, _VIDEO_AD_PRINCIPLES_INLINE
            )
            tag = "v3"

        activity.heartbeat(f"{tag}: generating playable storyboard")
        try:
            playable_visual = _claude_json(
                images + [{"type": "text", "text": base_user + "\n\n" + playable_prompt_body}],
                system=(
                    "You are a senior mobile playable ad designer. "
                    "You produce structured storyboard JSON that follows the playbook rigorously and respects strict word caps."
                ),
                schema_hint="(see prompt — return that exact shape)",
                max_tokens=4500,
            )
        except Exception as e:
            activity.logger.warning(f"playable visual storyboard failed: {e}")
            playable_visual = None

        activity.heartbeat(f"{tag}: generating video storyboard")
        try:
            video_visual = _claude_json(
                images + [{"type": "text", "text": base_user + "\n\n" + video_prompt_body}],
                system=(
                    "You are a senior mobile video ad creative director. "
                    "You produce structured storyboard JSON that follows the playbook rigorously and respects strict word caps."
                ),
                schema_hint="(see prompt — return that exact shape)",
                max_tokens=4500,
            )
        except Exception as e:
            activity.logger.warning(f"video visual storyboard failed: {e}")
            video_visual = None

    return Storyboards(
        playable_md=playable_md,
        video_md=video_md,
        playable_visual=playable_visual,
        video_visual=video_visual,
    )


_VIDEO_AD_PRINCIPLES_INLINE = """\
VIDEO AD PLAYBOOK (distilled):
• Hook window = 1.7s. Frame 1 stops the scroll.
• ONE hook archetype: near-fail/cliffhanger, visual-anomaly, POV/first-person, text-overlay-question,
  narrative-cliffhanger, rage-bait, satisfying-completion, status-fantasy.
• Beat map (8s): Hook (0–2s) → Reveal (2–5s) → Escalation (5–7s) → CTA (7–8s).
• Show the actual mechanic — not a cinematic.
• Use the game's own characters, enemies, ability names by name.
• 3 audio beats: sharp impact, rhythmic drive, satisfying crunch on CTA.
• CTA matches the emotional hook — challenge for near-fail; "Try it" for satisfying."""


# ── 5. render_slide_deck (HTML, single-file) ─────────────────────────────────


class SlideDeckInput(BaseModel):
    config_id: str = "default"
    context: ProjectContext
    genre: GenreResult
    analysis: CompetitiveAnalysis
    storyboards: Storyboards
    out_path: str


class SlideDeckResult(BaseModel):
    html_path: str
    size_bytes: int


def _embed_image(p: Path) -> str:
    if not p.exists():
        return ""
    b = base64.standard_b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{b}"


def _md_to_html(md: str) -> str:
    """Tiny markdown → HTML converter (headings, bullets, paragraphs).

    Avoids pulling in a markdown lib; the output formatting is well-defined since
    we wrote the prompts ourselves.
    """
    out_lines: list[str] = []
    in_ul = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False
            out_lines.append("")
            continue
        if line.startswith("# "):
            if in_ul:
                out_lines.append("</ul>"); in_ul = False
            out_lines.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            if in_ul:
                out_lines.append("</ul>"); in_ul = False
            out_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            if in_ul:
                out_lines.append("</ul>"); in_ul = False
            out_lines.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.lstrip().startswith(("- ", "* ")):
            if not in_ul:
                out_lines.append("<ul>"); in_ul = True
            content = line.lstrip()[2:]
            out_lines.append(f"<li>{_inline(content)}</li>")
        else:
            if in_ul:
                out_lines.append("</ul>"); in_ul = False
            out_lines.append(f"<p>{_inline(line)}</p>")
    if in_ul:
        out_lines.append("</ul>")
    return "\n".join(out_lines)


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


_DECK_CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
       background: #0a0a0f; color: #eef0f4; overflow: hidden; }
.deck { position: relative; width: 100vw; height: 100vh; }
.slide { position: absolute; inset: 0; padding: 64px 80px; display: flex; flex-direction: column;
         opacity: 0; pointer-events: none; transition: opacity 0.25s ease;
         overflow-y: auto; overflow-x: hidden; }
.slide.active { opacity: 1; pointer-events: auto; }
.slide h1 { font-size: 48px; margin: 0 0 8px; font-weight: 700; letter-spacing: -0.02em; color: #ffffff; }
.slide h2 { font-size: 22px; margin: 8px 0; font-weight: 600; color: #c4c8d4; }
.slide h3 { font-size: 18px; margin: 20px 0 8px; font-weight: 600; color: #a8acb8; }
.slide p, .slide li { font-size: 17px; line-height: 1.55; color: #d8dae0; }
.slide ul { padding-left: 22px; }
.slide li { margin-bottom: 6px; }
.slide code { background: #1a1c25; padding: 1px 6px; border-radius: 4px; font-size: 14px; color: #ffd9a8; }
.eyebrow { font-size: 13px; text-transform: uppercase; letter-spacing: 0.18em; color: #6c7080;
           margin-bottom: 12px; font-weight: 600; }
.kicker { font-size: 28px; line-height: 1.25; color: #d8dae0; margin: 8px 0 24px; max-width: 860px; }
.title-slide { justify-content: center; align-items: flex-start; padding: 80px 100px; }
.title-slide h1 { font-size: 84px; line-height: 1; margin-bottom: 16px; }
.frame-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 24px; }
.frame-strip img { width: 100%; aspect-ratio: 9/16; object-fit: cover; border-radius: 8px;
                   background: #161821; }
.cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 16px; }
.card { background: #14161f; border: 1px solid #1f2230; border-radius: 12px; padding: 18px 22px; }
.card h3 { margin-top: 0; color: #ffd9a8; }
.card p { margin: 8px 0 0; font-size: 15px; }
.tag { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
       background: #1f2230; color: #c4c8d4; margin-right: 6px; }
.nav { position: fixed; bottom: 24px; right: 32px; display: flex; gap: 12px; align-items: center;
       z-index: 10; }
.nav button { background: #1f2230; color: #eef0f4; border: 1px solid #2a2d3d; border-radius: 8px;
              padding: 8px 14px; cursor: pointer; font-size: 14px; }
.nav button:hover { background: #2a2d3d; }
.nav .counter { font-size: 13px; color: #6c7080; min-width: 64px; text-align: center; }
.lower-third { font-size: 13px; color: #6c7080; position: absolute; bottom: 24px; left: 80px; }
.col { flex: 1; min-height: 0; }
.two-col { display: grid; grid-template-columns: 1.4fr 1fr; gap: 32px; align-items: start; }
.storyboard { background: #0f1118; padding: 28px 36px; border-radius: 12px; border: 1px solid #1f2230;
              max-height: calc(100vh - 220px); overflow-y: auto; }
.storyboard h1 { font-size: 22px; }
.storyboard h2 { font-size: 16px; color: #ffd9a8; }
.storyboard p, .storyboard li { font-size: 14px; }
"""

_DECK_JS = """
const slides = document.querySelectorAll('.slide');
let i = 0;
function show(n) {
  i = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, idx) => s.classList.toggle('active', idx === i));
  document.getElementById('counter').textContent = (i + 1) + ' / ' + slides.length;
}
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ') show(i + 1);
  if (e.key === 'ArrowLeft') show(i - 1);
});
show(0);
"""


def _slide_title(name: str, genre: GenreResult) -> str:
    return f"""<section class="slide title-slide">
  <div class="eyebrow">Market Intelligence Brief</div>
  <h1>{_e(name)}</h1>
  <p class="kicker">{_e(genre.genre)} · <strong>{_e(genre.subgenre)}</strong></p>
  <div class="lower-third">Generated by adforge · market_intel pipeline</div>
</section>"""


def _slide_identity(ctx: ProjectContext, genre: GenreResult) -> str:
    frames_html = ""
    if ctx.frame_paths:
        frames = "".join(
            f'<img src="{_embed_image(Path(p))}" alt="frame {i}"/>'
            for i, p in enumerate(ctx.frame_paths[:4])
        )
        frames_html = f'<div class="frame-strip">{frames}</div>'
    return f"""<section class="slide">
  <div class="eyebrow">Game Identity</div>
  <h1>What is {_e(ctx.name)}?</h1>
  <p>{_e(ctx.description or '(no description in project.json)')}</p>
  <h2 style="margin-top:18px">Classification</h2>
  <p><span class="tag">Genre</span> {_e(genre.genre)} &nbsp;
     <span class="tag">Subgenre</span> {_e(genre.subgenre)} &nbsp;
     <span class="tag">Category id</span> <code>{_e(genre.category_id)}</code></p>
  <p style="color:#a8acb8;font-size:14px"><em>{_e(genre.rationale)}</em></p>
  {frames_html}
</section>"""


def _slide_competitors(analysis: CompetitiveAnalysis) -> str:
    cards = "".join(
        f"""<div class="card">
  <h3>{_e(c.get('name', '?'))}</h3>
  <p><strong>Why comparable:</strong> {_e(c.get('why', ''))}</p>
  <p><strong>What to steal:</strong> {_e(c.get('what_to_steal', ''))}</p>
</div>"""
        for c in analysis.closest_competitors[:6]
    )
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1>Who we're up against</h1>
  <div class="cards">{cards}</div>
</section>"""


def _slide_two_lists(eyebrow: str, title: str, items: list[str]) -> str:
    lis = "".join(f"<li>{_e(s)}</li>" for s in items)
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1>{_e(title)}</h1>
  <ul>{lis}</ul>
</section>"""


def _slide_positioning(analysis: CompetitiveAnalysis) -> str:
    return f"""<section class="slide">
  <div class="eyebrow">Recommended Positioning</div>
  <h1>How we should show up</h1>
  <p style="font-size:22px;line-height:1.5;max-width:1000px">{_e(analysis.positioning)}</p>
</section>"""


def _slide_features(analysis: CompetitiveAnalysis) -> str:
    lis = "".join(f"<li>{_e(s)}</li>" for s in analysis.key_features)
    return f"""<section class="slide">
  <div class="eyebrow">Key Features for Marketing</div>
  <h1>What to lead with</h1>
  <ul>{lis}</ul>
</section>"""


def _slide_storyboard(eyebrow: str, md: str) -> str:
    body = _md_to_html(md)
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <div class="storyboard">{body}</div>
</section>"""


def _slide_summary(ctx: ProjectContext, genre: GenreResult, analysis: CompetitiveAnalysis) -> str:
    return f"""<section class="slide">
  <div class="eyebrow">Next Steps</div>
  <h1>Where to go from here</h1>
  <ul>
    <li>Run <code>creative_forge</code> with the asset-aware-video config to generate the video ad</li>
    <li>Run <code>playable_forge</code> to scaffold the playable HTML using the storyboard</li>
    <li>Validate the positioning against {len(analysis.closest_competitors)} closest competitors</li>
    <li>A/B test the {len(analysis.key_features)} key features identified for marketing</li>
  </ul>
  <p style="color:#6c7080;font-size:13px;margin-top:32px">
    Project: <code>{_e(ctx.project_id)}</code> &nbsp;
    Genre: {_e(genre.genre)} / {_e(genre.subgenre)} &nbsp;
    Source category: <code>{_e(genre.category_id)}</code>
  </p>
</section>"""


def _e(s: Any) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@activity.defn(name="intel_render_slide_deck")
async def render_slide_deck(inp: SlideDeckInput) -> SlideDeckResult:
    activity.heartbeat("rendering slide deck")
    if inp.config_id == "intel-presentation-v7":
        html = _render_v7_deck(inp)
    elif inp.config_id == "intel-presentation-v6":
        html = _render_v6_deck(inp)
    elif inp.config_id == "intel-presentation-v5":
        html = _render_v5_deck(inp)
    elif inp.config_id == "intel-presentation-v4":
        html = _render_v4_deck(inp)
    elif inp.config_id == "intel-presentation-v3":
        html = _render_v3_deck(inp)
    elif inp.config_id == "intel-presentation-v2":
        html = _render_v2_deck(inp)
    else:
        slides = [
            _slide_title(inp.context.name, inp.genre),
            _slide_identity(inp.context, inp.genre),
            _slide_competitors(inp.analysis),
            _slide_two_lists("Challenges", "What stands in our way", inp.analysis.challenges),
            _slide_two_lists("Opportunities", "Where the gaps are", inp.analysis.opportunities),
            _slide_positioning(inp.analysis),
            _slide_features(inp.analysis),
            _slide_storyboard("Playable Ad — Storyboard", inp.storyboards.playable_md),
            _slide_storyboard("Video Ad — Storyboard", inp.storyboards.video_md),
            _slide_summary(inp.context, inp.genre, inp.analysis),
        ]
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{_DECK_CSS}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""

    out_path = Path(inp.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    return SlideDeckResult(html_path=str(out_path), size_bytes=out_path.stat().st_size)


# ── v2 deck (16:9, palette-themed, image-heavy, executive presentation) ─────


def _luminance(hex_c: str) -> float:
    """Relative luminance for choosing readable text color over a background."""
    h = hex_c.lstrip("#")
    if len(h) != 6:
        return 0.5
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def _palette_or_default(palette: list[str]) -> dict[str, str]:
    """Map an extracted palette → a small theme dict used by the v2 CSS."""
    if not palette:
        return {
            "bg": "#0b0b10", "fg": "#f0f1f5", "muted": "#9aa0ad",
            "accent": "#ffd9a8", "card": "#15171f", "border": "#262936",
            "font": "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif",
        }
    # Sort by luminance: darkest = bg, lightest = fg, mid-saturated = accent
    sorted_by_lum = sorted(palette, key=_luminance)
    bg = sorted_by_lum[0]
    fg = sorted_by_lum[-1]
    # accent: pick a mid-luminance color from the palette that's not bg/fg
    mids = [c for c in sorted_by_lum[1:-1]] or [palette[len(palette) // 2]]
    accent = max(mids, key=lambda c: abs(_luminance(c) - 0.5))
    # card/border are bg shifted slightly lighter
    return {
        "bg": bg,
        "fg": fg,
        "muted": "#9aa0ad" if _luminance(bg) < 0.5 else "#5a5e6b",
        "accent": accent,
        "card": _shift(bg, 0.08),
        "border": _shift(bg, 0.18),
        "font": "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif",
    }


def _hex_to_rgb(hex_c: str) -> tuple[int, int, int] | None:
    h = hex_c.lstrip("#")
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _relative_luminance(hex_c: str) -> float:
    rgb = _hex_to_rgb(hex_c)
    if not rgb:
        return 0.5
    vals = []
    for channel in rgb:
        c = channel / 255
        vals.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _contrast_ratio(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    light, dark = max(la, lb), min(la, lb)
    return (light + 0.05) / (dark + 0.05)


def _best_contrast_color(bg: str, candidates: list[str], fallback: str) -> str:
    usable = [c for c in candidates if c != bg and _hex_to_rgb(c)]
    if not usable:
        return fallback
    best = max(usable, key=lambda c: _contrast_ratio(bg, c))
    return best if _contrast_ratio(bg, best) >= 4.5 else fallback


def _v7_theme(palette: list[str], context: ProjectContext) -> dict[str, str]:
    """Pick either the lightest or darkest palette color as background, then
    choose foreground/accent colors by WCAG-ish contrast instead of vibes.
    """
    if not palette:
        theme = _palette_or_default([])
    else:
        colors = [c for c in palette if _hex_to_rgb(c)]
        darkest = min(colors, key=_relative_luminance)
        lightest = max(colors, key=_relative_luminance)
        light_mode = _relative_luminance(lightest) > 0.72
        bg = lightest if light_mode else darkest
        fg_fallback = "#111827" if light_mode else "#f8fafc"
        fg = _best_contrast_color(bg, colors + [fg_fallback], fg_fallback)
        accent_fallback = "#1d4ed8" if light_mode else "#ef4444"
        accent_candidates = [
            c for c in colors
            if c not in {bg, fg} and _contrast_ratio(bg, c) >= 3.0
        ]
        accent = max(
            accent_candidates or [accent_fallback],
            key=lambda c: (_contrast_ratio(bg, c), abs(_relative_luminance(c) - 0.5)),
        )
        card = _shift(bg, -0.10 if light_mode else 0.12)
        border = _shift(bg, -0.22 if light_mode else 0.24)
        theme = {
            "bg": bg,
            "fg": fg,
            "muted": "#475569" if light_mode else "#cbd5e1",
            "accent": accent,
            "card": card,
            "border": border,
        }
    theme["font"] = _font_stack_for_context(context)
    return theme


def _font_stack_for_context(ctx: ProjectContext) -> str:
    text = " ".join([ctx.name, ctx.genre_hint or "", ctx.description or "", " ".join(ctx.asset_names)]).lower()
    if any(w in text for w in ("word", "card", "solitaire", "spell", "scrabble")):
        return "Georgia, 'Times New Roman', ui-serif, serif"
    if any(w in text for w in ("slayer", "orc", "skeleton", "dragon", "castle", "battle")):
        return "'Arial Black', Impact, system-ui, sans-serif"
    return "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif"


def _shift(hex_c: str, amount: float) -> str:
    """Lighten/darken a color toward midgray by `amount` (0..1)."""
    h = hex_c.lstrip("#")
    if len(h) != 6:
        return hex_c
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    target = 128
    r = max(0, min(255, int(r + (target - r) * amount)))
    g = max(0, min(255, int(g + (target - g) * amount)))
    b = max(0, min(255, int(b + (target - b) * amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


_V2_CSS_TPL = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: %(bg)s; --fg: %(fg)s; --muted: %(muted)s;
  --accent: %(accent)s; --card: %(card)s; --border: %(border)s;
  --font: %(font)s;
}
html, body { width: 100%%; height: 100%%; background: #000; color: var(--fg); }
body { font-family: var(--font);
       overflow: hidden; }
.deck { position: relative; width: 100vw; height: 100vh;
        display: flex; align-items: center; justify-content: center; background: #000; }
.slide { position: absolute; aspect-ratio: 16/9; width: min(100vw, calc(100vh * 16 / 9));
         max-height: 100vh; background: var(--bg); color: var(--fg);
         padding: 5.5%% 6%%; display: flex; flex-direction: column;
         opacity: 0; pointer-events: none; transition: opacity 0.18s ease;
         overflow: hidden; }
.slide.active { opacity: 1; pointer-events: auto; }
.eyebrow { font-size: 0.95vw; text-transform: uppercase; letter-spacing: 0.22em;
           color: var(--accent); font-weight: 700; margin-bottom: 1.2vw; }
h1.big { font-size: 4.2vw; line-height: 1.05; font-weight: 800; letter-spacing: -0.025em;
         color: var(--fg); }
h1.med { font-size: 3vw; line-height: 1.1; font-weight: 800; letter-spacing: -0.02em; }
h2 { font-size: 1.4vw; font-weight: 600; color: var(--muted); margin-top: 0.6vw; }
.kicker { font-size: 1.6vw; line-height: 1.4; color: var(--fg); max-width: 70%%;
          margin-top: 1.4vw; opacity: 0.92; }
.row { display: flex; gap: 2vw; align-items: stretch; }
.col { flex: 1; min-width: 0; }
.frame-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.9vw;
              margin-top: 2vw; }
.frame-grid.tall { grid-template-columns: repeat(4, 1fr); }
.frame-grid img { width: 100%%; aspect-ratio: 9/16; object-fit: cover;
                  border-radius: 0.6vw; border: 1px solid var(--border); }
.hero-frames { position: absolute; right: 5%%; top: 50%%; transform: translateY(-50%%);
               display: flex; gap: 0.9vw; }
.hero-frames img { width: 12vw; aspect-ratio: 9/16; object-fit: cover;
                   border-radius: 0.8vw; border: 1px solid var(--border);
                   box-shadow: 0 1.5vw 3vw rgba(0,0,0,0.45); }
.hero-frames img:nth-child(2) { transform: translateY(-1.4vw); }
.hero-frames img:nth-child(3) { transform: translateY(0.8vw); }
.competitor-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.2vw;
                   margin-top: 2vw; }
.competitor-card { background: var(--card); border: 1px solid var(--border);
                   border-radius: 0.8vw; padding: 1.2vw; display: flex;
                   flex-direction: column; gap: 0.8vw; }
.competitor-card img { width: 4vw; height: 4vw; border-radius: 0.6vw;
                       object-fit: cover; background: var(--border); }
.competitor-card .name { font-weight: 700; font-size: 1.1vw; line-height: 1.2; }
.competitor-card .pub { font-size: 0.85vw; color: var(--muted); }
.competitor-card .why { font-size: 0.95vw; line-height: 1.4; color: var(--fg);
                        opacity: 0.85; margin-top: 0.4vw; }
.bullets { list-style: none; margin-top: 2vw; display: flex; flex-direction: column;
           gap: 1.4vw; }
.bullets li { display: flex; align-items: flex-start; gap: 1.2vw; }
.bullets .bullet-num { flex: 0 0 3vw; height: 3vw; border-radius: 50%%;
                       background: var(--accent); color: var(--bg);
                       font-weight: 800; font-size: 1.2vw; display: flex;
                       align-items: center; justify-content: center; }
.bullets .bullet-text { font-size: 1.5vw; line-height: 1.35; flex: 1;
                        padding-top: 0.55vw; }
.feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2vw;
                margin-top: 1.6vw; }
.feature-card { background: var(--card); border: 1px solid var(--border);
                border-radius: 0.8vw; padding: 1.4vw 1.6vw; }
.feature-card .feature-title { color: var(--accent); font-size: 0.9vw;
                               text-transform: uppercase; letter-spacing: 0.18em;
                               font-weight: 700; margin-bottom: 0.6vw; }
.feature-card .feature-body { font-size: 1.05vw; line-height: 1.4; }
.quote { font-size: 2.4vw; line-height: 1.35; font-weight: 600; max-width: 88%%;
         margin-top: 2.2vw; color: var(--fg); }
.quote::before { content: ""; display: block; width: 5vw; height: 0.4vw;
                 background: var(--accent); margin-bottom: 1.6vw; border-radius: 0.2vw; }
.story-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.1vw;
             margin-top: 1.4vw; }
.story-frame { background: var(--card); border: 1px solid var(--border);
               border-radius: 0.8vw; overflow: hidden; display: flex; flex-direction: column; }
.story-frame .story-img { aspect-ratio: 9/16; background: var(--border);
                          background-size: cover; background-position: center;
                          position: relative; display: flex; align-items: flex-end; }
.story-frame .story-overlay { width: 100%%; padding: 0.8vw 1vw; background: linear-gradient(to top, rgba(0,0,0,0.85), rgba(0,0,0,0));
                              color: white; font-size: 0.95vw; font-weight: 600; line-height: 1.2; }
.story-frame .story-meta { padding: 0.9vw 1vw; }
.story-frame .story-time { color: var(--accent); font-size: 0.85vw;
                           font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
.story-frame .story-text { font-size: 0.95vw; line-height: 1.35; margin-top: 0.4vw; }
.archetype { display: inline-block; padding: 0.5vw 1.1vw; background: var(--accent);
             color: var(--bg); border-radius: 0.5vw; font-weight: 700;
             font-size: 1.1vw; margin-top: 1.2vw; }
.palette-row { display: flex; gap: 0.6vw; margin-top: 1.2vw; }
.palette-row .swatch { width: 1.8vw; height: 1.8vw; border-radius: 0.3vw;
                       border: 1px solid var(--border); }
.spacer { flex: 1; }
.foot { font-size: 0.8vw; color: var(--muted); }
.nav { position: fixed; bottom: 1.5vw; right: 2vw; display: flex; gap: 0.8vw;
       align-items: center; z-index: 10; }
.nav button { background: var(--card); color: var(--fg); border: 1px solid var(--border);
              border-radius: 0.4vw; padding: 0.5vw 0.9vw; cursor: pointer;
              font-size: 0.95vw; }
.nav .counter { font-size: 0.85vw; color: var(--muted); min-width: 4vw; text-align: center; }
.tag-row { display: flex; gap: 0.6vw; flex-wrap: wrap; margin-top: 1.6vw; }
.tag { padding: 0.5vw 1vw; background: var(--card); border: 1px solid var(--border);
       border-radius: 100vw; font-size: 1vw; color: var(--fg); }
"""


def _v2_keyframe_uri(path: str) -> str:
    return _embed_image(Path(path))


def _v2_slide_title(name: str, genre: GenreResult, frame_uris: list[str], pal: list[str]) -> str:
    hero = ""
    if frame_uris:
        hero = '<div class="hero-frames">' + "".join(
            f'<img src="{u}" alt="frame">' for u in frame_uris[:3]
        ) + "</div>"
    palette_swatches = "".join(
        f'<div class="swatch" style="background:{c}"></div>' for c in pal[:5]
    )
    return f"""<section class="slide">
  <div class="eyebrow">Market Intelligence Brief</div>
  <h1 class="big">{_e(name)}</h1>
  <p class="kicker">{_e(genre.genre)} · {_e(genre.subgenre)}</p>
  <div class="palette-row">{palette_swatches}</div>
  <div class="spacer"></div>
  <div class="foot">adforge / market_intel · presentation v2</div>
  {hero}
</section>"""


def _v2_slide_identity(ctx: ProjectContext, genre: GenreResult, frame_uris: list[str]) -> str:
    short = (ctx.description or "").strip()
    short = short.split(". ")[0] if short else ""
    short = (short[:240] + "…") if len(short) > 240 else short
    grid = ""
    if frame_uris:
        grid = '<div class="frame-grid tall">' + "".join(
            f'<img src="{u}" alt="frame">' for u in frame_uris[:4]
        ) + "</div>"
    return f"""<section class="slide">
  <div class="eyebrow">The Game</div>
  <h1 class="med">{_e(ctx.name)}</h1>
  <p class="kicker">{_e(short)}</p>
  {grid}
</section>"""


def _v2_slide_competitors(analysis: CompetitiveAnalysis) -> str:
    """Use Claude's `closest_competitors` for the why/what-to-steal,
    enriched with icons from the SensorTower genre search when names match."""
    icons_by_name: dict[str, str] = {}
    for g in analysis.genre_competitors:
        name = (g.get("name") or "").strip().lower()
        if name and g.get("icon_b64"):
            icons_by_name[name] = g["icon_b64"]

    cards = []
    for c in analysis.closest_competitors[:4]:
        name = c.get("name", "?")
        icon = icons_by_name.get(name.strip().lower())
        if not icon:
            for ic_name, ic_b64 in icons_by_name.items():
                if name.lower() in ic_name or ic_name in name.lower():
                    icon = ic_b64
                    break
        icon_html = f'<img src="{icon}" alt="">' if icon else '<img alt="" style="background:var(--border)">'
        why = (c.get("what_to_steal") or c.get("why") or "")
        why_short = why.split(".")[0] + "." if "." in why else why[:140]
        cards.append(
            f'<div class="competitor-card">{icon_html}'
            f'<div class="name">{_e(name)}</div>'
            f'<div class="why">{_e(why_short)}</div></div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1 class="med">Who we're up against</h1>
  <div class="competitor-grid">{''.join(cards)}</div>
</section>"""


def _v2_slide_bullets(eyebrow: str, title: str, items: list[str], max_items: int = 3) -> str:
    short = []
    for s in items[:max_items]:
        s = s.strip()
        first = s.split(". ")[0] if ". " in s else s
        first = first[:140] + "…" if len(first) > 140 else first
        short.append(first)
    lis = "".join(
        f'<li><div class="bullet-num">{i + 1}</div><div class="bullet-text">{_e(s)}</div></li>'
        for i, s in enumerate(short)
    )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <ul class="bullets">{lis}</ul>
</section>"""


def _v2_slide_positioning(analysis: CompetitiveAnalysis) -> str:
    quote = analysis.positioning.split(". ")[0] + "."
    return f"""<section class="slide">
  <div class="eyebrow">Recommended Positioning</div>
  <p class="quote">{_e(quote)}</p>
</section>"""


def _v2_slide_features(analysis: CompetitiveAnalysis) -> str:
    cards = []
    for f in analysis.key_features[:4]:
        title_part, _, body_part = f.partition(":")
        if not body_part:
            title_part, body_part = "Feature", f
        cards.append(
            f'<div class="feature-card">'
            f'<div class="feature-title">{_e(title_part.strip()[:48])}</div>'
            f'<div class="feature-body">{_e(body_part.strip()[:200])}</div>'
            f'</div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">Lead With</div>
  <h1 class="med">Marketing-grade features</h1>
  <div class="feature-grid">{''.join(cards)}</div>
</section>"""


def _parse_storyboard_beats(md: str) -> list[dict[str, str]]:
    """Parse markdown storyboard for beat lines like '- **0–2s (Hook):** description'.

    Returns list of {time, label, text}. Falls back to empty on parse failure.
    """
    beats: list[dict[str, str]] = []
    for raw in md.splitlines():
        line = raw.strip()
        m = re.match(r"^-\s*\*\*(.+?)\*\*[:\-—]\s*(.+)$", line)
        if not m:
            m = re.match(r"^-\s*(.+?)[:\-—]\s+(.+)$", line)
        if m:
            head, body = m.group(1).strip(), m.group(2).strip()
            time_m = re.search(r"(\d+\s*[–\-]\s*\d+\s*s|\d+\s*s|\d+\.\d+s)", head)
            time_s = time_m.group(1) if time_m else ""
            beats.append({"time": time_s, "label": head, "text": body[:200]})
        if len(beats) >= 4:
            break
    return beats


def _v2_slide_storyboard(eyebrow: str, title: str, md: str, frame_uris: list[str]) -> str:
    beats = _parse_storyboard_beats(md)
    if not beats:
        # fallback: synthesize 4 beat slots from the markdown blob
        chunks = [c for c in re.split(r"\n\s*\n", md) if c.strip()][:4]
        beats = [
            {"time": f"Beat {i + 1}", "label": f"Beat {i + 1}", "text": c.strip().replace("\n", " ")[:160]}
            for i, c in enumerate(chunks)
        ]
    frames = []
    for i, beat in enumerate(beats[:4]):
        frame_uri = frame_uris[i % len(frame_uris)] if frame_uris else ""
        bg = f'background-image: url({frame_uri});' if frame_uri else ""
        overlay = f'<div class="story-overlay">{_e(beat.get("label", ""))}</div>'
        frames.append(
            f'<div class="story-frame">'
            f'<div class="story-img" style="{bg}">{overlay}</div>'
            f'<div class="story-meta">'
            f'<div class="story-time">{_e(beat.get("time") or f"Beat {i + 1}")}</div>'
            f'<div class="story-text">{_e(beat.get("text", "")[:180])}</div>'
            f'</div></div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <div class="story-row">{''.join(frames)}</div>
</section>"""


def _render_v2_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v2: extracting palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=5)
    theme = _palette_or_default(palette)

    activity.heartbeat("v2: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v2_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v2_slide_identity(inp.context, inp.genre, frame_uris),
        _v2_slide_competitors(inp.analysis),
        _v2_slide_bullets("Challenges", "What stands in our way", inp.analysis.challenges),
        _v2_slide_bullets("Opportunities", "Where the gaps are", inp.analysis.opportunities),
        _v2_slide_positioning(inp.analysis),
        _v2_slide_features(inp.analysis),
        _v2_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_md, frame_uris),
        _v2_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_md, frame_uris),
    ]

    css = _V2_CSS_TPL % theme

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""


# ── v3 deck (16:9, palette-themed, short copy, real data, SVG storyboards) ──


def _format_count(n: int | None) -> str:
    if not n:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _v3_slide_title(name: str, genre: GenreResult, frame_uris: list[str], pal: list[str]) -> str:
    hero = ""
    if frame_uris:
        hero = '<div class="hero-frames">' + "".join(
            f'<img src="{u}" alt="frame">' for u in frame_uris[:3]
        ) + "</div>"
    palette_swatches = "".join(
        f'<div class="swatch" style="background:{c}"></div>' for c in pal[:5]
    )
    return f"""<section class="slide">
  <div class="eyebrow">Market Intelligence</div>
  <h1 class="big">{_e(name)}</h1>
  <p class="kicker">{_e(genre.genre)} · {_e(genre.subgenre)}</p>
  <div class="palette-row">{palette_swatches}</div>
  <div class="spacer"></div>
  <div class="foot">adforge / market_intel · presentation v3</div>
  {hero}
</section>"""


def _v3_slide_identity(ctx: ProjectContext, genre: GenreResult, frame_uris: list[str]) -> str:
    short = (ctx.description or "").strip()
    short = short.split(". ")[0] if short else ""
    short = (short[:240] + "…") if len(short) > 240 else short
    grid = ""
    if frame_uris:
        grid = '<div class="frame-grid tall">' + "".join(
            f'<img src="{u}" alt="frame">' for u in frame_uris[:4]
        ) + "</div>"
    return f"""<section class="slide">
  <div class="eyebrow">The Game</div>
  <h1 class="med">{_e(ctx.name)}</h1>
  <p class="kicker">{_e(short)}</p>
  {grid}
</section>"""


def _v3_slide_competitor_cards(analysis: CompetitiveAnalysis) -> str:
    icons_by_name: dict[str, str] = {}
    for g in analysis.genre_competitors:
        name = (g.get("name") or "").strip().lower()
        if name and g.get("icon_b64"):
            icons_by_name[name] = g["icon_b64"]
    cards = []
    for c in analysis.closest_competitors[:4]:
        name = c.get("name", "?")
        icon = icons_by_name.get(name.strip().lower())
        if not icon:
            for ic_name, ic_b64 in icons_by_name.items():
                if name.lower() in ic_name or ic_name in name.lower():
                    icon = ic_b64
                    break
        icon_html = f'<img src="{icon}" alt="">' if icon else '<img alt="" style="background:var(--border)">'
        why = (c.get("what_to_steal") or c.get("why") or "")
        why_short = why.split(". ")[0]
        if why_short and not why_short.endswith("."):
            why_short += "."
        cards.append(
            f'<div class="competitor-card">{icon_html}'
            f'<div class="name">{_e(name)}</div>'
            f'<div class="why">{_e(why_short)}</div></div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1 class="med">Who we're up against</h1>
  <div class="competitor-grid">{''.join(cards)}</div>
</section>"""


def _v3_slide_competitor_data(analysis: CompetitiveAnalysis) -> str:
    rows = []
    for d in analysis.competitor_data[:6]:
        icon = d.get("icon_b64")
        icon_html = f'<img src="{icon}" alt="">' if icon else '<div class="data-icon-empty"></div>'
        # SensorTower returns categories as int IDs on iOS, str slugs on Android — stringify.
        cats = ", ".join(str(c) for c in (d.get("categories") or []))[:48]
        rating = _format_count(d.get("rating_count"))
        release = (d.get("release_date") or "")[:7]
        rows.append(
            f'<div class="data-row">'
            f'<div class="data-icon">{icon_html}</div>'
            f'<div class="data-name"><div class="data-title">{_e(d.get("name", "?"))}</div>'
            f'<div class="data-pub">{_e(d.get("publisher") or "")}</div></div>'
            f'<div class="data-stat"><div class="data-num">{_e(rating)}</div>'
            f'<div class="data-lbl">ratings</div></div>'
            f'<div class="data-stat"><div class="data-num">{_e(release)}</div>'
            f'<div class="data-lbl">released</div></div>'
            f'<div class="data-cats">{_e(cats)}</div>'
            f'</div>'
        )
    if not rows:
        rows = ['<div class="data-row" style="opacity:0.6">No genre-specific competitor data available.</div>']
    return f"""<section class="slide">
  <div class="eyebrow">Competitive Landscape</div>
  <h1 class="med">By the numbers</h1>
  <div class="data-table">{''.join(rows)}</div>
  <div class="data-footnote">Genre-matched apps via SensorTower search · ratings = global cumulative review count</div>
</section>"""


def _v3_slide_bullets_short(eyebrow: str, title: str, items_short: list[str], items_long: list[str]) -> str:
    items = items_short[:3] if items_short else items_long[:3]
    lis = "".join(
        f'<li><div class="bullet-num">{i + 1}</div><div class="bullet-text">{_e(s)}</div></li>'
        for i, s in enumerate(items)
    )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <ul class="bullets">{lis}</ul>
</section>"""


def _v3_slide_positioning(analysis: CompetitiveAnalysis) -> str:
    quote = analysis.positioning_short or analysis.positioning.split(". ")[0] + "."
    return f"""<section class="slide">
  <div class="eyebrow">Recommended Positioning</div>
  <p class="quote">{_e(quote)}</p>
</section>"""


def _v3_slide_features(analysis: CompetitiveAnalysis) -> str:
    short_titles = analysis.key_features_short or []
    long_details = analysis.key_features or []
    cards = []
    for i in range(min(4, max(len(short_titles), len(long_details)))):
        title = short_titles[i] if i < len(short_titles) else f"Feature {i + 1}"
        body = long_details[i] if i < len(long_details) else ""
        body_short = body.split(". ")[0]
        if body_short and not body_short.endswith("."):
            body_short += "."
        cards.append(
            f'<div class="feature-card">'
            f'<div class="feature-title">{_e(title)}</div>'
            f'<div class="feature-body">{_e(body_short)}</div>'
            f'</div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">Lead With</div>
  <h1 class="med">Marketing-grade features</h1>
  <div class="feature-grid">{''.join(cards)}</div>
</section>"""


_SAFE_SVG_TAGS = {"rect", "circle", "ellipse", "line", "path", "polygon", "polyline", "text", "g", "tspan"}


def _sanitize_svg_inner(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if raw.startswith("<svg"):
        m = re.search(r"<svg[^>]*>(.*?)</svg>", raw, flags=re.S)
        raw = m.group(1) if m else raw
    raw = re.sub(r"<\?xml[^?]*\?>", "", raw)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)

    def repl(m: re.Match) -> str:
        tag = m.group(2).lower()
        if tag in _SAFE_SVG_TAGS:
            return m.group(0)
        return ""

    raw = re.sub(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>", repl, raw)
    return raw


def _render_storyboard_frames(visual: dict[str, Any] | None, frame_uris: list[str]) -> str:
    beats = (visual or {}).get("beats") or []
    out = []
    for i in range(4):
        beat = beats[i] if i < len(beats) else None
        if beat:
            svg_inner = _sanitize_svg_inner(beat.get("svg") or "")
            label = beat.get("label", f"Beat {i + 1}")
            time_s = beat.get("time", "")
            visual_text = beat.get("visual", "")
            on_screen = beat.get("text", "")
            audio = beat.get("audio", "")
            sketch = (
                f'<svg viewBox="0 0 200 356" class="story-svg" preserveAspectRatio="xMidYMid meet" '
                f'xmlns="http://www.w3.org/2000/svg">{svg_inner}</svg>'
            ) if svg_inner else (
                f'<div class="story-fallback" style="background-image:url({frame_uris[i % len(frame_uris)]})"></div>'
                if frame_uris else '<div class="story-fallback"></div>'
            )
            text_overlay = f'<div class="story-osd">{_e(on_screen)}</div>' if on_screen else ""
            audio_line = f'<div class="story-audio">♪ {_e(audio)}</div>' if audio else ""
            out.append(
                f'<div class="story-frame-v3">'
                f'<div class="story-canvas">{sketch}{text_overlay}</div>'
                f'<div class="story-meta">'
                f'<div class="story-tag">{_e(time_s)} · {_e(label)}</div>'
                f'<div class="story-visual">{_e(visual_text)}</div>'
                f'{audio_line}'
                f'</div></div>'
            )
        else:
            out.append('<div class="story-frame-v3"><div class="story-canvas"></div></div>')
    return "".join(out)


def _v3_slide_storyboard(eyebrow: str, title: str, visual: dict[str, Any] | None,
                         frame_uris: list[str]) -> str:
    archetype = (visual or {}).get("archetype") or ""
    concept = (visual or {}).get("concept") or ""
    cta = (visual or {}).get("cta") or ""
    archetype_pill = f'<span class="archetype">{_e(archetype)}</span>' if archetype else ""
    cta_line = f'<div class="story-cta-row">CTA: <strong>{_e(cta)}</strong></div>' if cta else ""
    frames = _render_storyboard_frames(visual, frame_uris)
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <div class="story-header">{archetype_pill}<span class="story-concept">{_e(concept)}</span></div>
  <div class="story-row-v3">{frames}</div>
  {cta_line}
</section>"""


_V3_CSS_EXTRAS = """
.data-table { display: flex; flex-direction: column; gap: 0.6vw; margin-top: 1.6vw;
              max-height: 70%; overflow: hidden; }
.data-row { display: grid; grid-template-columns: 3vw 2.4fr 1fr 1fr 2.5fr;
            align-items: center; gap: 1.2vw; padding: 0.8vw 1.2vw;
            background: var(--card); border: 1px solid var(--border);
            border-radius: 0.6vw; }
.data-icon img { width: 3vw; height: 3vw; border-radius: 0.4vw; object-fit: cover; }
.data-icon-empty { width: 3vw; height: 3vw; border-radius: 0.4vw; background: var(--border); }
.data-title { font-weight: 700; font-size: 1.05vw; line-height: 1.2; }
.data-pub { font-size: 0.8vw; color: var(--muted); margin-top: 0.2vw; }
.data-stat { text-align: right; }
.data-num { font-weight: 800; font-size: 1.1vw; color: var(--accent); }
.data-lbl { font-size: 0.7vw; text-transform: uppercase; letter-spacing: 0.12em;
            color: var(--muted); margin-top: 0.15vw; }
.data-cats { font-size: 0.85vw; color: var(--muted); text-align: right; }
.data-footnote { font-size: 0.7vw; color: var(--muted); margin-top: 1.2vw; }

.story-header { display: flex; align-items: center; gap: 1.2vw; margin-top: 0.6vw; }
.story-header .archetype { font-size: 0.95vw; padding: 0.4vw 1vw; }
.story-concept { font-size: 1.1vw; color: var(--muted); flex: 1; }
.story-row-v3 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1vw;
                margin-top: 1.2vw; }
.story-frame-v3 { background: var(--card); border: 1px solid var(--border);
                  border-radius: 0.7vw; overflow: hidden; display: flex; flex-direction: column; }
.story-canvas { aspect-ratio: 9/16; background: var(--bg); position: relative;
                display: flex; align-items: center; justify-content: center; }
.story-canvas .story-svg { width: 100%; height: 100%; display: block; }
.story-canvas .story-fallback { width: 100%; height: 100%; background-size: cover;
                                background-position: center; opacity: 0.35; }
.story-osd { position: absolute; bottom: 0.6vw; left: 0.6vw; right: 0.6vw;
             background: rgba(0,0,0,0.75); color: white; padding: 0.3vw 0.6vw;
             border-radius: 0.3vw; font-size: 0.7vw; font-weight: 600;
             text-align: center; }
.story-meta { padding: 0.7vw 0.9vw 0.9vw; }
.story-tag { color: var(--accent); font-size: 0.75vw; font-weight: 700;
             text-transform: uppercase; letter-spacing: 0.12em; }
.story-visual { font-size: 0.9vw; line-height: 1.3; margin-top: 0.4vw; color: var(--fg); }
.story-audio { font-size: 0.75vw; color: var(--muted); margin-top: 0.4vw; font-style: italic; }
.story-cta-row { margin-top: 1vw; font-size: 1.1vw; color: var(--fg); }
.story-cta-row strong { color: var(--accent); }
"""


def _render_v3_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v3: extracting palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=5)
    theme = _palette_or_default(palette)

    activity.heartbeat("v3: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v3_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v3_slide_identity(inp.context, inp.genre, frame_uris),
        _v3_slide_competitor_cards(inp.analysis),
        _v3_slide_competitor_data(inp.analysis),
        _v3_slide_bullets_short("Challenges", "What stands in our way",
                                inp.analysis.challenges_short, inp.analysis.challenges),
        _v3_slide_bullets_short("Opportunities", "Where the gaps are",
                                inp.analysis.opportunities_short, inp.analysis.opportunities),
        _v3_slide_positioning(inp.analysis),
        _v3_slide_features(inp.analysis),
        _v3_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_visual, frame_uris),
        _v3_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_visual, frame_uris),
    ]

    css = (_V2_CSS_TPL % theme) + _V3_CSS_EXTRAS

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""


# ── v4 deck (merged competitor slide + text-heavy snake storyboards, no SVGs) ──


def _v4_slide_competitors(analysis: CompetitiveAnalysis) -> str:
    """Single competitor slide that combines:
      - icon + name + publisher (from genre_competitors)
      - rating count + release year (from competitor_data)
      - takeaway (from genre_competitor_takeaways, falling back to closest_competitors)

    Renders up to 8 cards in a 2×4 grid. Replaces both v3's "who we're up against"
    and "by the numbers" slides — denser, no fake-scrollable list.
    """
    # Build app_id → takeaway map
    takeaway_by_id: dict[str, str] = {}
    takeaway_by_name: dict[str, str] = {}
    for t in analysis.genre_competitor_takeaways or []:
        if t.get("app_id"):
            takeaway_by_id[str(t["app_id"])] = (t.get("takeaway") or "").strip()
        if t.get("name"):
            takeaway_by_name[str(t["name"]).strip().lower()] = (t.get("takeaway") or "").strip()
    # Closest competitors fallback (for any matched name)
    for c in analysis.closest_competitors or []:
        nm = (c.get("name") or "").strip().lower()
        if nm and nm not in takeaway_by_name:
            takeaway_by_name[nm] = (c.get("what_to_steal") or c.get("why") or "").strip()

    # Source rows: prefer competitor_data (sorted by rating count); fall back to genre_competitors.
    rows = list(analysis.competitor_data or [])
    if not rows:
        rows = list(analysis.genre_competitors or [])

    cards: list[str] = []
    for d in rows[:8]:
        app_id = str(d.get("app_id") or "")
        name = d.get("name") or "?"
        publisher = d.get("publisher") or ""
        icon = d.get("icon_b64")
        rating = _format_count(d.get("rating_count"))
        release_year = (d.get("release_date") or "")[:4]
        takeaway = (
            takeaway_by_id.get(app_id)
            or takeaway_by_name.get(str(name).strip().lower(), "")
            or ""
        )
        # Trim takeaway to one short sentence
        if takeaway:
            takeaway = takeaway.split(". ")[0]
            if not takeaway.endswith("."):
                takeaway += "."
        icon_html = (
            f'<img src="{icon}" class="comp-icon" alt="">'
            if icon
            else '<div class="comp-icon" style="background:var(--border)"></div>'
        )
        # Stat row: only show stats we actually have
        stat_blocks = []
        if rating != "—":
            stat_blocks.append(
                f'<div class="comp-stat"><strong>{_e(rating)}</strong><span>ratings</span></div>'
            )
        if release_year:
            stat_blocks.append(
                f'<div class="comp-stat"><strong>{_e(release_year)}</strong><span>released</span></div>'
            )
        stats_html = (
            f'<div class="comp-stats">{"".join(stat_blocks)}</div>' if stat_blocks else ""
        )
        takeaway_html = (
            f'<div class="comp-takeaway">{_e(takeaway)}</div>' if takeaway else ""
        )
        cards.append(
            f'<div class="competitor-card-v4">'
            f'<div class="comp-head">{icon_html}'
            f'<div class="comp-titles">'
            f'<div class="comp-name">{_e(name)}</div>'
            f'<div class="comp-pub">{_e(publisher)}</div>'
            f'</div></div>'
            f'{stats_html}{takeaway_html}'
            f'</div>'
        )
    if not cards:
        cards = ['<div class="competitor-card-v4" style="opacity:0.6">No genre-specific competitors found.</div>']
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1 class="med">Who we're up against</h1>
  <div class="competitor-grid-v4">{''.join(cards)}</div>
  <div class="data-footnote">Genre-matched apps via SensorTower search · ratings = global cumulative review count</div>
</section>"""


def _v4_render_beat_card(i: int, beat: dict[str, Any]) -> str:
    label = beat.get("label", f"Beat {i + 1}")
    time_s = beat.get("time", "")
    visual = beat.get("visual", "")
    on_screen = beat.get("text", "")
    audio = beat.get("audio", "")
    why = beat.get("why", "")
    osd = (
        f'<div class="beat-osd">"{_e(on_screen)}"</div>'
        if on_screen and on_screen.strip() not in ("", "(none)")
        else '<div class="beat-osd beat-osd-empty">no overlay</div>'
    )
    audio_html = (
        f'<div class="beat-audio">♪ {_e(audio)}</div>' if audio else ""
    )
    why_html = (
        f'<div class="beat-why">{_e(why)}</div>' if why else ""
    )
    return f"""<div class="beat-card">
  <div class="beat-head">
    <div class="beat-num">{i + 1}</div>
    <div class="beat-titles">
      <div class="beat-time">{_e(time_s)}</div>
      <div class="beat-label">{_e(label)}</div>
    </div>
  </div>
  <div class="beat-visual">{_e(visual)}</div>
  {osd}
  {audio_html}
  {why_html}
</div>"""


def _v4_slide_storyboard(eyebrow: str, title: str, visual: dict[str, Any] | None) -> str:
    archetype = (visual or {}).get("archetype") or ""
    concept = (visual or {}).get("concept") or ""
    cta = (visual or {}).get("cta") or ""
    beats = (visual or {}).get("beats") or []
    if not beats:
        body = '<div class="story-empty">Storyboard generation failed — check the worker log.</div>'
    else:
        cards: list[str] = []
        for i, beat in enumerate(beats[:5]):
            cards.append(_v4_render_beat_card(i, beat))
            if i < min(len(beats), 5) - 1:
                cards.append('<div class="beat-arrow">→</div>')
        body = f'<div class="story-snake">{"".join(cards)}</div>'

    archetype_pill = (
        f'<span class="archetype">{_e(archetype)}</span>' if archetype else ""
    )
    concept_html = (
        f'<span class="story-concept">{_e(concept)}</span>' if concept else ""
    )
    cta_line = (
        f'<div class="story-cta-row">CTA: <strong>{_e(cta)}</strong></div>' if cta else ""
    )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <div class="story-header">{archetype_pill}{concept_html}</div>
  {body}
  {cta_line}
</section>"""


_V4_CSS_EXTRAS = """
/* v4: merged competitor cards + text-heavy snake storyboards, no SVG */

.competitor-grid-v4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1vw;
                      margin-top: 1.4vw; }
.competitor-card-v4 { background: var(--card); border: 1px solid var(--border);
                      border-radius: 0.7vw; padding: 1vw 1.1vw; display: flex;
                      flex-direction: column; gap: 0.7vw; min-height: 0; }
.comp-head { display: flex; gap: 0.8vw; align-items: center; }
.comp-icon { width: 2.6vw; height: 2.6vw; border-radius: 0.4vw; object-fit: cover; flex-shrink: 0; }
.comp-titles { min-width: 0; }
.comp-name { font-weight: 700; font-size: 0.95vw; line-height: 1.15;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.comp-pub { font-size: 0.7vw; color: var(--muted); margin-top: 0.15vw;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.comp-stats { display: flex; gap: 1.2vw; padding: 0.4vw 0; border-top: 1px solid var(--border);
              border-bottom: 1px solid var(--border); }
.comp-stat strong { color: var(--accent); font-size: 1vw; line-height: 1; display: block; }
.comp-stat span { font-size: 0.6vw; color: var(--muted); text-transform: uppercase;
                  letter-spacing: 0.12em; margin-top: 0.2vw; display: block; }
.comp-takeaway { font-size: 0.78vw; line-height: 1.4; color: var(--fg); flex: 1; }

/* snake storyboard */
.story-snake { display: grid; align-items: stretch; gap: 0.5vw; margin-top: 1.2vw;
               grid-template-columns: repeat(9, auto); /* 5 cards + 4 arrows */ }
.story-snake.four { grid-template-columns: repeat(7, auto); /* 4 cards + 3 arrows */ }
.beat-card { background: var(--card); border: 1px solid var(--border); border-radius: 0.6vw;
             padding: 0.9vw 1vw; display: flex; flex-direction: column; gap: 0.55vw;
             min-width: 0; flex: 1; }
.beat-head { display: flex; gap: 0.7vw; align-items: center; }
.beat-num { width: 1.8vw; height: 1.8vw; border-radius: 50%; background: var(--accent);
            color: var(--bg); display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 0.95vw; flex-shrink: 0; }
.beat-titles { min-width: 0; }
.beat-time { font-size: 0.65vw; color: var(--accent); text-transform: uppercase;
             letter-spacing: 0.14em; font-weight: 700; }
.beat-label { font-size: 1vw; font-weight: 800; color: var(--fg); line-height: 1.1; }
.beat-visual { font-size: 0.78vw; line-height: 1.4; color: var(--fg); }
.beat-osd { background: rgba(255,255,255,0.06); border-left: 0.18vw solid var(--accent);
            padding: 0.4vw 0.7vw; font-size: 0.72vw; color: var(--fg); border-radius: 0.25vw;
            font-weight: 600; }
.beat-osd-empty { font-style: italic; opacity: 0.5; font-weight: 400;
                  border-left-color: var(--border); }
.beat-audio { font-size: 0.7vw; color: var(--muted); font-style: italic; }
.beat-why { font-size: 0.7vw; color: var(--muted); border-top: 1px solid var(--border);
            padding-top: 0.45vw; line-height: 1.35; }
.beat-arrow { display: flex; align-items: center; justify-content: center; color: var(--accent);
              font-size: 1.2vw; padding: 0 0.2vw; }
.story-empty { padding: 2vw; text-align: center; color: var(--muted); font-size: 1vw; }
"""


def _render_v4_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v4: extracting palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=5)
    theme = _palette_or_default(palette)

    activity.heartbeat("v4: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v3_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v3_slide_identity(inp.context, inp.genre, frame_uris),
        _v4_slide_competitors(inp.analysis),
        _v3_slide_bullets_short(
            "Challenges", "What stands in our way",
            inp.analysis.challenges_short, inp.analysis.challenges,
        ),
        _v3_slide_bullets_short(
            "Opportunities", "Where the gaps are",
            inp.analysis.opportunities_short, inp.analysis.opportunities,
        ),
        _v3_slide_positioning(inp.analysis),
        _v3_slide_features(inp.analysis),
        _v4_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_visual),
        _v4_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_visual),
    ]

    css = (_V2_CSS_TPL % theme) + _V3_CSS_EXTRAS + _V4_CSS_EXTRAS

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""


# ── v5 deck (denser competitor grid w/ scale + share-of-voice, snake storyboards) ──


def _format_pct(p: float | None) -> str:
    if p is None:
        return ""
    if p > 1:
        return f"{p:.1f}%"
    if p >= 0.01:
        return f"{p * 100:.1f}%"
    return f"{p * 100:.2f}%"


def _v5_slide_competitors(analysis: CompetitiveAnalysis) -> str:
    """v5 competitor slide: up to 12 cards in a 3-row × 4-col grid, each with
    scale tier badge (proxy for users), rating count, release year, and
    Share-of-Voice if the genre app appears in the broad-category top advertisers.
    Replaces v4's 2×4 grid — denser, with one extra public spend signal.
    """
    takeaway_by_id: dict[str, str] = {}
    takeaway_by_name: dict[str, str] = {}
    for t in analysis.genre_competitor_takeaways or []:
        if t.get("app_id"):
            takeaway_by_id[str(t["app_id"])] = (t.get("takeaway") or "").strip()
        if t.get("name"):
            takeaway_by_name[str(t["name"]).strip().lower()] = (t.get("takeaway") or "").strip()
    for c in analysis.closest_competitors or []:
        nm = (c.get("name") or "").strip().lower()
        if nm and nm not in takeaway_by_name:
            takeaway_by_name[nm] = (c.get("what_to_steal") or c.get("why") or "").strip()

    rows = list(analysis.competitor_data or [])
    if not rows:
        rows = list(analysis.genre_competitors or [])

    cards: list[str] = []
    for d in rows[:12]:
        app_id = str(d.get("app_id") or "")
        name = d.get("name") or "?"
        publisher = d.get("publisher") or ""
        icon = d.get("icon_b64")
        rating = _format_count(d.get("rating_count"))
        release_year = (d.get("release_date") or "")[:4]
        scale = d.get("scale_tier") or _scale_tier(int(d.get("rating_count") or 0))
        sov = d.get("share_of_voice")
        sov_str = _format_pct(sov) if isinstance(sov, (int, float)) else ""
        takeaway = (
            takeaway_by_id.get(app_id)
            or takeaway_by_name.get(str(name).strip().lower(), "")
            or ""
        )
        if takeaway:
            takeaway = takeaway.split(". ")[0]
            if not takeaway.endswith("."):
                takeaway += "."
        icon_html = (
            f'<img src="{icon}" class="comp-icon" alt="">'
            if icon
            else '<div class="comp-icon" style="background:var(--border)"></div>'
        )
        scale_class = "scale-mega" if scale == "Mega Hit" else (
            "scale-hit" if scale == "Hit" else (
                "scale-solid" if scale == "Solid" else "scale-niche"
            )
        )
        scale_pill = f'<span class="scale-pill {scale_class}">{_e(scale)}</span>'
        stat_blocks = [
            f'<div class="comp-stat"><strong>{_e(rating)}</strong><span>ratings</span></div>',
        ]
        if release_year:
            stat_blocks.append(
                f'<div class="comp-stat"><strong>{_e(release_year)}</strong><span>since</span></div>'
            )
        if sov_str:
            stat_blocks.append(
                f'<div class="comp-stat sov"><strong>{_e(sov_str)}</strong><span>share of voice</span></div>'
            )
        stats_html = f'<div class="comp-stats">{"".join(stat_blocks)}</div>'
        takeaway_html = (
            f'<div class="comp-takeaway">{_e(takeaway)}</div>' if takeaway else ""
        )
        cards.append(
            f'<div class="competitor-card-v5">'
            f'<div class="comp-head">{icon_html}'
            f'<div class="comp-titles">'
            f'<div class="comp-name-row"><div class="comp-name">{_e(name)}</div>{scale_pill}</div>'
            f'<div class="comp-pub">{_e(publisher)}</div>'
            f'</div></div>'
            f'{stats_html}{takeaway_html}'
            f'</div>'
        )
    if not cards:
        cards = ['<div class="competitor-card-v5" style="opacity:0.6">No genre-specific competitors found.</div>']
    sov_present = any(
        isinstance(d.get("share_of_voice"), (int, float)) for d in rows[:12]
    )
    sov_note = (
        " · share of voice = % of impressions in this category from SensorTower top advertisers"
        if sov_present else ""
    )
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1 class="med">Who we're up against</h1>
  <div class="competitor-grid-v5">{''.join(cards)}</div>
  <div class="data-footnote">Genre-matched apps via SensorTower search · scale tier from global cumulative ratings (proxy for user base){sov_note}</div>
</section>"""


_V5_CSS_EXTRAS = """
/* v5: denser competitor grid w/ scale tier + share-of-voice */
.competitor-grid-v5 { display: grid; grid-template-columns: repeat(4, 1fr);
                      grid-auto-rows: 1fr; gap: 0.7vw; margin-top: 1.2vw; }
.competitor-card-v5 { background: var(--card); border: 1px solid var(--border);
                      border-radius: 0.6vw; padding: 0.75vw 0.85vw; display: flex;
                      flex-direction: column; gap: 0.5vw; min-height: 0; }
.competitor-card-v5 .comp-head { display: flex; gap: 0.6vw; align-items: center; }
.competitor-card-v5 .comp-icon { width: 2.2vw; height: 2.2vw; border-radius: 0.35vw;
                                 object-fit: cover; flex-shrink: 0; }
.competitor-card-v5 .comp-titles { min-width: 0; flex: 1; }
.comp-name-row { display: flex; gap: 0.4vw; align-items: center; min-width: 0; }
.competitor-card-v5 .comp-name { font-weight: 700; font-size: 0.85vw; line-height: 1.15;
                                 white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                                 flex: 1; min-width: 0; }
.scale-pill { font-size: 0.55vw; padding: 0.18vw 0.45vw; border-radius: 100vw;
              text-transform: uppercase; letter-spacing: 0.1em; font-weight: 800;
              flex-shrink: 0; line-height: 1; }
.scale-mega { background: var(--accent); color: var(--bg); }
.scale-hit { background: rgba(255,255,255,0.16); color: var(--accent);
             border: 1px solid var(--accent); }
.scale-solid { background: var(--border); color: var(--fg); }
.scale-niche { background: transparent; color: var(--muted);
               border: 1px solid var(--border); }
.competitor-card-v5 .comp-pub { font-size: 0.62vw; color: var(--muted); margin-top: 0.15vw;
                                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.competitor-card-v5 .comp-stats { display: flex; gap: 0.7vw; padding: 0.35vw 0;
                                  border-top: 1px solid var(--border);
                                  border-bottom: 1px solid var(--border); }
.competitor-card-v5 .comp-stat strong { color: var(--accent); font-size: 0.85vw;
                                        line-height: 1; display: block; }
.competitor-card-v5 .comp-stat span { font-size: 0.5vw; color: var(--muted);
                                       text-transform: uppercase; letter-spacing: 0.1em;
                                       margin-top: 0.18vw; display: block; }
.comp-stat.sov strong { color: var(--fg); }
.competitor-card-v5 .comp-takeaway { font-size: 0.7vw; line-height: 1.35;
                                     color: var(--fg); flex: 1; }
"""


def _render_v5_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v5: extracting palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=5)
    theme = _palette_or_default(palette)

    activity.heartbeat("v5: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v3_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v3_slide_identity(inp.context, inp.genre, frame_uris),
        _v5_slide_competitors(inp.analysis),
        _v3_slide_bullets_short(
            "Challenges", "What stands in our way",
            inp.analysis.challenges_short, inp.analysis.challenges,
        ),
        _v3_slide_bullets_short(
            "Opportunities", "Where the gaps are",
            inp.analysis.opportunities_short, inp.analysis.opportunities,
        ),
        _v3_slide_positioning(inp.analysis),
        _v3_slide_features(inp.analysis),
        _v4_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_visual),
        _v4_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_visual),
    ]

    css = (_V2_CSS_TPL % theme) + _V3_CSS_EXTRAS + _V4_CSS_EXTRAS + _V5_CSS_EXTRAS

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""


# ── v6 deck (ad-active Solid+ competitors + tactical slides 4-6) ─────────────


def _v6_competitor_rows(analysis: CompetitiveAnalysis) -> list[dict[str, Any]]:
    rows = list(analysis.competitor_data or analysis.genre_competitors or [])
    for d in rows:
        if not d.get("scale_tier"):
            d["scale_tier"] = _scale_tier(int(d.get("rating_count") or 0))
    priority = {"Mega Hit": 0, "Hit": 1, "Solid": 2, "Niche": 3, "Long Tail": 4}
    filtered = [d for d in rows if d.get("scale_tier") != "Long Tail"]
    if not filtered:
        filtered = rows
    filtered.sort(
        key=lambda d: (
            0 if (d.get("ad_activity") or {}).get("active") else 1,
            priority.get(d.get("scale_tier"), 9),
            -(int(d.get("rating_count") or 0)),
        )
    )
    return filtered[:8]


def _v6_slide_competitors(analysis: CompetitiveAnalysis) -> str:
    rows = _v6_competitor_rows(analysis)
    takeaway_by_id = {
        str(t.get("app_id")): (t.get("takeaway") or "").strip()
        for t in analysis.genre_competitor_takeaways or []
        if t.get("app_id")
    }
    cards: list[str] = []
    for d in rows:
        icon = d.get("icon_b64")
        icon_html = f'<img src="{icon}" class="comp-icon" alt="">' if icon else '<div class="comp-icon" style="background:var(--border)"></div>'
        scale = d.get("scale_tier") or _scale_tier(int(d.get("rating_count") or 0))
        scale_class = "scale-mega" if scale == "Mega Hit" else (
            "scale-hit" if scale == "Hit" else ("scale-solid" if scale == "Solid" else "scale-niche")
        )
        ad = d.get("ad_activity") or {}
        creative_count = ad.get("creative_count")
        networks = ", ".join(ad.get("networks") or [])
        examples = d.get("creative_examples") or []
        ad_line = (
            f'{_e(_format_count(creative_count))} recent creatives'
            if isinstance(creative_count, int) and creative_count > 0 else "No recent creative pull"
        )
        if networks:
            ad_line += f" · {_e(networks)}"
        takeaway = takeaway_by_id.get(str(d.get("app_id") or ""), "")
        example_html = f'<div class="ad-example">“{_e(examples[0])}”</div>' if examples else ""
        cards.append(
            f'<div class="competitor-card-v6">'
            f'<div class="comp-head">{icon_html}<div class="comp-titles">'
            f'<div class="comp-name-row"><div class="comp-name">{_e(d.get("name") or "?")}</div>'
            f'<span class="scale-pill {scale_class}">{_e(scale)}</span></div>'
            f'<div class="comp-pub">{_e(d.get("publisher") or "")}</div></div></div>'
            f'<div class="comp-stats">'
            f'<div class="comp-stat"><strong>{_e(_format_count(d.get("rating_count")))}</strong><span>ratings</span></div>'
            f'<div class="comp-stat"><strong>{_e(ad_line)}</strong><span>ad activity</span></div>'
            f'</div>'
            f'<div class="comp-takeaway">{_e(takeaway or "Study the ad promise, not just the product scale.")}</div>'
            f'{example_html}'
            f'</div>'
        )
    if not cards:
        cards = ['<div class="competitor-card-v6" style="opacity:0.6">No Solid+ genre competitors found.</div>']
    return f"""<section class="slide">
  <div class="eyebrow">Closest Competitors</div>
  <h1 class="med">Who is worth studying?</h1>
  <div class="competitor-grid-v6">{''.join(cards)}</div>
  <div class="data-footnote">Filtered to non-Long-Tail genre/subgenre matches · ratings indicate scale · ad activity comes from recent SensorTower creative pulls when available</div>
</section>"""


def _split_action(text: str) -> tuple[str, str]:
    parts = re.split(r"\bAction path:\s*", text, maxsplit=1, flags=re.I)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    sentences = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    if len(sentences) == 2:
        return sentences[0].strip(), sentences[1].strip()
    return text.strip(), ""


def _v6_slide_tactical(eyebrow: str, title: str, titles: list[str], bodies: list[str]) -> str:
    cards: list[str] = []
    for i, body in enumerate(bodies[:3]):
        head = titles[i] if i < len(titles) else f"Point {i + 1}"
        context, action = _split_action(body)
        action_html = f'<div class="action-path"><strong>Action path:</strong> {_e(action)}</div>' if action else ""
        cards.append(
            f'<div class="tactical-card">'
            f'<div class="tactical-num">{i + 1}</div>'
            f'<h2>{_e(head)}</h2>'
            f'<p>{_e(context)}</p>'
            f'{action_html}'
            f'</div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <div class="tactical-grid">{''.join(cards)}</div>
</section>"""


def _v6_slide_positioning(analysis: CompetitiveAnalysis) -> str:
    lead = analysis.positioning_short or "Own the most visual advertising promise."
    body = analysis.positioning or lead
    features = analysis.key_features_short or analysis.key_features or []
    proof = "".join(f"<li>{_e(f)}</li>" for f in features[:4])
    return f"""<section class="slide">
  <div class="eyebrow">Recommended Positioning</div>
  <h1 class="med">The ad promise to own</h1>
  <div class="positioning-v6">
    <p class="quote">{_e(lead)}</p>
    <p class="positioning-body">{_e(body)}</p>
    <div class="proof-box"><h2>Proof to put in the first 3 seconds</h2><ul>{proof}</ul></div>
  </div>
</section>"""


_V6_CSS_EXTRAS = """
/* v6: fewer, deeper competitor cards and tactical action-path slides */
.competitor-grid-v6 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8vw; margin-top: 1vw; }
.competitor-card-v6 { background: var(--card); border: 1px solid var(--border);
                      border-radius: 0.7vw; padding: 0.85vw; display: flex;
                      flex-direction: column; gap: 0.55vw; min-height: 12.5vw; }
.competitor-card-v6 .comp-stat { min-width: 0; }
.competitor-card-v6 .comp-stat strong { font-size: 0.78vw; color: var(--accent); display: block; line-height: 1.15; }
.competitor-card-v6 .comp-stat span { font-size: 0.5vw; color: var(--muted);
                                      text-transform: uppercase; letter-spacing: 0.1em; }
.ad-example { font-size: 0.64vw; line-height: 1.3; color: var(--muted);
              border-left: 2px solid var(--accent); padding-left: 0.5vw; }
.tactical-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1vw; margin-top: 1.3vw; }
.tactical-card { background: var(--card); border: 1px solid var(--border); border-radius: 0.9vw;
                 padding: 1.25vw; min-height: 24vw; display: flex; flex-direction: column; gap: 0.8vw; }
.tactical-num { width: 2vw; height: 2vw; border-radius: 50%; background: var(--accent);
                color: var(--bg); display: flex; align-items: center; justify-content: center;
                font-weight: 900; }
.tactical-card h2 { font-size: 1.25vw; line-height: 1.15; margin: 0; color: var(--fg); }
.tactical-card p { font-size: 0.95vw; line-height: 1.45; margin: 0; color: var(--fg); }
.action-path { margin-top: auto; padding-top: 0.8vw; border-top: 1px solid var(--border);
               font-size: 0.88vw; line-height: 1.4; color: var(--fg); }
.positioning-v6 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 1.4vw; align-items: start; }
.positioning-v6 .quote { grid-column: 1 / -1; font-size: 2.2vw; line-height: 1.12; margin: 0; }
.positioning-body { font-size: 1.05vw; line-height: 1.5; margin: 0; color: var(--fg); }
.proof-box { background: var(--card); border: 1px solid var(--border); border-radius: 0.8vw; padding: 1vw; }
.proof-box h2 { margin: 0 0 0.7vw; font-size: 1vw; color: var(--accent); }
.proof-box li { font-size: 0.9vw; line-height: 1.35; margin-bottom: 0.45vw; }
"""


def _render_v6_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v6: extracting palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=5)
    theme = _palette_or_default(palette)

    activity.heartbeat("v6: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v3_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v3_slide_identity(inp.context, inp.genre, frame_uris),
        _v6_slide_competitors(inp.analysis),
        _v6_slide_tactical(
            "Challenges", "What stands in our way",
            inp.analysis.challenges_short, inp.analysis.challenges,
        ),
        _v6_slide_tactical(
            "Opportunities", "Where we can stand out",
            inp.analysis.opportunities_short, inp.analysis.opportunities,
        ),
        _v6_slide_positioning(inp.analysis),
        _v3_slide_features(inp.analysis),
        _v4_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_visual),
        _v4_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_visual),
    ]

    css = (_V2_CSS_TPL % theme) + _V3_CSS_EXTRAS + _V4_CSS_EXTRAS + _V5_CSS_EXTRAS + _V6_CSS_EXTRAS

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""


# ── v7 deck (creative-led competitors + contrast-safe theme) ─────────────────


def _v7_slide_creative_competitors(analysis: CompetitiveAnalysis) -> str:
    rows = list(analysis.competitor_data or [])
    for d in rows:
        if not d.get("scale_tier"):
            d["scale_tier"] = _scale_tier(int(d.get("rating_count") or 0))

    def score(d: dict[str, Any]) -> tuple[int, float, int]:
        ad = d.get("ad_activity") or {}
        creative_count = int(ad.get("creative_count") or 0)
        sov = float(d.get("share_of_voice") or 0)
        ratings = int(d.get("rating_count") or 0)
        return creative_count, sov, ratings

    ranked = sorted(rows, key=score, reverse=True)
    ranked = [d for d in ranked if score(d)[0] or score(d)[1]][:8] or ranked[:8]

    cards: list[str] = []
    for d in ranked:
        icon = d.get("icon_b64")
        icon_html = f'<img src="{icon}" class="comp-icon" alt="">' if icon else '<div class="comp-icon" style="background:var(--border)"></div>'
        ad = d.get("ad_activity") or {}
        creative_count = int(ad.get("creative_count") or 0)
        networks = ", ".join(ad.get("networks") or [])
        sov = d.get("share_of_voice")
        sov_html = _format_pct(float(sov)) if isinstance(sov, (int, float)) else "—"
        examples = d.get("creative_examples") or []
        msg = examples[0] if examples else "No sample creative message available."
        trend = "Active ad buyer" if creative_count else "Scale comp; monitor creatives"
        scale = d.get("scale_tier") or _scale_tier(int(d.get("rating_count") or 0))
        cards.append(
            f'<div class="creative-comp-card">'
            f'<div class="comp-head">{icon_html}<div class="comp-titles">'
            f'<div class="comp-name">{_e(d.get("name") or "?")}</div>'
            f'<div class="comp-pub">{_e(d.get("publisher") or "")}</div></div></div>'
            f'<div class="creative-metrics">'
            f'<div><strong>{_e(_format_count(creative_count))}</strong><span>recent creatives</span></div>'
            f'<div><strong>{_e(sov_html)}</strong><span>share signal</span></div>'
            f'<div><strong>{_e(scale)}</strong><span>scale</span></div>'
            f'</div>'
            f'<div class="creative-trend">{_e(trend)}{(" · " + _e(networks)) if networks else ""}</div>'
            f'<div class="creative-msg">“{_e(msg[:150])}”</div>'
            f'</div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">Creative Competition</div>
  <h1 class="med">Who is buying attention?</h1>
  <div class="creative-comp-grid">{''.join(cards)}</div>
  <div class="data-footnote">Ranked by recent SensorTower creative activity first, then share signal and scale. Ratings are context, not the deciding lens.</div>
</section>"""


def _v7_slide_tactical(eyebrow: str, title: str, titles: list[str], bodies: list[str]) -> str:
    cards: list[str] = []
    for i, body in enumerate(bodies[:3]):
        head = titles[i] if i < len(titles) else f"Point {i + 1}"
        context, action = _split_action(body)
        cards.append(
            f'<div class="tactical-card v7">'
            f'<div class="tactical-num">{i + 1}</div>'
            f'<h2>{_e(head)}</h2>'
            f'<p>{_e(context)}</p>'
            f'<div class="action-path"><strong>Action path:</strong> {_e(action or "Choose one concrete test before scaling spend.")}</div>'
            f'</div>'
        )
    return f"""<section class="slide">
  <div class="eyebrow">{_e(eyebrow)}</div>
  <h1 class="med">{_e(title)}</h1>
  <div class="tactical-grid">{''.join(cards)}</div>
  <div class="data-footnote">Challenges are blockers. Opportunities are distinct wedges or advantages, not the same fact reframed positively.</div>
</section>"""


_V7_CSS_EXTRAS = """
/* v7: contrast-safe and creative-led */
.creative-comp-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8vw; margin-top: 1vw; }
.creative-comp-card { background: var(--card); border: 1px solid var(--border);
                      border-radius: 0.75vw; padding: 0.85vw; display: flex;
                      flex-direction: column; gap: 0.6vw; min-height: 13.5vw; }
.creative-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.45vw;
                    border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
                    padding: 0.45vw 0; }
.creative-metrics strong { display: block; color: var(--accent); font-size: 0.82vw; line-height: 1.1; }
.creative-metrics span { display: block; color: var(--muted); font-size: 0.48vw;
                         text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.18vw; }
.creative-trend { font-size: 0.68vw; line-height: 1.25; color: var(--fg); font-weight: 700; }
.creative-msg { font-size: 0.66vw; line-height: 1.32; color: var(--fg);
                border-left: 0.18vw solid var(--accent); padding-left: 0.55vw; opacity: 0.92; }
.tactical-card.v7 p { font-size: 0.92vw; }
.data-footnote { color: var(--muted); font-size: 0.7vw; margin-top: 0.7vw; }
"""


def _render_v7_deck(inp: SlideDeckInput) -> str:
    activity.heartbeat("v7: extracting contrast-safe palette")
    palette = _extract_palette(inp.context.frame_paths, n_colors=6)
    theme = _v7_theme(palette, inp.context)

    activity.heartbeat("v7: embedding frames")
    frame_uris = [_v2_keyframe_uri(p) for p in inp.context.frame_paths]

    slides = [
        _v3_slide_title(inp.context.name, inp.genre, frame_uris, palette),
        _v3_slide_identity(inp.context, inp.genre, frame_uris),
        _v7_slide_creative_competitors(inp.analysis),
        _v7_slide_tactical(
            "Challenges", "What blocks adoption?",
            inp.analysis.challenges_short, inp.analysis.challenges,
        ),
        _v7_slide_tactical(
            "Opportunities", "What can we uniquely exploit?",
            inp.analysis.opportunities_short, inp.analysis.opportunities,
        ),
        _v6_slide_positioning(inp.analysis),
        _v3_slide_features(inp.analysis),
        _v4_slide_storyboard("Playable Ad", "Storyboard", inp.storyboards.playable_visual),
        _v4_slide_storyboard("Video Ad", "Storyboard", inp.storyboards.video_visual),
    ]

    css = (_V2_CSS_TPL % theme) + _V3_CSS_EXTRAS + _V4_CSS_EXTRAS + _V5_CSS_EXTRAS + _V6_CSS_EXTRAS + _V7_CSS_EXTRAS

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Market Intelligence — {_e(inp.context.name)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">
    {''.join(slides)}
    <nav class="nav">
      <button onclick="show(i-1)">←</button>
      <span class="counter" id="counter"></span>
      <button onclick="show(i+1)">→</button>
    </nav>
  </main>
  <script>{_DECK_JS}</script>
</body>
</html>"""
