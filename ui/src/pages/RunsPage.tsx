import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RunSummary } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId, pipelineGlyph } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { StatusPill } from "../components/Pill";
import { EmptyState } from "../components/EmptyState";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api.runs()
      .then((r) => !cancelled && setRuns(r))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    if (!runs) return null;
    if (!filter.trim()) return runs;
    const q = filter.toLowerCase();
    return runs.filter((r) =>
      r.run_id.toLowerCase().includes(q) ||
      (r.pipeline ?? "").toLowerCase().includes(q) ||
      (r.target_id ?? "").toLowerCase().includes(q),
    );
  }, [runs, filter]);

  const stats = useMemo(() => {
    if (!runs) return null;
    const byStatus = runs.reduce<Record<string, number>>((acc, r) => {
      acc[r.status] = (acc[r.status] ?? 0) + 1;
      return acc;
    }, {});
    return { total: runs.length, byStatus };
  }, [runs]);

  return (
    <section className="page-in">
      <PageHeader
        index="01"
        eyebrow="pipeline executions"
        title="Runs"
        accent={stats ? `${stats.total.toString().padStart(3, "0")} on disk` : undefined}
        right={
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter by id / pipeline / target"
            className="w-[320px] border border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-2 text-[12px] placeholder:text-[var(--color-faint)] focus:border-[var(--color-forge)] focus:outline-none"
          />
        }
      />

      {err && (
        <div className="mb-6 border border-[var(--color-rust)]/60 bg-[var(--color-rust)]/5 p-4 text-[12px] text-[var(--color-rust)]">
          could not reach the api at <span className="font-mono">/api/runs</span>: {err}
          <div className="mt-2 text-[var(--color-text-2)]">
            start it with <span className="font-mono text-[var(--color-text)]">uv run adforge api</span>.
          </div>
        </div>
      )}

      {filtered && filtered.length === 0 && !err && (
        <EmptyState
          title="No runs yet."
          body="Pipeline executions will appear here as they finish. Each row is a single run, identified by its run_id."
          hint={
            <>
              <div className="mb-2 text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)]">try one</div>
              <div className="font-mono text-[var(--color-text)]">
                $ uv run adforge run creative --target castle_clashers
              </div>
            </>
          }
        />
      )}

      {filtered && filtered.length > 0 && (
        <RunsTable rows={filtered} />
      )}
    </section>
  );
}

function RunsTable({ rows }: { rows: RunSummary[] }) {
  return (
    <div className="border border-[var(--color-line)] bg-[var(--color-surface)]">
      {/* Header row */}
      <div className="grid grid-cols-[14px_1.6fr_120px_140px_120px_120px_80px] items-center gap-4 border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2 text-[10px] uppercase tracking-[0.16em] text-[var(--color-muted)]">
        <span></span>
        <span>run_id</span>
        <span>pipeline</span>
        <span>target</span>
        <span>started</span>
        <span>duration</span>
        <span className="text-right">status</span>
      </div>

      <ul className="stagger">
        {rows.map((r) => (
          <RunRow key={r.run_id} r={r} />
        ))}
      </ul>
    </div>
  );
}

function RunRow({ r }: { r: RunSummary }) {
  const parsed = parseRunId(r.run_id);
  const ts = parsed?.ts ?? fmtTime(r.started_at);
  const duration = fmtDuration(r.started_at, r.completed_at);

  return (
    <li>
      <Link
        to={`/runs/${encodeURIComponent(r.run_id)}`}
        className="row-hairline group grid grid-cols-[14px_1.6fr_120px_140px_120px_120px_80px] items-center gap-4 px-4 py-3 transition-colors"
      >
        {/* edge tick — turns orange on hover (CSS) */}
        <span className="row-tick block h-[14px] w-[2px] bg-[var(--color-line-2)] transition-colors" />
        {/* run_id */}
        <div className="min-w-0">
          <div className="truncate text-[12.5px] text-[var(--color-text)] group-hover:text-[var(--color-forge)] transition-colors">
            {r.run_id}
          </div>
          <div className="mt-0.5 text-[10.5px] uppercase tracking-[0.12em] text-[var(--color-faint)]">
            {r.artifact_count} artifact{r.artifact_count === 1 ? "" : "s"}
            {!r.has_manifest && (
              <span className="ml-2 text-[var(--color-rust)]">no manifest</span>
            )}
          </div>
        </div>
        {/* pipeline */}
        <div className="text-[12px] text-[var(--color-text-2)]">
          <span className="mr-2 text-[var(--color-forge)]">{pipelineGlyph(r.pipeline)}</span>
          {r.pipeline ?? "—"}
        </div>
        {/* target */}
        <div className="truncate text-[12px] text-[var(--color-text-2)]">{r.target_id ?? "—"}</div>
        {/* started */}
        <div className="text-[12px] text-[var(--color-muted)]">{ts}</div>
        {/* duration */}
        <div className="text-[12px] text-[var(--color-muted)]">{duration}</div>
        {/* status */}
        <div className="flex justify-end">
          <StatusPill status={r.status} />
        </div>
      </Link>
    </li>
  );
}
