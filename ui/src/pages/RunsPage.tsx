import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RunSummary } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId, pipelineGlyph } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { StatusPill } from "../components/Pill";

type ViewMode = "all" | "by-game";
type SortDir = "newest" | "oldest";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");
  const [view, setView] = useState<ViewMode>("all");
  const [sort, setSort] = useState<SortDir>("newest");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = () => {
      api.runs()
        .then((r) => {
          if (cancelled) return;
          setRuns(r);
          setErr(null);
          const anyRunning = r.some((row) => row.status === "running");
          timer = setTimeout(tick, anyRunning ? 2000 : 5000);
        })
        .catch((e) => {
          if (cancelled) return;
          setErr(String(e));
          timer = setTimeout(tick, 5000);
        });
    };
    tick();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, []);

  const filtered = useMemo(() => {
    if (!runs) return null;
    const q = filter.trim().toLowerCase();
    let list = runs;
    if (q) {
      list = list.filter((r) =>
        r.run_id.toLowerCase().includes(q) ||
        (r.pipeline ?? "").toLowerCase().includes(q) ||
        (r.project_id ?? "").toLowerCase().includes(q) ||
        (r.config_id ?? "").toLowerCase().includes(q),
      );
    }
    if (sort === "oldest") return [...list].reverse();
    return list;
  }, [runs, filter, sort]);

  const grouped = useMemo(() => {
    if (!filtered || view !== "by-game") return null;
    const map = new Map<string, RunSummary[]>();
    for (const r of filtered) {
      // Fall back to extracting project from run_id when project_id is null
      let key = r.project_id;
      if (!key) {
        const parts = r.run_id.split("__");
        key = parts.length >= 3 ? parts[parts.length - 1] : "unknown";
      }
      // Normalize old project names
      if (key === "castle_clashers") key = "castle_busters";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(r);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered, view]);

  const projects = useMemo(() => {
    if (!runs) return [];
    const s = new Set<string>();
    for (const r of runs) {
      let pid = r.project_id;
      if (!pid) {
        const parts = r.run_id.split("__");
        pid = parts.length >= 3 ? parts[parts.length - 1] : null;
      }
      if (pid === "castle_clashers") pid = "castle_busters";
      if (pid) s.add(pid);
    }
    return [...s].sort();
  }, [runs]);

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="Runs"
        title="Every execution."
        subtitle="Browse all runs chronologically or grouped by game. Click any run to inspect artifacts and leave feedback."
        right={
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter by id, pipeline, project, config"
            className="w-[340px] rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-2 text-[13.5px] placeholder:text-[var(--color-faint)] focus:border-[var(--color-forge)] focus:outline-none"
          />
        }
      />

      {/* View controls */}
      <div className="mb-6 flex items-center gap-3">
        <div className="flex rounded-md border border-[var(--color-line)] overflow-hidden text-[13px]">
          <ViewBtn active={view === "all"} onClick={() => setView("all")}>All stacked</ViewBtn>
          <ViewBtn active={view === "by-game"} onClick={() => setView("by-game")}>By game</ViewBtn>
        </div>
        <div className="flex rounded-md border border-[var(--color-line)] overflow-hidden text-[13px]">
          <ViewBtn active={sort === "newest"} onClick={() => setSort("newest")}>Newest first</ViewBtn>
          <ViewBtn active={sort === "oldest"} onClick={() => setSort("oldest")}>Oldest first</ViewBtn>
        </div>
        {runs && (
          <span className="ml-auto text-[12px] text-[var(--color-muted)]">
            {filtered?.length ?? 0} runs · {projects.length} games
          </span>
        )}
      </div>

      {err && (
        <div className="mb-6 rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {filtered && filtered.length === 0 && !err && (
        <div className="rounded border border-dashed border-[var(--color-line-2)] p-10 text-center">
          <p className="font-display italic text-[24px] text-[var(--color-text)]">No runs yet.</p>
          <p className="mt-2 text-[14px] text-[var(--color-text-2)]">
            Open a project and run a pipeline to get started.
          </p>
        </div>
      )}

      {/* All stacked view */}
      {view === "all" && filtered && filtered.length > 0 && (
        <RunTable runs={filtered} />
      )}

      {/* By game view */}
      {view === "by-game" && grouped && grouped.map(([projectId, gameRuns]) => (
        <div key={projectId} className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <h2 className="font-display italic text-[22px] text-[var(--color-text)]">
              {projectId}
            </h2>
            <span className="rounded-full bg-[var(--color-surface-2)] px-2.5 py-0.5 text-[12px] text-[var(--color-muted)]">
              {gameRuns.length} runs
            </span>
          </div>
          <RunTable runs={gameRuns} compact />
        </div>
      ))}
    </section>
  );
}

function ViewBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3.5 py-1.5 transition-colors ${
        active
          ? "bg-[var(--color-forge)] text-white"
          : "bg-[var(--color-surface)] text-[var(--color-muted)] hover:text-[var(--color-text-2)]"
      }`}
    >
      {children}
    </button>
  );
}

function RunTable({ runs, compact }: { runs: RunSummary[]; compact?: boolean }) {
  return (
    <div className="overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className={`grid ${compact ? "grid-cols-[1fr_100px_120px_100px_60px_80px]" : "grid-cols-[1.4fr_120px_140px_120px_100px_60px_90px]"} items-center gap-4 border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-2.5 text-[11.5px] uppercase tracking-[0.06em] text-[var(--color-muted)]`}>
        <span>When</span>
        {!compact && <span>Project</span>}
        <span>Pipeline</span>
        <span>Config</span>
        <span>Duration</span>
        <span className="text-center">Fb</span>
        <span className="text-right">Status</span>
      </div>
      <ul className="stagger">
        {runs.map((r) => <RunRow key={r.run_id} r={r} compact={compact} />)}
      </ul>
    </div>
  );
}

function FeedbackBadge({ has, status }: { has: boolean; status?: string | null }) {
  if (!has) return <span className="text-[var(--color-faint)]">—</span>;
  if (status === "fulfilled") {
    return <span title="feedback fulfilled" className="text-[var(--color-emerald)] text-[14px]">✓</span>;
  }
  if (status === "wontfix") {
    return <span title="feedback wontfix" className="text-[var(--color-muted)] text-[14px]">✕</span>;
  }
  return <span title="open feedback" className="text-[var(--color-saffron)] text-[14px]">●</span>;
}

function RunRow({ r, compact }: { r: RunSummary; compact?: boolean }) {
  const parsed = parseRunId(r.run_id);
  const glyph = pipelineGlyph(r.pipeline);
  const pipelineLabel = r.pipeline === "creative_forge" ? "creative" : r.pipeline === "playable_forge" ? "playable" : (r.pipeline ?? "—");

  return (
    <li>
      <Link
        to={`/runs/${encodeURIComponent(r.run_id)}`}
        className={`row-hairline grid ${compact ? "grid-cols-[1fr_100px_120px_100px_60px_80px]" : "grid-cols-[1.4fr_120px_140px_120px_100px_60px_90px]"} items-center gap-4 px-5 py-3 text-[13.5px] transition-colors`}
      >
        <div className="min-w-0">
          <div className="truncate text-[var(--color-text)]">
            {parsed?.ts ?? fmtTime(r.started_at)}
          </div>
        </div>
        {!compact && (
          <div className="truncate text-[var(--color-text-2)] font-medium">{r.project_id ?? "—"}</div>
        )}
        <div className="flex items-center gap-1.5 text-[var(--color-text-2)]">
          <span className="text-[10px]">{glyph}</span>
          {pipelineLabel}
        </div>
        <div className="truncate text-[var(--color-muted)] text-[12.5px]">{r.config_id ?? "—"}</div>
        <div className="text-[var(--color-muted)] text-[12.5px]">{fmtDuration(r.started_at, r.completed_at)}</div>
        <div className="flex justify-center"><FeedbackBadge has={!!r.has_feedback} status={r.feedback_status ?? undefined} /></div>
        <div className="flex justify-end"><StatusPill status={r.status} /></div>
      </Link>
    </li>
  );
}
