"""adforge CLI — the surface for humans.

Three groups, mirroring the architecture:

  adforge worker                    long-lived Temporal worker (hosts activities + workflows)
  adforge run    <pipeline> ...     start a workflow against a target
  adforge tools  <helper>  ...      standalone helpers (no Temporal, no worker)

A run takes a `--target <id>`, where `<id>` is a folder under `targets/`.
The CLI resolves `targets/<id>/` into a Target object (video + assets + metadata)
and hands the workflow already-resolved paths plus a fresh `run_id`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from adforge import targets as targets_mod
from adforge import worker as worker_mod
from adforge.activities.types import VariationSpec
from adforge.config import RUNS_DIR, settings
from adforge.runs import ensure_run_dir, list_runs, make_run_id

app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")
run = typer.Typer(no_args_is_help=True, help="Launch Temporal workflows against a target.")
tools = typer.Typer(no_args_is_help=True, help="Standalone helpers (no Temporal needed).")
app.add_typer(run, name="run")
app.add_typer(tools, name="tools")


# ───── worker ───────────────────────────────────────────────────────────


@app.command()
def worker() -> None:
    """Run the Temporal worker (long-lived process)."""
    worker_mod.main()


@app.command()
def api(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code change (dev)"),
) -> None:
    """Run the FastAPI shim that powers the ui/ viewer."""
    import uvicorn

    uvicorn.run("adforge.api:app", host=host, port=port, reload=reload)


# ───── workflow launchers ────────────────────────────────────────────────


async def _start_workflow(workflow_name: str, arg, workflow_id: str) -> None:
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


def _resolve_target(target_id: str) -> targets_mod.Target:
    try:
        return targets_mod.load(target_id)
    except FileNotFoundError as e:
        rprint(f"[red]error:[/red] {e}")
        raise typer.Exit(code=2)


@run.command("playable")
def run_playable(
    target: str = typer.Option(..., "--target", help="Target id (folder under targets/)"),
    variants: int = typer.Option(4, "--variants", help="How many baseline variants to emit"),
) -> None:
    """video + assets → playable HTML + variants."""
    from adforge.pipelines.playable_forge import PlayableForgeInput

    t = _resolve_target(target)
    if not t.has_video():
        rprint(f"[red]error:[/red] target '{t.id}' has no video.mp4 — playable_forge needs one.")
        raise typer.Exit(code=2)

    rid = make_run_id("playable", t.id)
    run_dir = str(ensure_run_dir(rid))

    default_variants = [
        VariationSpec(name="easy",     overrides={"enemySpeed": 60,  "winScore": 8,  "spawnEverySeconds": 1.6}),
        VariationSpec(name="hard",     overrides={"enemySpeed": 140, "winScore": 18, "spawnEverySeconds": 0.7}),
        VariationSpec(name="speedrun", overrides={"sessionSeconds": 15}),
        VariationSpec(name="neon",     overrides={"palette": ["#0b0b1a","#ff2bd6","#22e1ff","#fff700","#ff7849"]}),
    ][:variants]

    inp = PlayableForgeInput(
        target_id=t.id, run_id=rid, run_dir=run_dir,
        video_path=t.video_path, asset_dir=t.asset_dir,
        variants=default_variants,
    )
    asyncio.run(_start_workflow("playable_forge", inp, workflow_id=rid))


@run.command("creative")
def run_creative(
    target: str = typer.Option(..., "--target", help="Target id (folder under targets/)"),
    category: str = typer.Option("7012", "--category"),
    country: str = typer.Option("US", "--country"),
    network: str = typer.Option("TikTok", "--network"),
    period: str = typer.Option("month", "--period"),
    sample: int = typer.Option(30, "--sample"),
    render_http: bool = typer.Option(False, "--render-http", help="Render via Scenario HTTP API (else use the MCP)"),
) -> None:
    """target → market-informed brief + Scenario prompt."""
    from adforge.pipelines.creative_forge import CreativeForgeInput

    t = _resolve_target(target)
    rid = make_run_id("creative", t.id)
    run_dir = str(ensure_run_dir(rid))

    inp = CreativeForgeInput(
        target_id=t.id, run_id=rid, run_dir=run_dir,
        target_term=t.name,
        category=category, country=country, network=network, period=period,
        sample=sample, render_with_scenario_http=render_http,
    )
    asyncio.run(_start_workflow("creative_forge", inp, workflow_id=rid))


@run.command("full")
def run_full(
    target: str = typer.Option(..., "--target", help="Target id (folder under targets/)"),
    category: str = typer.Option("7012", "--category"),
    country: str = typer.Option("US", "--country"),
    network: str = typer.Option("TikTok", "--network"),
    period: str = typer.Option("month", "--period"),
    sample: int = typer.Option(30, "--sample"),
    render_http: bool = typer.Option(False, "--render-http"),
) -> None:
    """The merged demo: target → brief + Scenario prompt + market-informed playable + variants."""
    from adforge.pipelines.full_forge import FullForgeInput

    t = _resolve_target(target)
    if not t.has_video():
        rprint(f"[red]error:[/red] target '{t.id}' has no video.mp4 — full_forge needs one.")
        raise typer.Exit(code=2)

    rid = make_run_id("full", t.id)
    run_dir = str(ensure_run_dir(rid))

    inp = FullForgeInput(
        target_id=t.id, run_id=rid, run_dir=run_dir,
        target_term=t.name, video_path=t.video_path, asset_dir=t.asset_dir,
        category=category, country=country, network=network, period=period,
        sample=sample, render_with_scenario_http=render_http,
    )
    asyncio.run(_start_workflow("full_forge", inp, workflow_id=rid))


# ───── tools (no Temporal required) ──────────────────────────────────────


@tools.command("env")
def tools_env() -> None:
    """Print resolved settings (with secrets masked)."""
    s = settings().model_dump()
    masked = {k: ("<set>" if v else "<empty>") if "key" in k or "id" in k else v for k, v in s.items()}
    rprint(masked)


@tools.command("targets")
def tools_targets(target_id: Optional[str] = typer.Argument(None, help="If given, show details. Else list all.")) -> None:
    """List targets, or show details for one."""
    if target_id:
        t = _resolve_target(target_id)
        rprint(t.model_dump())
        return

    ids = targets_mod.list_targets()
    if not ids:
        rprint("[yellow]no targets[/yellow] — see targets/README.md to add one.")
        return
    table = Table(title="targets/")
    table.add_column("id"); table.add_column("name"); table.add_column("video"); table.add_column("assets")
    for tid in ids:
        try:
            t = targets_mod.load(tid)
            table.add_row(t.id, t.name, "✓" if t.has_video() else "—", "✓" if t.has_assets() else "—")
        except Exception as e:
            table.add_row(tid, f"[red]err: {e}[/red]", "?", "?")
    rprint(table)


@tools.command("runs")
def tools_runs(run_id: Optional[str] = typer.Argument(None, help="If given, show manifest. Else list all.")) -> None:
    """List runs, or show one run's manifest."""
    if run_id:
        manifest = RUNS_DIR / run_id / "manifest.json"
        if not manifest.is_file():
            rprint(f"[red]no manifest at {manifest}[/red]")
            raise typer.Exit(code=2)
        rprint(json.loads(manifest.read_text()))
        return

    ids = list_runs()
    if not ids:
        rprint("[yellow]no runs[/yellow]")
        return
    table = Table(title="runs/")
    table.add_column("run_id"); table.add_column("pipeline"); table.add_column("target"); table.add_column("status")
    for rid in ids:
        manifest = RUNS_DIR / rid / "manifest.json"
        if manifest.is_file():
            m = json.loads(manifest.read_text())
            table.add_row(rid, m.get("pipeline", "?"), m.get("target_id", "?"), m.get("status", "?"))
        else:
            table.add_row(rid, "?", "?", "[yellow]no manifest[/yellow]")
    rprint(table)


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
