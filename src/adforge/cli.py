"""adforge CLI — the surface for humans.

  adforge worker                       long-lived Temporal worker
  adforge api                          FastAPI shim that powers the UI
  adforge run    <pipeline> ...        start a workflow against a project
  adforge tools  <helper>  ...         standalone helpers (no Temporal)

A run takes `--project <id>`, where `<id>` is a folder under `projects/`.
Optional `--config <id>` picks a named PipelineConfig preset (default: "default").
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from adforge import feedback as feedback_mod
from adforge import projects as projects_mod
from adforge import worker as worker_mod
from adforge.activities.types import VariationSpec
from adforge.config import RUNS_DIR, settings
from adforge.pipelines import PIPELINES, find_config
from adforge.runs import ensure_run_dir, list_runs, make_run_id

app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")
run = typer.Typer(no_args_is_help=True, help="Launch Temporal workflows against a project.")
tools = typer.Typer(no_args_is_help=True, help="Standalone helpers (no Temporal needed).")
feedback = typer.Typer(no_args_is_help=True, help="Read & write per-run feedback (drives the /iterate skill).")
app.add_typer(run, name="run")
app.add_typer(tools, name="tools")
app.add_typer(feedback, name="feedback")


# ───── worker / api ─────────────────────────────────────────────────────


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


def _resolve_project(project_id: str) -> projects_mod.Project:
    try:
        return projects_mod.load(project_id)
    except FileNotFoundError as e:
        rprint(f"[red]error:[/red] {e}")
        raise typer.Exit(code=2)


def _resolve_config(pipeline_id: str, config_id: str) -> str:
    """Validate the config exists for this pipeline; bail with a helpful list if not."""
    cfg = find_config(pipeline_id, config_id)
    if cfg is None:
        spec = next((p for p in PIPELINES if p.id == pipeline_id), None)
        available = ", ".join(c.id for c in (spec.configs if spec else []))
        rprint(f"[red]error:[/red] config '{config_id}' not found for {pipeline_id}. Available: {available}")
        raise typer.Exit(code=2)
    return config_id


@run.command("playable")
def run_playable(
    project: str = typer.Option(..., "--project", help="Project id (folder under projects/)"),
    config:  str = typer.Option("default", "--config", help="PipelineConfig preset id"),
    variants: int = typer.Option(4, "--variants", help="How many baseline variants to emit"),
) -> None:
    """video + assets → playable HTML + variants."""
    from adforge.pipelines.playable_forge import PlayableForgeInput

    p = _resolve_project(project)
    if not p.has_video():
        rprint(f"[red]error:[/red] project '{p.id}' has no video.mp4 — playable_forge needs one.")
        raise typer.Exit(code=2)
    cfg_id = _resolve_config("playable_forge", config)

    rid = make_run_id("playable", p.id)
    run_dir = str(ensure_run_dir(rid))

    default_variants = [
        VariationSpec(name="easy",     overrides={"enemySpeed": 60,  "winScore": 8,  "spawnEverySeconds": 1.6}),
        VariationSpec(name="hard",     overrides={"enemySpeed": 140, "winScore": 18, "spawnEverySeconds": 0.7}),
        VariationSpec(name="speedrun", overrides={"sessionSeconds": 15}),
        VariationSpec(name="neon",     overrides={"palette": ["#0b0b1a","#ff2bd6","#22e1ff","#fff700","#ff7849"]}),
    ][:variants]

    inp = PlayableForgeInput(
        project_id=p.id, run_id=rid, run_dir=run_dir, config_id=cfg_id,
        video_path=p.video_path, asset_dir=p.asset_dir,
        variants=default_variants,
    )
    asyncio.run(_start_workflow("playable_forge", inp, workflow_id=rid))


@run.command("creative")
def run_creative(
    project: str = typer.Option(..., "--project", help="Project id (folder under projects/)"),
    config:  str = typer.Option("default", "--config", help="PipelineConfig preset id"),
    category: Optional[str] = typer.Option(None, "--category", help="Override project.category_id"),
    country:  Optional[str] = typer.Option(None, "--country",  help="Override project.country"),
    network: str = typer.Option("TikTok", "--network"),
    period: str = typer.Option("month", "--period"),
    sample: int = typer.Option(30, "--sample"),
    render_http: bool = typer.Option(False, "--render-http", help="Render via Scenario HTTP API (else use the MCP)"),
) -> None:
    """project → market insights → storyboard → video ad creative."""
    from adforge.pipelines.creative_forge import CreativeForgeInput

    p = _resolve_project(project)
    cfg_id = _resolve_config("creative_forge", config)
    rid = make_run_id("creative", p.id)
    run_dir = str(ensure_run_dir(rid))

    inp = CreativeForgeInput(
        project_id=p.id, run_id=rid, run_dir=run_dir, config_id=cfg_id,
        target_term=p.name,
        category=category or p.category_id,
        country=country or p.country,
        network=network, period=period,
        sample=sample, render_with_scenario_http=render_http,
    )
    asyncio.run(_start_workflow("creative_forge", inp, workflow_id=rid))


# ───── tools (no Temporal required) ──────────────────────────────────────


@tools.command("env")
def tools_env() -> None:
    """Print resolved settings (with secrets masked)."""
    s = settings().model_dump()
    masked = {k: ("<set>" if v else "<empty>") if "key" in k or "id" in k else v for k, v in s.items()}
    rprint(masked)


@tools.command("projects")
def tools_projects(project_id: Optional[str] = typer.Argument(None, help="If given, show details. Else list all.")) -> None:
    """List projects, or show details for one."""
    if project_id:
        p = _resolve_project(project_id)
        rprint(p.model_dump())
        return

    ids = projects_mod.list_projects()
    if not ids:
        rprint("[yellow]no projects[/yellow] — see projects/README.md to add one.")
        return
    table = Table(title="projects/")
    table.add_column("id"); table.add_column("name"); table.add_column("video"); table.add_column("assets")
    for pid in ids:
        try:
            p = projects_mod.load(pid)
            table.add_row(p.id, p.name, "✓" if p.has_video() else "—", "✓" if p.has_assets() else "—")
        except Exception as e:
            table.add_row(pid, f"[red]err: {e}[/red]", "?", "?")
    rprint(table)


@tools.command("pipelines")
def tools_pipelines() -> None:
    """List pipelines + their configs."""
    table = Table(title="pipelines/")
    table.add_column("id"); table.add_column("name"); table.add_column("configs"); table.add_column("inputs"); table.add_column("outputs")
    for spec in PIPELINES:
        table.add_row(
            spec.id, spec.name,
            ", ".join(c.id for c in spec.configs),
            ", ".join(i.id for i in spec.inputs) or "—",
            ", ".join(spec.outputs) or "—",
        )
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
    table.add_column("run_id"); table.add_column("pipeline"); table.add_column("project"); table.add_column("config"); table.add_column("status")
    for rid in ids:
        manifest = RUNS_DIR / rid / "manifest.json"
        if manifest.is_file():
            m = json.loads(manifest.read_text())
            table.add_row(
                rid,
                m.get("pipeline", "?"),
                m.get("project_id", m.get("target_id", "?")),
                m.get("config_id", "?"),
                m.get("status", "?"),
            )
        else:
            table.add_row(rid, "?", "?", "?", "[yellow]no manifest[/yellow]")
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


# ───── feedback (drives the /iterate skill) ─────────────────────────────


@feedback.command("ls")
def feedback_ls(
    all_: bool = typer.Option(False, "--all", "-a", help="Include fulfilled / wontfix (default: open only)"),
) -> None:
    """List feedback files across runs."""
    status = None if all_ else feedback_mod.STATUS_OPEN
    items = feedback_mod.list_all(status=status)
    if not items:
        rprint("[yellow]no feedback found[/yellow]" + ("" if all_ else " (try --all to include closed)"))
        return
    table = Table(title="feedback", show_lines=False)
    table.add_column("status"); table.add_column("run_id"); table.add_column("updated"); table.add_column("addressed by"); table.add_column("preview")
    for fb in items:
        addressed = f"{fb.addressed_in_run or '—'} / {fb.addressed_by_config or '—'}"
        preview = (fb.body.strip().split("\n", 1)[0])[:80]
        table.add_row(fb.status, fb.run_id, fb.updated_at, addressed, preview)
    rprint(table)


@feedback.command("show")
def feedback_show(run_id: str = typer.Argument(..., help="Run id")) -> None:
    """Print one run's feedback (frontmatter + body)."""
    fb = feedback_mod.load(run_id)
    if fb is None:
        rprint(f"[yellow]no feedback at runs/{run_id}/feedback.md[/yellow]")
        raise typer.Exit(code=1)
    rprint(fb.model_dump())


@feedback.command("close")
def feedback_close(
    run_id: str = typer.Argument(..., help="Run id whose feedback you're closing"),
    by_run: str = typer.Option(..., "--by-run", help="The new run_id that addressed this feedback"),
    by_config: str = typer.Option(..., "--by-config", help="The new config_id that addressed this feedback"),
) -> None:
    """Mark feedback fulfilled and link the iteration that addressed it."""
    try:
        fb = feedback_mod.close(run_id, addressed_in_run=by_run, addressed_by_config=by_config)
    except FileNotFoundError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    rprint(f"[green]closed[/green] {run_id} → addressed in {by_run} ({by_config})")
    rprint(fb.model_dump())


@feedback.command("wontfix")
def feedback_wontfix(run_id: str = typer.Argument(..., help="Run id")) -> None:
    """Mark feedback as wontfix (we decided not to address it)."""
    try:
        fb = feedback_mod.set_status(run_id, feedback_mod.STATUS_WONTFIX)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    rprint(f"[yellow]wontfix[/yellow] {run_id}")
    rprint(fb.model_dump())


@feedback.command("reopen")
def feedback_reopen(run_id: str = typer.Argument(..., help="Run id")) -> None:
    """Re-open a previously closed feedback (status → open)."""
    try:
        fb = feedback_mod.set_status(run_id, feedback_mod.STATUS_OPEN)
    except (FileNotFoundError, ValueError) as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    rprint(f"[green]reopened[/green] {run_id}")
    rprint(fb.model_dump())


if __name__ == "__main__":
    app()
