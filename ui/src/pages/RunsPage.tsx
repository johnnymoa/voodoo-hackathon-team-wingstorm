import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RunSummary } from "../lib/api";
import { fmtDuration, fmtTime, parseRunId } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { StatusPill } from "../components/Pill";

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
    const q = filter.trim().toLowerCase();
    if (!q) return runs;
    return runs.filter((r) =>
      r.run_id.toLowerCase().includes(q) ||
      (r.pipeline ?? "").toLowerCase().includes(q) ||
      (r.project_id ?? "").toLowerCase().includes(q) ||
      (r.config_id ?? "").toLowerCase().includes(q),
    );
  }, [runs, filter]);

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="Runs"
        title="Every execution."
        subtitle="One row per run. Click to inspect the manifest and the artifacts it produced."
        right={
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter by id, pipeline, project, config"
            className="w-[340px] rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-2 text-[13.5px] placeholder:text-[var(--color-faint)] focus:border-[var(--color-forge)] focus:outline-none"
          />
        }
      />

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

      {filtered && filtered.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]">
          <div className="grid grid-cols-[1.6fr_140px_160px_120px_120px_100px] items-center gap-5 border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[12px] text-[var(--color-muted)]">
            <span>When · run_id</span>
            <span>Pipeline</span>
            <span>Project</span>
            <span>Config</span>
            <span>Duration</span>
            <span className="text-right">Status</span>
          </div>
          <ul className="stagger">
            {filtered.map((r) => <RunRow key={r.run_id} r={r} />)}
          </ul>
        </div>
      )}
    </section>
  );
}

function RunRow({ r }: { r: RunSummary }) {
  const parsed = parseRunId(r.run_id);
  return (
    <li>
      <Link
        to={`/runs/${encodeURIComponent(r.run_id)}`}
        className="row-hairline grid grid-cols-[1.6fr_140px_160px_120px_120px_100px] items-center gap-5 px-5 py-3.5 text-[14px] transition-colors"
      >
        <div className="min-w-0">
          <div className="truncate text-[var(--color-text)]">{parsed?.ts ?? fmtTime(r.started_at)}</div>
          <div className="mt-0.5 truncate font-mono text-[11.5px] text-[var(--color-faint)]">{r.run_id}</div>
        </div>
        <div className="text-[var(--color-text-2)]">{r.pipeline ?? "—"}</div>
        <div className="truncate text-[var(--color-text-2)]">{r.project_id ?? "—"}</div>
        <div className="text-[var(--color-muted)]">{r.config_id ?? "—"}</div>
        <div className="text-[var(--color-muted)]">{fmtDuration(r.started_at, r.completed_at)}</div>
        <div className="flex justify-end"><StatusPill status={r.status} /></div>
      </Link>
    </li>
  );
}
