import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Artifact, type RunManifest } from "../lib/api";
import { fmtBytes, fmtDuration, fmtTime, parseRunId, pipelineGlyph } from "../lib/format";
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
        <Link to="/runs" className="text-[11px] uppercase tracking-[0.16em] text-[var(--color-muted)] hover:text-[var(--color-forge)]">
          ← back to runs
        </Link>
        <div className="mt-6 border border-[var(--color-rust)]/60 bg-[var(--color-rust)]/5 p-4 text-[12px] text-[var(--color-rust)]">
          could not load run: {err}
        </div>
      </section>
    );
  }

  if (!m) {
    return (
      <section className="page-in">
        <div className="text-[12px] text-[var(--color-muted)]">loading run…</div>
      </section>
    );
  }

  const activeArtifact = m.artifacts.find((a) => a.name === active) ?? null;

  return (
    <section className="page-in">
      {/* Breadcrumb */}
      <div className="mb-5 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-[var(--color-muted)]">
        <Link to="/runs" className="hover:text-[var(--color-forge)]">runs</Link>
        <span className="text-[var(--color-faint)]">/</span>
        <span className="truncate text-[var(--color-text-2)] normal-case tracking-normal font-mono text-[12px]">{m.run_id}</span>
      </div>

      {/* Header */}
      <header className="mb-8 grid grid-cols-1 gap-6 border-b border-[var(--color-line)] pb-8 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <StatusPill status={m.status} />
            <Pill tone="forge">
              <span>{pipelineGlyph(m.pipeline)}</span>
              {m.pipeline}
            </Pill>
            <Pill>target · {m.target_id}</Pill>
            <Pill tone="muted">{m.artifacts.length} artifact{m.artifacts.length === 1 ? "" : "s"}</Pill>
          </div>
          <h1 className="font-display italic text-[40px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
            {parsed?.target ?? m.target_id}
            <span className="ml-3 text-[var(--color-forge)] not-italic">·</span>
            <span className="ml-2 italic text-[var(--color-text-2)]">{parsed?.ts ?? fmtTime(m.started_at)}</span>
          </h1>
          <div className="mt-2">
            <Mono value={m.run_id} />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 lg:gap-6 self-end text-[11px]">
          <Stat label="started"   value={fmtTime(m.started_at)} />
          <Stat label="completed" value={fmtTime(m.completed_at)} />
          <Stat label="duration"  value={fmtDuration(m.started_at, m.completed_at)} accent />
          <a
            href={api.temporalUrl(m.run_id)}
            target="_blank"
            rel="noreferrer"
            className="col-span-3 mt-2 flex items-center justify-between border border-[var(--color-line-2)] px-3 py-2 text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
          >
            <span>view in temporal</span>
            <span>↗</span>
          </a>
        </div>
      </header>

      {/* Body: 2-col, artifacts list + viewer */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <ArtifactList
          artifacts={m.artifacts}
          children={m.children}
          activeName={active}
          onSelect={setActive}
        />
        <div className="min-w-0">
          {activeArtifact ? (
            <ArtifactView runId={m.run_id} artifact={activeArtifact} />
          ) : (
            <div className="border border-[var(--color-line)] bg-[var(--color-surface)] p-10 text-center text-[12px] text-[var(--color-muted)]">
              no artifact selected.
            </div>
          )}
        </div>
      </div>

      {/* Params block */}
      <details className="mt-8 border border-[var(--color-line)] bg-[var(--color-surface)]">
        <summary className="cursor-pointer select-none border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2 text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)] hover:text-[var(--color-text)]">
          params
        </summary>
        <pre className="overflow-auto p-6 text-[12px] leading-relaxed text-[var(--color-text-2)]">
          {JSON.stringify(m.params, null, 2)}
        </pre>
      </details>
    </section>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.16em] text-[var(--color-muted)]">{label}</div>
      <div className={`mt-1 text-[13px] ${accent ? "text-[var(--color-forge)]" : "text-[var(--color-text)]"}`}>
        {value}
      </div>
    </div>
  );
}

function ArtifactList({
  artifacts, children, activeName, onSelect,
}: {
  artifacts: Artifact[];
  children: string[];
  activeName: string | null;
  onSelect: (name: string) => void;
}) {
  const grouped = useMemo(() => groupArtifacts(artifacts), [artifacts]);

  return (
    <aside className="border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-4 py-2 text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)]">
        artifacts · {artifacts.length}
      </div>

      <ul className="stagger">
        {grouped.map(({ kind, items }) => (
          <li key={kind}>
            <div className="px-4 pt-3 pb-1 text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-faint)]">
              {KIND_LABEL[kind] ?? kind}
            </div>
            {items.map((a) => {
              const active = a.name === activeName;
              return (
                <button
                  key={a.name}
                  onClick={() => onSelect(a.name)}
                  className={`row-hairline group flex w-full items-center justify-between gap-2 px-4 py-2 text-left text-[12px] transition-colors ${
                    active
                      ? "bg-[var(--color-canvas)] text-[var(--color-forge)]"
                      : "text-[var(--color-text-2)] hover:text-[var(--color-text)]"
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`size-[5px] shrink-0 rounded-full ${active ? "bg-[var(--color-forge)]" : "bg-[var(--color-faint)]"}`} />
                    <span className="truncate">{a.name}</span>
                  </span>
                  <span className="shrink-0 text-[10px] text-[var(--color-faint)]">{fmtBytes(a.size_bytes)}</span>
                </button>
              );
            })}
          </li>
        ))}
      </ul>

      {children.length > 0 && (
        <div className="border-t border-[var(--color-line)]">
          <div className="px-4 pt-3 pb-1 text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-faint)]">
            children
          </div>
          {children.map((rid) => (
            <Link
              key={rid}
              to={`/runs/${encodeURIComponent(rid)}`}
              className="row-hairline flex items-center justify-between gap-2 px-4 py-2 text-[12px] text-[var(--color-text-2)] hover:text-[var(--color-forge)]"
            >
              <span className="truncate font-mono">{rid}</span>
              <span className="text-[var(--color-faint)]">→</span>
            </Link>
          ))}
        </div>
      )}
    </aside>
  );
}

const KIND_LABEL: Record<string, string> = {
  html: "playable",
  md:   "documents",
  json: "data",
  txt:  "prompts",
  png:  "images",
  jpg:  "images",
  jpeg: "images",
  webp: "images",
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
