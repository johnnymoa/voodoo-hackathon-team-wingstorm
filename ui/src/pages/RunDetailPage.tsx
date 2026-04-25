import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Artifact, type RunManifest } from "../lib/api";
import { fmtBytes, fmtDuration, fmtTime, parseRunId } from "../lib/format";
import { Pill, StatusPill } from "../components/Pill";
import { Mono } from "../components/Mono";
import { ArtifactView } from "../components/ArtifactView";

export default function RunDetailPage() {
  const { runId = "" } = useParams();
  const [m, setM] = useState<RunManifest | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.run(runId)
      .then((res) => {
        if (cancelled) return;
        setM(res);
        setActive(pickPrimary(res.artifacts)?.name ?? null);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, [runId]);

  const parsed = useMemo(() => parseRunId(runId), [runId]);

  if (err) {
    return (
      <section className="page-in">
        <Link to="/runs" className="text-[13px] text-[var(--color-muted)] hover:text-[var(--color-forge)]">← back to runs</Link>
        <div className="mt-6 rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      </section>
    );
  }

  if (!m) {
    return <section className="page-in"><div className="text-[14px] text-[var(--color-muted)]">loading run…</div></section>;
  }

  const activeArtifact = m.artifacts.find((a) => a.name === active) ?? null;

  return (
    <section className="page-in">
      {/* Breadcrumb */}
      <div className="mb-4 text-[13px] text-[var(--color-muted)]">
        <Link to="/runs" className="hover:text-[var(--color-forge)]">Runs</Link>
        <span className="mx-2 text-[var(--color-faint)]">/</span>
        <span className="font-mono text-[12.5px] text-[var(--color-text-2)]">{m.run_id}</span>
      </div>

      {/* Header */}
      <header className="mb-10 grid grid-cols-1 gap-8 border-b border-[var(--color-line)] pb-8 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <StatusPill status={m.status} />
            <Pill tone="forge">{m.pipeline}</Pill>
            <Pill>config · {m.config_id || "default"}</Pill>
            <Link to={`/projects/${encodeURIComponent(m.project_id)}`}>
              <Pill className="hover:border-[var(--color-forge)] hover:text-[var(--color-forge)] cursor-pointer">
                project · {m.project_id}
              </Pill>
            </Link>
          </div>
          <h1 className="font-display italic text-[44px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
            {m.project_id}
            <span className="mx-3 text-[var(--color-forge)]/70 not-italic">·</span>
            <span className="text-[var(--color-text-2)]">{parsed?.ts ?? fmtTime(m.started_at)}</span>
          </h1>
          <div className="mt-2"><Mono value={m.run_id} /></div>
        </div>
        <div className="grid grid-cols-3 gap-5 self-end text-[13px]">
          <Stat label="started"   value={fmtTime(m.started_at)} />
          <Stat label="completed" value={fmtTime(m.completed_at)} />
          <Stat label="duration"  value={fmtDuration(m.started_at, m.completed_at)} accent />
          <a
            href={api.temporalUrl(m.run_id)}
            target="_blank"
            rel="noreferrer"
            className="col-span-3 mt-2 flex items-center justify-between rounded-md border border-[var(--color-line-2)] px-4 py-2 text-[12.5px] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
          >
            <span>View in Temporal</span><span aria-hidden>↗</span>
          </a>
        </div>
      </header>

      {/* Body: artifacts list + viewer */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
        <ArtifactList
          artifacts={m.artifacts}
          activeName={active}
          onSelect={setActive}
        />
        <div className="min-w-0">
          {activeArtifact ? (
            <ArtifactView runId={m.run_id} artifact={activeArtifact} />
          ) : (
            <div className="rounded-md border border-[var(--color-line)] bg-[var(--color-surface)] p-10 text-center text-[14px] text-[var(--color-muted)]">
              no artifact selected.
            </div>
          )}
        </div>
      </div>

      {/* Params */}
      <details className="mt-10 overflow-hidden rounded-md border border-[var(--color-line)] bg-[var(--color-surface)]">
        <summary className="cursor-pointer select-none border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[13px] text-[var(--color-muted)] hover:text-[var(--color-text)]">
          Params used for this run
        </summary>
        <pre className="overflow-auto p-6 text-[12.5px] leading-relaxed text-[var(--color-text-2)] font-mono">
          {JSON.stringify(m.params, null, 2)}
        </pre>
      </details>
    </section>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[11.5px] text-[var(--color-muted)]">{label}</div>
      <div className={`mt-1 ${accent ? "text-[var(--color-forge)]" : "text-[var(--color-text)]"}`}>
        {value}
      </div>
    </div>
  );
}

function ArtifactList({
  artifacts, activeName, onSelect,
}: {
  artifacts: Artifact[];
  activeName: string | null;
  onSelect: (name: string) => void;
}) {
  const grouped = useMemo(() => groupArtifacts(artifacts), [artifacts]);

  return (
    <aside className="overflow-hidden rounded-md border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[12.5px] text-[var(--color-muted)]">
        Artifacts · {artifacts.length}
      </div>

      <ul>
        {grouped.map(({ kind, items }) => (
          <li key={kind}>
            <div className="px-5 pt-4 pb-1.5 text-[11px] uppercase tracking-[0.08em] text-[var(--color-faint)]">
              {KIND_LABEL[kind] ?? kind}
            </div>
            {items.map((a) => {
              const active = a.name === activeName;
              return (
                <button
                  key={a.name}
                  onClick={() => onSelect(a.name)}
                  className={`row-hairline group flex w-full items-center justify-between gap-2 px-5 py-2.5 text-left text-[13.5px] transition-colors ${
                    active
                      ? "bg-[var(--color-canvas)] text-[var(--color-forge)]"
                      : "text-[var(--color-text-2)] hover:text-[var(--color-text)]"
                  }`}
                >
                  <span className="truncate">{a.name}</span>
                  <span className="shrink-0 text-[11.5px] text-[var(--color-faint)]">{fmtBytes(a.size_bytes)}</span>
                </button>
              );
            })}
          </li>
        ))}
      </ul>
    </aside>
  );
}

const KIND_LABEL: Record<string, string> = {
  html: "Playable",
  md:   "Documents",
  json: "Data",
  txt:  "Prompts",
  png:  "Images",
  jpg:  "Images",
  jpeg: "Images",
  webp: "Images",
};

function groupArtifacts(arts: Artifact[]): { kind: string; items: Artifact[] }[] {
  const PRIORITY = ["html", "md", "txt", "json", "png", "jpg", "jpeg", "webp", "svg"];
  const map = new Map<string, Artifact[]>();
  for (const a of arts) {
    const k = a.kind || "bin";
    map.set(k, [...(map.get(k) ?? []), a]);
  }
  const ordered: { kind: string; items: Artifact[] }[] = [];
  for (const k of PRIORITY) if (map.has(k)) { ordered.push({ kind: k, items: map.get(k)! }); map.delete(k); }
  for (const [k, items] of map) ordered.push({ kind: k, items });
  return ordered;
}

function pickPrimary(arts: Artifact[]): Artifact | null {
  const ORDER = ["html", "md", "txt", "json", "png"];
  for (const k of ORDER) {
    const hit = arts.find((a) => a.kind === k);
    if (hit) return hit;
  }
  return arts[0] ?? null;
}
