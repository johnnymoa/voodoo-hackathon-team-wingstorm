import { useEffect, useState } from "react";
import { api, type Pipeline } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";

const TRACK_LABEL: Record<Pipeline["track"], string> = {
  "track-2": "Track 2 · Playable",
  "track-3": "Track 3 · Intelligence",
  "merged":  "Merged · Killer demo",
};

export default function PipelinesPage() {
  const [list, setList] = useState<Pipeline[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.pipelines()
      .then((r) => !cancelled && setList(r))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-in">
      <PageHeader
        index="03"
        eyebrow="recipes the forge knows"
        title="Pipelines"
        accent={list ? `${list.length.toString().padStart(2, "0")} available` : undefined}
      />

      {err && (
        <div className="border border-[var(--color-rust)]/60 bg-[var(--color-rust)]/5 p-4 text-[12px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {list && (
        <div className="stagger grid grid-cols-1 gap-5 lg:grid-cols-3">
          {list.map((p) => <PipelineCard key={p.id} p={p} />)}
        </div>
      )}
    </section>
  );
}

function PipelineCard({ p }: { p: Pipeline }) {
  const copyCmd = async () => {
    try { await navigator.clipboard.writeText(p.cli.replace("<id>", "castle_clashers")); } catch { /* ignore */ }
  };

  return (
    <article className="group relative flex h-full flex-col overflow-hidden border border-[var(--color-line)] bg-[var(--color-surface)] p-6 transition-colors hover:border-[var(--color-line-2)]">
      <span className="absolute inset-x-0 top-0 h-px bg-[var(--color-forge)] opacity-0 transition-opacity group-hover:opacity-100" />

      {/* Glyph + eyebrow */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">
            {TRACK_LABEL[p.track]}
          </div>
          <h2 className="mt-1 font-display italic text-[28px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
            {p.name}
          </h2>
          <div className="mt-1 font-mono text-[11.5px] text-[var(--color-faint)]">{p.id}</div>
        </div>
        <div className="font-display italic text-[44px] leading-none text-[var(--color-forge)] opacity-30 group-hover:opacity-90 transition-opacity">
          {p.glyph}
        </div>
      </div>

      <p className="mt-4 text-[13px] leading-relaxed text-[var(--color-text-2)]">{p.tagline}</p>

      {/* Needs / Produces */}
      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-[var(--color-line)] pt-4">
        <div>
          <div className="text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">needs</div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {p.needs.length === 0 ? (
              <span className="text-[12px] text-[var(--color-faint)]">— just a target</span>
            ) : (
              p.needs.map((n) => <Pill key={n} tone="forge">{n}</Pill>)
            )}
          </div>
        </div>
        <div>
          <div className="text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">produces</div>
          <ul className="mt-1.5 space-y-0.5 font-mono text-[11px] text-[var(--color-text-2)]">
            {p.produces.slice(0, 5).map((f) => <li key={f}>· {f}</li>)}
          </ul>
        </div>
      </div>

      {/* CLI */}
      <button
        onClick={copyCmd}
        title="copy command"
        className="mt-auto pt-5 text-left"
      >
        <div className="text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">cli ⧉</div>
        <div className="mt-1 break-all border border-[var(--color-line)] bg-[var(--color-canvas)] px-3 py-2 font-mono text-[11.5px] text-[var(--color-text)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)] transition-colors">
          {p.cli.replace("<id>", "castle_clashers")}
        </div>
      </button>
    </article>
  );
}
