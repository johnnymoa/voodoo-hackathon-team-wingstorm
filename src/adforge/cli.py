"""adforge CLI.

  adforge worker                                  start the Temporal worker
  adforge run playable --video <path> ...         launch the playable_forge workflow
  adforge run creative --target <game> ...        launch the creative_forge workflow
  adforge run full     --target <game> --video <path> ...   launch full_forge

Standalone helpers (no Temporal needed):
  adforge tools st-search "royal match"           SensorTower search
  adforge tools st-top-creatives --network TikTok SensorTower top creatives
  adforge tools env                               print resolved settings
  adforge tools inline <html>                     inline external assets in place
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

from adforge import worker as worker_mod
from adforge.activities.types import VariationSpec
from adforge.config import OUTPUT_DIR, ensure_dirs, settings
from adforge.utils import run_id, slug

app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")
run = typer.Typer(no_args_is_help=True, help="Launch Temporal workflows.")
tools = typer.Typer(no_args_is_help=True, help="Standalone helpers (no Temporal).")
app.add_typer(run, name="run")
app.add_typer(tools, name="tools")


# ───── worker ───────────────────────────────────────────────────────────


@app.command()
def worker() -> None:
    """Run the Temporal worker (long-lived process)."""
    worker_mod.main()


# ───── workflow launchers ────────────────────────────────────────────────


async def _start_workflow(workflow_name: str, arg, workflow_id: str):
    from temporalio.client import Client
    from temporalio.contrib.pydantic import pydantic_data_converter

    s = settings()
    client = await Client.connect(
        s.temporal_address,
        namespace=s.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
    handle = await client.start_workflow(
        workflow_name,
        arg,
        id=workflow_id,
        task_queue=s.temporal_task_queue,
    )
    rprint(f"[green]started[/green] workflow_id={workflow_id} run_id={handle.first_execution_run_id}")
    rprint(f"  → web ui: http://localhost:8233/namespaces/{s.temporal_namespace}/workflows/{workflow_id}")
    result = await handle.result()
    rprint("[bold green]done[/bold green]")
    rprint(result.model_dump() if hasattr(result, "model_dump") else result)


@run.command("playable")
def run_playable(
    video: Path = typer.Option(..., "--video", help="Path to gameplay video"),
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory"),
    asset_dir: Optional[Path] = typer.Option(None, "--assets", help="Asset folder to inline"),
    variants: int = typer.Option(4, "--variants", help="How many baseline variants to emit"),
) -> None:
    """video → playable HTML + variants."""
    from adforge.pipelines.playable_forge import PlayableForgeInput

    ensure_dirs()
    rid = run_id(prefix="playable")
    out_dir = str(out or OUTPUT_DIR / "playables" / rid)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    default_variants = [
        VariationSpec(name="easy",     overrides={"enemySpeed": 60,  "winScore": 8,  "spawnEverySeconds": 1.6}),
        VariationSpec(name="hard",     overrides={"enemySpeed": 140, "winScore": 18, "spawnEverySeconds": 0.7}),
        VariationSpec(name="speedrun", overrides={"sessionSeconds": 15}),
        VariationSpec(name="neon",     overrides={"palette": ["#0b0b1a","#ff2bd6","#22e1ff","#fff700","#ff7849"]}),
    ][:variants]

    inp = PlayableForgeInput(
        video_path=str(video),
        out_dir=out_dir,
        asset_dir=str(asset_dir) if asset_dir else None,
        variants=default_variants,
    )
    asyncio.run(_start_workflow("playable_forge", inp, workflow_id=f"playable-{rid}"))


@run.command("creative")
def run_creative(
    target: str = typer.Option(..., "--target", help='Target game name, e.g. "castle clasher"'),
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory"),
    category: str = typer.Option("7012", "--category"),
    country: str = typer.Option("US", "--country"),
    network: str = typer.Option("TikTok", "--network"),
    period: str = typer.Option("month", "--period"),
    sample: int = typer.Option(30, "--sample"),
    render_http: bool = typer.Option(False, "--render-http", help="Render via Scenario HTTP API (else use the MCP)"),
) -> None:
    """target game → market-informed brief + Scenario prompt."""
    from adforge.pipelines.creative_forge import CreativeForgeInput

    ensure_dirs()
    rid = run_id(prefix=f"creative-{slug(target)}")
    out_dir = str(out or OUTPUT_DIR / "creatives" / rid)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    inp = CreativeForgeInput(
        target_term=target, out_dir=out_dir,
        category=category, country=country, network=network, period=period,
        sample=sample, render_with_scenario_http=render_http,
    )
    asyncio.run(_start_workflow("creative_forge", inp, workflow_id=f"creative-{rid}"))


@run.command("full")
def run_full(
    target: str = typer.Option(..., "--target"),
    video: Path = typer.Option(..., "--video"),
    out: Optional[Path] = typer.Option(None, "--out"),
    asset_dir: Optional[Path] = typer.Option(None, "--assets"),
    category: str = typer.Option("7012", "--category"),
    country: str = typer.Option("US", "--country"),
    network: str = typer.Option("TikTok", "--network"),
    period: str = typer.Option("month", "--period"),
    sample: int = typer.Option(30, "--sample"),
    render_http: bool = typer.Option(False, "--render-http"),
) -> None:
    """The merged demo: target + video → brief + Scenario prompt + market-informed playable + variants."""
    from adforge.pipelines.full_forge import FullForgeInput

    ensure_dirs()
    rid = run_id(prefix=f"full-{slug(target)}")
    out_dir = str(out or OUTPUT_DIR / "full" / rid)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    inp = FullForgeInput(
        target_term=target, video_path=str(video), out_dir=out_dir,
        asset_dir=str(asset_dir) if asset_dir else None,
        category=category, country=country, network=network, period=period,
        sample=sample, render_with_scenario_http=render_http,
    )
    asyncio.run(_start_workflow("full_forge", inp, workflow_id=f"full-{rid}"))


# ───── tools (no Temporal required) ──────────────────────────────────────


@tools.command("env")
def tools_env() -> None:
    """Print resolved settings (with secrets masked)."""
    s = settings().model_dump()
    masked = {k: ("<set>" if v else "<empty>") if "key" in k or "id" in k else v for k, v in s.items()}
    rprint(masked)


@tools.command("st-search")
def tools_st_search(term: str, limit: int = 5) -> None:
    from adforge.connectors import sensortower

    out = sensortower.search_entities(term, limit=limit)
    rprint(out)


@tools.command("st-top-creatives")
def tools_st_top_creatives(
    category: str = "7012",
    country: str = "US",
    network: str = "TikTok",
    period: str = "month",
    limit: int = 50,
    save: Optional[Path] = None,
) -> None:
    from adforge.connectors import sensortower

    data = sensortower.top_creatives(
        category=category, country=country, network=network, period=period, limit=limit
    )
    if save:
        save.parent.mkdir(parents=True, exist_ok=True)
        save.write_text(json.dumps(data, indent=2))
        rprint(f"saved → {save}")
    else:
        rprint({"count": data.get("count"), "ad_units": len(data.get("ad_units", []))})


@tools.command("inline")
def tools_inline(html: Path) -> None:
    """Inline external assets in an HTML playable in place."""
    from adforge.activities.variations import _inline_one
    from adforge.utils import file_size_mb

    new = _inline_one(html.read_text(encoding="utf-8"), html.parent)
    html.write_text(new, encoding="utf-8")
    rprint(f"wrote {html} ({file_size_mb(html):.2f} MB)")


@tools.command("gemini-models")
def tools_gemini_models() -> None:
    from adforge.connectors import gemini

    for m in gemini.list_models():
        rprint(m)


if __name__ == "__main__":
    app()
