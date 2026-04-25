import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Pipeline, type ProjectDetail, type RunSummary } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId } from "../lib/format";
import { Pill, StatusPill } from "../components/Pill";

export default function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.project(projectId), api.projectRuns(projectId), api.pipelines()])
      .then(([p, r, ps]) => {
        if (cancelled) return;
        setProject(p); setRuns(r); setPipelines(ps);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, [projectId]);

  if (err) {
    return (
      <section className="page-in">
        <Link to="/projects" className="text-[13px] text-[var(--color-muted)] hover:text-[var(--color-forge)]">← back to projects</Link>
        <div className="mt-6 rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      </section>
    );
  }

  if (!project) {
    return <section className="page-in"><div className="text-[14px] text-[var(--color-muted)]">loading…</div></section>;
  }

  return (
    <section className="page-in">
      {/* Breadcrumb */}
      <div className="mb-4 text-[13px] text-[var(--color-muted)]">
        <Link to="/projects" className="hover:text-[var(--color-forge)]">Projects</Link>
        <span className="mx-2 text-[var(--color-faint)]">/</span>
        <span className="text-[var(--color-text-2)]">{project.id}</span>
      </div>

      {/* Header */}
      <header className="mb-10 grid grid-cols-1 gap-8 border-b border-[var(--color-line)] pb-8 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <h1 className="font-display italic text-[52px] leading-[1.02] tracking-[-0.02em] text-[var(--color-text)]">
            {project.name}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[13.5px] text-[var(--color-muted)]">
            <span className="font-mono">{project.id}</span>
            {project.genre && <><span className="text-[var(--color-faint)]">·</span><span>{project.genre}</span></>}
          </div>
          {project.description && (
            <p className="mt-5 max-w-[68ch] text-[15px] leading-relaxed text-[var(--color-text-2)]">
              {project.description}
            </p>
          )}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <Pill tone={project.has_video ? "emerald" : "muted"}>{project.has_video ? "video ✓" : "no video"}</Pill>
            <Pill tone={project.has_assets ? "emerald" : "muted"}>{project.has_assets ? "assets ✓" : "no assets"}</Pill>
            {project.category_id && <Pill>category {project.category_id}</Pill>}
            {project.country && <Pill>{project.country}</Pill>}
          </div>
        </div>
      </header>

      {/* Run a pipeline */}
      <h2 className="mb-4 font-display italic text-[28px] tracking-[-0.01em] text-[var(--color-text)]">Run a pipeline</h2>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {pipelines?.map((pipe) => (
          <PipelineLauncher key={pipe.id} project={project} pipe={pipe} />
        ))}
      </div>

      {/* Runs */}
      <h2 className="mt-14 mb-4 font-display italic text-[28px] tracking-[-0.01em] text-[var(--color-text)]">
        Runs <span className="text-[var(--color-muted)]">· {runs?.length ?? 0}</span>
      </h2>
      {runs && runs.length === 0 && (
        <div className="rounded border border-dashed border-[var(--color-line-2)] p-8 text-center text-[14px] text-[var(--color-muted)]">
          No runs yet for this project.
        </div>
      )}
      {runs && runs.length > 0 && (
        <ul className="stagger overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]">
          {runs.map((r) => <RunRow key={r.run_id} r={r} />)}
        </ul>
      )}
    </section>
  );
}

function PipelineLauncher({ project, pipe }: { project: ProjectDetail; pipe: Pipeline }) {
  const [configId, setConfigId] = useState<string>(pipe.configs[0]?.id ?? "default");
  const cfg = useMemo(() => pipe.configs.find((c) => c.id === configId), [pipe, configId]);
  const blocked = pipe.needs.includes("video") && !project.video_path;
  const cli = `uv run adforge run ${pipe.id.replace("_forge", "")} --project ${project.id}${configId !== "default" ? ` --config ${configId}` : ""}`;

  const copy = async () => {
    try { await navigator.clipboard.writeText(cli); } catch { /* ignore */ }
  };

  return (
    <div className={`relative overflow-hidden rounded-lg border bg-[var(--color-surface)] p-6 ${blocked ? "border-[var(--color-line)] opacity-60" : "border-[var(--color-line)] hover:border-[var(--color-forge)]/40"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display italic text-[24px] leading-tight tracking-[-0.01em] text-[var(--color-text)]">
            {pipe.name}
          </h3>
          <p className="mt-1.5 max-w-[42ch] text-[13.5px] leading-relaxed text-[var(--color-text-2)]">
            {pipe.tagline}
          </p>
        </div>
        <span className="font-display italic text-[34px] text-[var(--color-forge)]/60">{pipe.glyph}</span>
      </div>

      {blocked && (
        <div className="mt-4 rounded border border-[var(--color-rust)]/30 bg-[var(--color-rust)]/5 px-3 py-2 text-[12.5px] text-[var(--color-rust)]">
          needs <code className="font-mono">video.mp4</code> in this project
        </div>
      )}

      <div className="mt-5">
        <label className="text-[12px] text-[var(--color-muted)]">Config</label>
        <select
          value={configId}
          onChange={(e) => setConfigId(e.target.value)}
          className="mt-1 w-full rounded border border-[var(--color-line-2)] bg-[var(--color-canvas)] px-3 py-2 text-[13.5px] text-[var(--color-text)] focus:border-[var(--color-forge)] focus:outline-none"
        >
          {pipe.configs.map((c) => (
            <option key={c.id} value={c.id}>{c.name} — {c.description}</option>
          ))}
        </select>
        {cfg && (
          <p className="mt-2 text-[12.5px] text-[var(--color-muted)]">{cfg.description}</p>
        )}
      </div>

      <button
        onClick={copy}
        disabled={blocked}
        className={`mt-5 group block w-full text-left ${blocked ? "cursor-not-allowed" : ""}`}
      >
        <div className="text-[12px] text-[var(--color-muted)]">CLI · click to copy</div>
        <div className="mt-1 break-all rounded border border-[var(--color-line)] bg-[var(--color-canvas)] px-3 py-2.5 font-mono text-[12.5px] text-[var(--color-text)] group-hover:border-[var(--color-forge)] group-hover:text-[var(--color-forge)] transition-colors">
          {cli}
        </div>
      </button>
    </div>
  );
}

function RunRow({ r }: { r: RunSummary }) {
  const parsed = parseRunId(r.run_id);
  return (
    <li>
      <Link
        to={`/runs/${encodeURIComponent(r.run_id)}`}
        className="row-hairline grid grid-cols-[1.4fr_120px_120px_120px_120px] items-center gap-5 px-5 py-3.5 text-[14px] transition-colors"
      >
        <div className="min-w-0">
          <div className="truncate text-[var(--color-text)]">{parsed?.ts ?? fmtTime(r.started_at)}</div>
          <div className="mt-0.5 truncate font-mono text-[11.5px] text-[var(--color-faint)]">{r.run_id}</div>
        </div>
        <div className="text-[var(--color-text-2)]">{r.pipeline ?? "—"}</div>
        <div className="text-[var(--color-muted)]">{r.config_id ?? "—"}</div>
        <div className="text-[var(--color-muted)]">{fmtDuration(r.started_at, r.completed_at)}</div>
        <div className="flex justify-end"><StatusPill status={r.status} /></div>
      </Link>
    </li>
  );
}
