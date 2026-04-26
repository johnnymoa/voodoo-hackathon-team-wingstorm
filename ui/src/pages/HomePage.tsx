import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Pipeline, type Project, type RunSummary } from "../lib/api";
import { fmtTime, parseRunId } from "../lib/format";
import { StatusPill } from "../components/Pill";

export default function HomePage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[] | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.projects(), api.pipelines(), api.runs()])
      .then(([p, pl, r]) => {
        if (cancelled) return;
        setProjects(p); setPipelines(pl); setRuns(r);
      })
      .catch(() => { /* shown via empty counts */ });
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-in">
      <header className="card-pop relative isolate mb-10 overflow-hidden bg-[var(--color-surface)]">
        <div className="bp-grid absolute inset-0 opacity-80" aria-hidden />
        <div className="absolute right-8 top-8 hidden rotate-2 rounded border-[3px] border-black bg-[var(--color-saffron)] px-5 py-3 text-[15px] font-bold shadow-[4px_4px_0_#000] md:block">
          from game folder to campaign draft
        </div>
        <div className="relative grid grid-cols-1 gap-8 px-8 pt-14 pb-12 lg:grid-cols-[1.2fr_0.8fr] lg:px-12">
          <div>
            <h1 className="max-w-[12ch] font-display text-[72px] font-bold leading-[0.94] tracking-[-0.055em] text-[var(--color-text)] md:text-[92px]">
              make game marketing faster
            </h1>
            <p className="mt-6 max-w-[58ch] text-[20px] leading-relaxed text-[var(--color-text-2)]">
              adforge turns project information into useful marketing drafts: video ad concepts,
              playable ads, market-backed briefs, and the next version after feedback.
            </p>
            <div className="mt-7 flex flex-wrap gap-4">
              <Link
                to="/projects"
                className="btn-primary px-6 py-3 text-[16px] font-bold"
              >
                see projects
              </Link>
              <Link
                to="/pipelines"
                className="btn-secondary px-6 py-3 text-[16px] font-bold"
              >
                see what it can make
              </Link>
            </div>
          </div>

          <div className="grid content-end gap-4">
            <MiniPanel title="1. add the game" body="drop in the pitch, design doc, screenshots, video, and art." tone="bg-[var(--color-forge)]" />
            <MiniPanel title="2. choose an output" body="pick a video ad, playable ad, or market read." tone="bg-[var(--color-saffron)]" />
            <MiniPanel title="3. react and improve" body="leave feedback, make a sharper version, compare the results." tone="bg-[var(--color-rust)]" />
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <SummaryCard
          title="projects"
          tagline="game folders ready for marketing work."
          count={projects?.length}
          countLabel="available"
          href="/projects"
          previews={projects?.slice(0, 3).map((p) => ({ key: p.id, label: p.name, hint: p.genre ?? "game" }))}
        />
        <SummaryCard
          title="outputs"
          tagline="marketing materials adforge can create."
          count={pipelines?.length}
          countLabel="types"
          href="/pipelines"
          previews={pipelines?.map((p) => ({ key: p.id, label: p.name, hint: p.configs[p.configs.length - 1]?.name ?? "ready" }))}
        />
        <SummaryCard
          title="history"
          tagline="the latest things your team made."
          count={runs?.length}
          countLabel="made"
          href="/runs"
          previews={runs?.slice(0, 3).map((r) => ({
            key: r.run_id,
            label: parseRunId(r.run_id)?.ts ?? fmtTime(r.started_at),
            hint: friendlyPipeline(r.pipeline),
          }))}
        />
      </div>

      <div className="mt-12">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-[32px] font-bold tracking-[-0.02em] text-[var(--color-text)]">recent output</h2>
          {runs && runs.length > 0 && (
            <Link to="/runs" className="text-[13px] font-bold text-[var(--color-muted)] hover:text-[var(--color-rust)]">
              view all
            </Link>
          )}
        </div>
        {runs && runs.length === 0 && (
          <div className="rounded border-[3px] border-dashed border-[var(--color-line)] p-8 text-center text-[14.5px] text-[var(--color-text-2)]">
            nothing made yet. open a project and choose what you want to create.
          </div>
        )}
        {runs && runs.length > 0 && (
          <ul className="stagger overflow-hidden rounded-lg border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
            {runs.slice(0, 6).map((r) => (
              <li key={r.run_id}>
                <Link
                  to={`/runs/${encodeURIComponent(r.run_id)}`}
                  className="row-hairline grid grid-cols-[1.4fr_150px_140px_100px] items-center gap-5 px-5 py-3.5 text-[14px]"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[var(--color-text)]">{parseRunId(r.run_id)?.ts ?? fmtTime(r.started_at)}</div>
                    <div className="mt-0.5 truncate text-[11.5px] text-[var(--color-faint)]">created</div>
                  </div>
                  <div className="text-[var(--color-text-2)]">{friendlyPipeline(r.pipeline)}</div>
                  <div className="truncate text-[var(--color-text-2)]">{r.project_id ?? "project"}</div>
                  <div className="flex justify-end"><StatusPill status={r.status} /></div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function MiniPanel({ title, body, tone }: { title: string; body: string; tone: string }) {
  return (
    <div className={`rounded border-[3px] border-black p-4 shadow-[4px_4px_0_#000] ${tone}`}>
      <h3 className="font-display text-[22px] font-bold tracking-[-0.02em] text-black">{title}</h3>
      <p className="mt-1 text-[14px] leading-relaxed text-black">{body}</p>
    </div>
  );
}

function SummaryCard({
  title, tagline, count, countLabel, href, previews,
}: {
  title: string;
  tagline: string;
  count: number | undefined;
  countLabel: string;
  href: string;
  previews: { key: string; label: string; hint: string }[] | undefined;
}) {
  return (
    <Link
      to={href}
      className="card-pop group flex flex-col gap-5 bg-[var(--color-surface)] p-6"
    >
      <div>
        <h3 className="font-display text-[34px] font-bold leading-[1.05] tracking-[-0.03em] text-[var(--color-text)]">
          {title}
        </h3>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--color-text-2)]">{tagline}</p>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-[48px] font-bold leading-none text-[var(--color-text)]">
          {count === undefined ? "—" : count.toString().padStart(2, "0")}
        </span>
        <span className="text-[13px] text-[var(--color-muted)]">{countLabel}</span>
      </div>
      <ul className="space-y-1.5 border-t-[3px] border-[var(--color-line)] pt-4 text-[13px]">
        {(previews ?? []).map((p) => (
          <li key={p.key} className="flex items-center justify-between gap-3">
            <span className="truncate text-[var(--color-text)]">{p.label}</span>
            <span className="shrink-0 text-[12px] text-[var(--color-muted)]">{p.hint}</span>
          </li>
        ))}
        {(previews?.length ?? 0) === 0 && (
          <li className="text-[var(--color-muted)]">empty</li>
        )}
      </ul>
      <div className="mt-auto text-[13px] font-bold text-[var(--color-muted)] transition-colors group-hover:text-[var(--color-rust)]">
        open
      </div>
    </Link>
  );
}

function friendlyPipeline(pipeline: string | null) {
  if (pipeline === "creative_forge") return "video ad";
  if (pipeline === "playable_forge") return "playable ad";
  return pipeline || "marketing output";
}
