import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Pipeline, type PipelineInput, type ProjectDetail, type RunSummary } from "../lib/api";
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
        <Link to="/projects" className="text-[13px] text-[var(--color-muted)] hover:text-[var(--color-rust)]">back to projects</Link>
        <div className="mt-6 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] p-4 text-[14px] text-[var(--color-text)]">
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
      <div className="mb-4 text-[13px] text-[var(--color-muted)]">
        <Link to="/projects" className="hover:text-[var(--color-rust)]">projects</Link>
        <span className="mx-2 text-[var(--color-faint)]">/</span>
        <span className="text-[var(--color-text-2)]">{project.name}</span>
      </div>

      <header className="mb-8 border-b-[3px] border-[var(--color-line)] pb-8">
        <div className="min-w-0">
          <h1 className="font-display text-[58px] font-bold leading-[1.02] tracking-[-0.035em] text-[var(--color-text)]">
            {project.name}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {project.genre && <Pill tone="forge">{project.genre}</Pill>}
            {project.subgenre && <Pill tone="saffron">{project.subgenre}</Pill>}
            {project.art_style && <Pill>{project.art_style}</Pill>}
            {project.juice && <Pill tone="rust">{project.juice} juice</Pill>}
          </div>
          <p className="mt-5 max-w-[68ch] text-[22px] font-bold leading-snug text-[var(--color-text)]">
            {project.elevator_pitch || "could not infer a short pitch because no design doc or descriptive project notes were found."}
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-7 lg:grid-cols-[minmax(0,1fr)_420px]">
        <main className="min-w-0">
          <section className="card-pop bg-[var(--color-surface)] p-6">
            <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">next step</div>
            <h2 className="mt-1 font-display text-[42px] font-bold leading-tight tracking-[-0.035em] text-[var(--color-text)]">
              make marketing material
            </h2>
            <p className="mt-2 max-w-[68ch] text-[15px] leading-relaxed text-[var(--color-text-2)]">
              choose what you want to create. adforge will use this project’s pitch, visuals, videos, and notes to make a first draft.
            </p>
          </section>

          <div className="mt-6 space-y-5">
            {pipelines?.map((pipe) => (
              <PipelineLauncher key={pipe.id} project={project} pipe={pipe} />
            ))}
          </div>

          <h2 className="mt-14 mb-4 font-display text-[32px] font-bold tracking-[-0.02em] text-[var(--color-text)]">
            output history <span className="text-[var(--color-muted)]">· {runs?.length ?? 0}</span>
          </h2>
          {runs && runs.length === 0 && (
            <div className="rounded border-[3px] border-dashed border-[var(--color-line)] p-8 text-center text-[14.5px] text-[var(--color-text-2)]">
              nothing made yet for this project.
            </div>
          )}
          {runs && runs.length > 0 && (
            <ul className="stagger overflow-hidden rounded-lg border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
              {runs.map((r) => <RunRow key={r.run_id} r={r} />)}
            </ul>
          )}
        </main>

        <ProjectMedia project={project} />
      </div>
    </section>
  );
}

function ProjectMedia({ project }: { project: ProjectDetail }) {
  const screenshots = project.screenshots ?? [];
  const videos = project.gameplay_videos ?? [];
  const docs = project.design_documents ?? [];
  const palette = project.color_palette ?? [];

  return (
    <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
      <div className="card-pop bg-[var(--color-surface)] p-5">
        <div className="mb-3 text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">game info</div>
        <div className="grid grid-cols-2 gap-3 text-[14px]">
          <Info label="genre" value={project.genre} />
          <Info label="subgenre" value={project.subgenre} />
          <Info label="art style" value={project.art_style} />
          <Info label="juice" value={project.juice} />
        </div>
        <div className="mt-4">
          <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">summary</div>
          <p className="mt-1 text-[var(--color-text)]">
            {project.summary || project.description || "could not infer a summary because no design doc or descriptive project notes were found."}
          </p>
        </div>
        <div className="mt-4">
          <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">color palette</div>
          {palette.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {palette.map((color) => <ColorChip key={color} label={color} />)}
            </div>
          ) : (
            <div className="mt-1 text-[var(--color-muted)]">could not infer without screenshots or images</div>
          )}
        </div>
        <div className="mt-4">
          <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">design document</div>
          {docs[0] ? (
            <a
              href={api.projectFileUrl(project.id, docs[0].rel_path)}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block underline decoration-[3px] underline-offset-4"
            >
              open {docs[0].name}
            </a>
          ) : (
            <div className="mt-1 text-[var(--color-muted)]">no design document found in the project folder</div>
          )}
        </div>
      </div>

      <div className="card-pop bg-[var(--color-surface)] p-5">
        <div className="mb-3 text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">gameplay video</div>
        {videos[0] ? (
          <video
            src={api.projectFileUrl(project.id, videos[0].rel_path)}
            controls
            className="aspect-video w-full rounded border-[3px] border-[var(--color-line)] bg-black object-cover"
          />
        ) : (
          <p className="text-[14px] text-[var(--color-muted)]">no gameplay video found</p>
        )}
      </div>

      <div className="card-pop bg-[var(--color-surface)] p-5">
        <div className="mb-3 text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">screenshots</div>
        {screenshots.length ? (
          <div className="grid grid-cols-2 gap-3">
            {screenshots.slice(0, 8).map((shot) => (
              <img
                key={shot.rel_path}
                src={api.projectFileUrl(project.id, shot.rel_path)}
                alt={shot.name}
                className="aspect-square w-full rounded border-[3px] border-[var(--color-line)] object-cover"
              />
            ))}
          </div>
        ) : (
          <div className="rounded border-[3px] border-dashed border-[var(--color-line)] bg-[var(--color-canvas)] p-8 text-center text-[14px] text-[var(--color-muted)]">
            no screenshots found in the project folder
          </div>
        )}
      </div>
    </aside>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">{label}</div>
      <div className="mt-1 text-[var(--color-text)]">{value || "could not infer from files"}</div>
    </div>
  );
}

function ColorChip({ label }: { label: string }) {
  const hex = label.match(/#[0-9a-f]{6}/i)?.[0];
  return (
    <span
      className="inline-flex items-center gap-2 rounded border-2 border-[var(--color-line)] px-2.5 py-[3px] text-[11.5px] font-bold"
      style={{ backgroundColor: hex ?? "var(--color-canvas)", color: textColor(hex) }}
    >
      <span
        className="inline-block size-3 rounded border border-[var(--color-line)]"
        style={{ backgroundColor: hex ?? "transparent" }}
      />
      {label}
    </span>
  );
}

function textColor(hex?: string) {
  if (!hex) return "var(--color-text)";
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? "#000" : "#fff";
}

function isInputSatisfied(project: ProjectDetail, i: PipelineInput): boolean {
  if (!i.required) return true;
  if (i.id === "video")    return Boolean(project.video_path);
  if (i.id === "assets")   return Boolean(project.asset_dir);
  if (i.id === "metadata") return true;
  return true;
}

function PipelineLauncher({ project, pipe }: { project: ProjectDetail; pipe: Pipeline }) {
  const navigate = useNavigate();
  const [configId, setConfigId] = useState<string>(pipe.configs[pipe.configs.length - 1]?.id ?? "default");
  const cfg = useMemo(() => pipe.configs.find((c) => c.id === configId), [pipe, configId]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const missing = pipe.inputs.filter((i) => !isInputSatisfied(project, i));
  const blocked = missing.length > 0;

  const onRun = async () => {
    if (blocked || busy) return;
    setErr(null);
    setBusy(true);
    try {
      const res = await api.startRun(pipe.id, project.id, configId);
      navigate(`/runs/${encodeURIComponent(res.run_id)}`);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setBusy(false);
    }
  };

  return (
    <div className={`card-pop relative overflow-hidden bg-[var(--color-surface)] p-6 ${blocked ? "opacity-70" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-[28px] font-bold leading-tight tracking-[-0.02em] text-[var(--color-text)]">
            {pipe.name}
          </h3>
        </div>
      </div>

      <p className="mt-4 max-w-[48ch] text-[14.5px] leading-relaxed text-[var(--color-text-2)]">
        {pipe.description}
      </p>

      {pipe.inputs.length > 0 && (
        <ul className="mt-4 space-y-2">
          {pipe.inputs.map((i) => {
            const ok = isInputSatisfied(project, i);
            return (
              <li key={i.id} className="flex gap-2 text-[13.5px] text-[var(--color-text-2)]">
                <Pill tone={ok ? "emerald" : (i.required ? "rust" : "muted")}>{ok ? "ready" : (i.required ? "missing" : "optional")}</Pill>
                <span>{i.description}</span>
              </li>
            );
          })}
        </ul>
      )}

      {blocked && (
        <div className="mt-4 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] px-3 py-2 text-[13px] text-[var(--color-text)]">
          this needs {missing.map((m) => m.description).join(", ")} before it can run.
        </div>
      )}

      <div className="mt-5">
        <label className="text-[12px] font-bold tracking-[0.08em] text-[var(--color-muted)]">output style</label>
        <select
          value={configId}
          onChange={(e) => setConfigId(e.target.value)}
          className="mt-1.5 w-full rounded border-[3px] border-[var(--color-line)] bg-[var(--color-canvas)] px-3 py-2 text-[14px] text-[var(--color-text)] focus:outline-none"
        >
          {pipe.configs.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {cfg && (
          <p className="mt-2 text-[13px] text-[var(--color-text-2)]">{cfg.description}</p>
        )}
      </div>

      <button
        onClick={onRun}
        disabled={blocked || busy}
        className={`mt-5 w-full px-5 py-3 text-[15px] font-bold transition-opacity ${
          blocked
            ? "cursor-not-allowed border-[3px] border-[var(--color-line)] bg-[var(--color-canvas)] text-[var(--color-faint)]"
            : busy
              ? "btn-primary cursor-wait opacity-70"
              : "btn-primary"
        }`}
      >
        {busy ? "starting..." : blocked ? "not ready yet" : "make this"}
      </button>

      {err && (
        <div className="mt-3 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] px-3 py-2 text-[13px] text-[var(--color-text)]">
          {err}
        </div>
      )}
    </div>
  );
}

function RunRow({ r }: { r: RunSummary }) {
  const parsed = parseRunId(r.run_id);
  return (
    <li>
      <Link
        to={`/runs/${encodeURIComponent(r.run_id)}`}
        className="row-hairline grid grid-cols-[1.4fr_140px_120px_120px] items-center gap-5 px-5 py-3.5 text-[14px] transition-colors"
      >
        <div className="min-w-0">
          <div className="truncate text-[var(--color-text)]">{parsed?.ts ?? fmtTime(r.started_at)}</div>
          <div className="mt-0.5 truncate text-[11.5px] text-[var(--color-faint)]">created</div>
        </div>
        <div className="text-[var(--color-text-2)]">{friendlyPipeline(r.pipeline)}</div>
        <div className="text-[var(--color-muted)]">{fmtDuration(r.started_at, r.completed_at)}</div>
        <div className="flex justify-end"><StatusPill status={r.status} /></div>
      </Link>
    </li>
  );
}

function friendlyPipeline(pipeline: string | null) {
  if (pipeline === "creative_forge") return "video ad";
  if (pipeline === "playable_forge") return "playable ad";
  return pipeline || "marketing output";
}
