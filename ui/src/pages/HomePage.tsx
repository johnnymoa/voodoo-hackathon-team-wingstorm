import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Pipeline, type RunSummary, type Target } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId, pipelineGlyph } from "../lib/format";
import { StatusPill } from "../components/Pill";

/** The home page is the product manifesto.
 *  Three columns, three concepts: TARGET → PIPELINE → RUN.
 *  In 5 seconds a judge understands the entire tool. */
export default function HomePage() {
  const [targets, setTargets] = useState<Target[] | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[] | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.targets(), api.pipelines(), api.runs()])
      .then(([t, p, r]) => {
        if (cancelled) return;
        setTargets(t); setPipelines(p); setRuns(r);
      })
      .catch(() => { /* shown via empty counts */ });
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-in">
      {/* Editorial hero */}
      <header className="relative isolate overflow-hidden border border-[var(--color-line)] bg-[var(--color-surface)]">
        <div className="bp-grid absolute inset-0 opacity-40" aria-hidden />
        <div
          className="absolute -top-32 -right-24 size-[420px] rounded-full opacity-30 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(255,87,34,0.65), transparent 60%)" }}
          aria-hidden
        />
        <div className="relative px-10 pt-12 pb-14">
          <div className="flex items-center gap-3 text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">
            <span className="text-[var(--color-forge)]">§ 00</span>
            <span className="h-px w-12 bg-[var(--color-line-2)]" />
            <span>the forge</span>
          </div>
          <h1 className="mt-4 max-w-[20ch] font-display text-[64px] leading-[0.98] tracking-[-0.02em] text-[var(--color-text)]">
            <span className="italic">A single forge for</span>{" "}
            <span className="italic text-[var(--color-forge)]">ad assets.</span>
          </h1>
          <p className="mt-6 max-w-[64ch] text-[14px] leading-relaxed text-[var(--color-text-2)]">
            adforge turns a <em className="font-display not-italic text-[var(--color-text)]">target</em> (everything you know about a game) into a{" "}
            <em className="font-display not-italic text-[var(--color-text)]">run</em> (a self-describing folder of artifacts), via a{" "}
            <em className="font-display not-italic text-[var(--color-text)]">pipeline</em> (a recipe). One model, three pipelines today, more tomorrow.
          </p>
        </div>
      </header>

      {/* The blueprint — three columns with arrows between */}
      <div className="mt-10 grid grid-cols-1 gap-0 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <Column
          index="01"
          title="Target"
          tagline="Everything you know about a game."
          countLabel="targets on disk"
          count={targets?.length}
          href="/targets"
          ctaLabel="open targets →"
        >
          {targets && targets.length > 0 ? (
            <ul className="space-y-1">
              {targets.slice(0, 3).map((t) => (
                <li key={t.id} className="flex items-center justify-between gap-2 text-[12px]">
                  <Link to="/targets" className="truncate text-[var(--color-text)] hover:text-[var(--color-forge)]">
                    {t.name}
                  </Link>
                  <span className="shrink-0 text-[10.5px] text-[var(--color-faint)]">
                    {t.has_video ? "video " : "—   "}
                    {t.has_assets ? "assets" : "—"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyHint command="mkdir targets/<id> && echo '{}' > targets/<id>/target.json" />
          )}
        </Column>

        <Arrow />

        <Column
          index="02"
          title="Pipeline"
          tagline="A repeatable recipe."
          countLabel="pipelines available"
          count={pipelines?.length}
          href="/pipelines"
          ctaLabel="open catalog →"
        >
          {pipelines && pipelines.length > 0 ? (
            <ul className="space-y-1.5">
              {pipelines.map((p) => (
                <li key={p.id} className="flex items-center gap-2 text-[12px]">
                  <span className="text-[var(--color-forge)]">{p.glyph}</span>
                  <span className="text-[var(--color-text)]">{p.name}</span>
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-[12px] text-[var(--color-muted)]">loading…</span>
          )}
        </Column>

        <Arrow />

        <Column
          index="03"
          title="Run"
          tagline="The output, with manifest."
          countLabel="runs on disk"
          count={runs?.length}
          href="/runs"
          ctaLabel="open runs →"
        >
          {runs && runs.length > 0 ? (
            <ul className="space-y-1">
              {runs.slice(0, 3).map((r) => (
                <li key={r.run_id} className="flex items-center justify-between gap-2 text-[12px]">
                  <Link
                    to={`/runs/${encodeURIComponent(r.run_id)}`}
                    className="flex min-w-0 items-center gap-2 text-[var(--color-text)] hover:text-[var(--color-forge)]"
                  >
                    <span className="text-[var(--color-forge)]">{pipelineGlyph(r.pipeline)}</span>
                    <span className="truncate">{parseRunId(r.run_id)?.ts ?? fmtTime(r.started_at)}</span>
                  </Link>
                  <StatusPill status={r.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyHint command="uv run adforge run creative --target <id>" />
          )}
        </Column>
      </div>

      {/* Last activity strip */}
      <RecentRuns runs={runs} />
    </section>
  );
}

/* ─── small primitives, only used here ──────────────────────────────────── */

function Column({
  index, title, tagline, countLabel, count, href, ctaLabel, children,
}: {
  index: string;
  title: string;
  tagline: string;
  countLabel: string;
  count: number | undefined;
  href: string;
  ctaLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="group relative flex flex-col gap-4 border border-[var(--color-line)] bg-[var(--color-surface)] p-6 transition-colors hover:border-[var(--color-line-2)]">
      <span className="absolute inset-x-0 top-0 h-px bg-[var(--color-forge)] opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-center gap-3 text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">
        <span className="text-[var(--color-forge)]">§ {index}</span>
        <span className="h-px flex-1 bg-[var(--color-line)]" />
      </div>
      <div>
        <h2 className="font-display italic text-[34px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
          {title}
        </h2>
        <p className="mt-1 text-[12px] text-[var(--color-text-2)]">{tagline}</p>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-display italic text-[36px] leading-none text-[var(--color-text)]">
          {count === undefined ? "—" : count.toString().padStart(2, "0")}
        </span>
        <span className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-muted)]">{countLabel}</span>
      </div>
      <div className="border-t border-[var(--color-line)] pt-3">
        {children}
      </div>
      <Link
        to={href}
        className="mt-auto pt-2 text-[11px] uppercase tracking-[0.14em] text-[var(--color-muted)] hover:text-[var(--color-forge)] transition-colors"
      >
        {ctaLabel}
      </Link>
    </div>
  );
}

function Arrow() {
  return (
    <div className="hidden items-center justify-center px-4 text-[var(--color-faint)] lg:flex">
      <span className="font-display italic text-[40px] leading-none">→</span>
    </div>
  );
}

function EmptyHint({ command }: { command: string }) {
  return (
    <div className="border border-dashed border-[var(--color-line)] bg-[var(--color-canvas)] p-3">
      <div className="text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-faint)]">try</div>
      <div className="mt-1 break-all font-mono text-[11px] text-[var(--color-text-2)]">{command}</div>
    </div>
  );
}

function RecentRuns({ runs }: { runs: RunSummary[] | null }) {
  if (!runs || runs.length === 0) return null;
  const recent = runs.slice(0, 5);
  return (
    <div className="mt-12 border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="flex items-center justify-between border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2">
        <span className="text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)]">recent activity</span>
        <Link to="/runs" className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-text-2)] hover:text-[var(--color-forge)]">
          all runs →
        </Link>
      </div>
      <ul className="stagger">
        {recent.map((r) => {
          return (
            <li key={r.run_id}>
              <Link
                to={`/runs/${encodeURIComponent(r.run_id)}`}
                className="row-hairline grid grid-cols-[14px_1.4fr_120px_140px_120px_80px] items-center gap-4 px-4 py-3"
              >
                <span className="row-tick block h-[14px] w-[2px] bg-[var(--color-line-2)]" />
                <span className="truncate text-[12.5px] text-[var(--color-text)]">{r.run_id}</span>
                <span className="text-[12px] text-[var(--color-text-2)]">
                  <span className="mr-2 text-[var(--color-forge)]">{pipelineGlyph(r.pipeline)}</span>
                  {r.pipeline ?? "—"}
                </span>
                <span className="truncate text-[12px] text-[var(--color-text-2)]">{r.target_id ?? "—"}</span>
                <span className="text-[12px] text-[var(--color-muted)]">
                  {fmtDuration(r.started_at, r.completed_at)}
                </span>
                <span className="flex justify-end">
                  <StatusPill status={r.status} />
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
