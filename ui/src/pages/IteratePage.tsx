import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type FeedbackIndexRow } from "../lib/api";
import { fmtTime, parseRunId } from "../lib/format";
import { PageHeader } from "../components/Layout";

type StatusFilter = "open" | "fulfilled" | "wontfix" | "all";

export default function IteratePage() {
  const [rows, setRows] = useState<FeedbackIndexRow[] | null>(null);
  const [filter, setFilter] = useState<StatusFilter>("open");
  const [err, setErr] = useState<string | null>(null);
  const [copiedFor, setCopiedFor] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    api.feedbackIndex(filter)
      .then((r) => !cancelled && setRows(r))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, [filter]);

  // Group by project so iteration feels linear within a game's history
  const groupedByProject = useMemo(() => {
    if (!rows) return null;
    const map = new Map<string, FeedbackIndexRow[]>();
    for (const r of rows) {
      const k = r.project_id || "unknown";
      map.set(k, [...(map.get(k) ?? []), r]);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [rows]);

  const copyIterateCmd = async (runId: string) => {
    const cmd = `/iterate ${runId}`;
    try {
      await navigator.clipboard.writeText(cmd);
      setCopiedFor(runId);
      setTimeout(() => setCopiedFor((c) => (c === runId ? null : c)), 1800);
    } catch {
      /* noop */
    }
  };

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="Iterate"
        title="Open feedback awaiting iteration."
        subtitle="One row per run with feedback. Click 'Copy /iterate' and paste into Claude Code — the iterate skill will read the feedback, propose a new config, kick off a comparison run, and auto-close this row."
        right={
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as StatusFilter)}
            className="rounded border border-[var(--color-line-2)] bg-[var(--color-canvas)] px-3 py-1.5 text-[13.5px] text-[var(--color-text)] focus:border-[var(--color-forge)] focus:outline-none"
          >
            <option value="open">open ({rows?.filter(r => r.feedback_status === "open").length ?? 0})</option>
            <option value="fulfilled">fulfilled</option>
            <option value="wontfix">wontfix</option>
            <option value="all">all</option>
          </select>
        }
      />

      {err && (
        <div className="rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {rows && rows.length === 0 && (
        <div className="rounded border border-dashed border-[var(--color-line-2)] p-10 text-center">
          <p className="font-display italic text-[24px] text-[var(--color-text)]">No {filter} feedback.</p>
          <p className="mt-2 text-[14px] text-[var(--color-text-2)]">
            {filter === "open"
              ? "All caught up. Open a run, write feedback, come back here to iterate."
              : "Switch the filter to see other statuses."}
          </p>
        </div>
      )}

      {groupedByProject && groupedByProject.length > 0 && (
        <div className="space-y-8">
          {groupedByProject.map(([proj, items]) => (
            <section key={proj}>
              <header className="mb-3 flex items-baseline gap-3 border-b border-[var(--color-line)] pb-2">
                <h2 className="font-display italic text-[26px] tracking-[-0.005em] text-[var(--color-text)]">
                  {proj}
                </h2>
                <span className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-muted)]">
                  {items.length} {items.length === 1 ? "item" : "items"}
                </span>
              </header>
              <ul className="space-y-3">
                {items.map((row) => (
                  <FeedbackRow
                    key={row.run_id}
                    row={row}
                    onCopy={copyIterateCmd}
                    copied={copiedFor === row.run_id}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}

function FeedbackRow({
  row, onCopy, copied,
}: {
  row: FeedbackIndexRow;
  onCopy: (id: string) => void;
  copied: boolean;
}) {
  const parsed = parseRunId(row.run_id);
  const statusBadge = {
    open:      "bg-[var(--color-saffron)]/15 text-[var(--color-saffron)]",
    fulfilled: "bg-[var(--color-emerald)]/15 text-[var(--color-emerald)]",
    wontfix:   "bg-[var(--color-line-2)] text-[var(--color-muted)]",
  }[row.feedback_status as "open" | "fulfilled" | "wontfix"] ?? "bg-[var(--color-line)] text-[var(--color-muted)]";

  return (
    <li className="overflow-hidden rounded-md border border-[var(--color-line)] bg-[var(--color-surface)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2.5">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className={`rounded px-2 py-0.5 text-[11px] uppercase tracking-[0.08em] ${statusBadge}`}>
            {row.feedback_status}
          </span>
          <Link
            to={`/runs/${encodeURIComponent(row.run_id)}`}
            className="font-mono text-[12px] text-[var(--color-forge)] hover:underline"
          >
            {row.run_id}
          </Link>
          <span className="text-[12px] text-[var(--color-muted)]">{row.pipeline}</span>
          <span className="text-[12px] text-[var(--color-muted)]">config: {row.config_id || "default"}</span>
          <span className="text-[12px] text-[var(--color-faint)]">
            {parsed?.ts ?? fmtTime(row.updated_at)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onCopy(row.run_id)}
            className="rounded-md border border-[var(--color-line-2)] px-3 py-1.5 text-[12.5px] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
          >
            {copied ? "Copied!" : `Copy /iterate ${row.run_id.slice(0, 8)}…`}
          </button>
        </div>
      </header>
      <p className="whitespace-pre-wrap p-4 text-[13.5px] leading-relaxed text-[var(--color-text)]">
        {row.body}
      </p>
      {row.addressed_in_run && (
        <footer className="border-t border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2 text-[12px] text-[var(--color-text-2)]">
          <span className="text-[var(--color-emerald)]">addressed</span> by{" "}
          <Link
            to={`/runs/${encodeURIComponent(row.addressed_in_run)}`}
            className="font-mono text-[12px] text-[var(--color-forge)] hover:underline"
          >
            {row.addressed_in_run}
          </Link>
          {row.addressed_by_config && (
            <span className="ml-2 text-[var(--color-muted)]">
              · config <code className="font-mono text-[11.5px]">{row.addressed_by_config}</code>
            </span>
          )}
        </footer>
      )}
    </li>
  );
}
