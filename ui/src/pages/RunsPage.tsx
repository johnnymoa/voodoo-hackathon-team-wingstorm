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
        eyebrow="history"
        title="everything made"
        subtitle="a timeline of marketing outputs, newest first. open any row to view the files and leave feedback for the next version."
        right={
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter by output, project, or style"
            className="w-[340px] rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] px-3 py-2 text-[13.5px] placeholder:text-[var(--color-faint)] focus:outline-none"
          />
        }
      />

      {err && (
        <div className="mb-6 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] p-4 text-[14px] text-[var(--color-text)]">
          {err}
        </div>
      )}

      {filtered && filtered.length === 0 && !err && (
        <div className="rounded border-[3px] border-dashed border-[var(--color-line)] p-10 text-center">
          <p className="font-display text-[26px] font-bold text-[var(--color-text)]">nothing made yet</p>
          <p className="mt-2 text-[14px] text-[var(--color-text-2)]">
            open a project and choose what you want to create.
          </p>
        </div>
      )}

      {filtered && filtered.length > 0 && (
        <div className="overflow-hidden rounded-lg border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
          <div className="grid grid-cols-[1.6fr_150px_160px_120px_100px] items-center gap-5 border-b-[3px] border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[12px] font-bold text-[var(--color-muted)]">
            <span>created</span>
            <span>output</span>
            <span>project</span>
            <span>time</span>
            <span className="text-right">status</span>
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
        className="row-hairline grid grid-cols-[1.6fr_150px_160px_120px_100px] items-center gap-5 px-5 py-3.5 text-[14px] transition-colors"
      >
        <div className="min-w-0">
          <div className="truncate text-[var(--color-text)]">{parsed?.ts ?? fmtTime(r.started_at)}</div>
          <div className="mt-0.5 truncate text-[11.5px] text-[var(--color-faint)]">created</div>
        </div>
        <div className="text-[var(--color-text-2)]">{friendlyPipeline(r.pipeline)}</div>
        <div className="truncate text-[var(--color-text-2)]">{r.project_id ?? "—"}</div>
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
