import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Pipeline, type Project, type RunSummary } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId } from "../lib/format";
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
      {/* Editorial hero */}
      <header className="relative isolate mb-10 overflow-hidden rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)]">
        <div className="bp-grid absolute inset-0 opacity-50" aria-hidden />
        <div
          className="absolute -top-32 -right-24 size-[420px] rounded-full opacity-30 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(255,110,61,0.55), transparent 60%)" }}
          aria-hidden
        />
        <div className="relative px-10 pt-14 pb-16">
          <h1 className="max-w-[24ch] font-display text-[64px] leading-[1.0] tracking-[-0.02em] text-[var(--color-text)]">
            <span className="italic">Build ads for your games,</span>{" "}
            <span className="italic text-[var(--color-forge)]">faster.</span>
          </h1>
          <p className="mt-6 max-w-[68ch] text-[16px] leading-relaxed text-[var(--color-text-2)]">
            adforge runs Temporal pipelines on your <em className="font-display not-italic text-[var(--color-text)]">projects</em> (games)
            to produce <em className="font-display not-italic text-[var(--color-text)]">runs</em> (folders of artifacts you can ship).
            Two pipelines today: a video-ad creator and a playable-ad builder.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              to="/projects"
              className="rounded-md bg-[var(--color-forge)] px-5 py-2.5 text-[14px] font-medium text-[var(--color-canvas)] hover:opacity-90 transition-opacity"
            >
              Open projects
            </Link>
            <Link
              to="/pipelines"
              className="rounded-md border border-[var(--color-line-2)] px-5 py-2.5 text-[14px] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)] transition-colors"
            >
              Browse pipelines
            </Link>
          </div>
        </div>
      </header>

      {/* Three cards = the model */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <SummaryCard
          title="Projects"
          tagline="One folder per game. Drop a project.json + optional video + assets."
          count={projects?.length}
          countLabel="on disk"
          href="/projects"
          previews={projects?.slice(0, 3).map((p) => ({ key: p.id, label: p.name, hint: p.genre ?? p.id }))}
        />
        <SummaryCard
          title="Pipelines"
          tagline="Recipes that turn projects into runs. Each has named configs to A/B."
          count={pipelines?.length}
          countLabel="available"
          href="/pipelines"
          previews={pipelines?.map((p) => ({ key: p.id, label: p.name, hint: p.tagline.split("→")[0].trim() }))}
        />
        <SummaryCard
          title="Runs"
          tagline="One folder per execution. Manifest + artifacts, deep-linked to Temporal."
          count={runs?.length}
          countLabel="on disk"
          href="/runs"
          previews={runs?.slice(0, 3).map((r) => ({
            key: r.run_id,
            label: parseRunId(r.run_id)?.ts ?? fmtTime(r.started_at),
            hint: `${r.pipeline ?? "?"} · ${r.project_id ?? "?"}`,
          }))}
        />
      </div>

      {/* Recent runs */}
      <div className="mt-12">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display italic text-[26px] tracking-[-0.01em] text-[var(--color-text)]">Recent activity</h2>
          {runs && runs.length > 0 && (
            <Link to="/runs" className="text-[13px] text-[var(--color-muted)] hover:text-[var(--color-forge)]">
              all runs →
            </Link>
          )}
        </div>
        {runs && runs.length === 0 && (
          <div className="rounded border border-dashed border-[var(--color-line-2)] p-8 text-center text-[14px] text-[var(--color-muted)]">
            No runs yet — open a project and hit "run" on a pipeline.
          </div>
        )}
        {runs && runs.length > 0 && (
          <ul className="stagger overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]">
            {runs.slice(0, 6).map((r) => (
              <li key={r.run_id}>
                <Link
                  to={`/runs/${encodeURIComponent(r.run_id)}`}
                  className="row-hairline grid grid-cols-[1.4fr_120px_140px_120px_100px] items-center gap-5 px-5 py-3.5 text-[14px]"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[var(--color-text)]">{parseRunId(r.run_id)?.ts ?? fmtTime(r.started_at)}</div>
                    <div className="mt-0.5 truncate font-mono text-[11.5px] text-[var(--color-faint)]">{r.run_id}</div>
                  </div>
                  <div className="text-[var(--color-text-2)]">{r.pipeline ?? "—"}</div>
                  <div className="truncate text-[var(--color-text-2)]">{r.project_id ?? "—"}</div>
                  <div className="text-[var(--color-muted)]">{fmtDuration(r.started_at, r.completed_at)}</div>
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
      className="group flex flex-col gap-5 rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-6 transition-colors hover:border-[var(--color-forge)]/40"
    >
      <div>
        <h3 className="font-display italic text-[30px] leading-[1.05] tracking-[-0.01em] text-[var(--color-text)]">
          {title}
        </h3>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--color-text-2)]">{tagline}</p>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-display italic text-[44px] leading-none text-[var(--color-text)]">
          {count === undefined ? "—" : count.toString().padStart(2, "0")}
        </span>
        <span className="text-[13px] text-[var(--color-muted)]">{countLabel}</span>
      </div>
      <ul className="space-y-1.5 border-t border-[var(--color-line)] pt-4 text-[13px]">
        {(previews ?? []).map((p) => (
          <li key={p.key} className="flex items-center justify-between gap-3">
            <span className="truncate text-[var(--color-text)]">{p.label}</span>
            <span className="shrink-0 text-[12px] text-[var(--color-muted)]">{p.hint}</span>
          </li>
        ))}
        {(previews?.length ?? 0) === 0 && (
          <li className="text-[var(--color-muted)]">— empty —</li>
        )}
      </ul>
      <div className="mt-auto text-[13px] text-[var(--color-muted)] group-hover:text-[var(--color-forge)] transition-colors">
        Open →
      </div>
    </Link>
  );
}
