import { useEffect, useState } from "react";
import { api, type Pipeline } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";

const TRACK_LABEL: Record<Pipeline["track"], string> = {
  "track-2": "Track 2 · Playable",
  "track-3": "Track 3 · Video Ad",
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
        eyebrow="Pipelines"
        title="Recipes the forge runs."
        subtitle="Each pipeline takes a project and produces a run. Configs are named presets you can A/B as you iterate."
      />

      {err && (
        <div className="rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {list && (
        <div className="stagger grid grid-cols-1 gap-5 lg:grid-cols-2">
          {list.map((p) => <PipelineCard key={p.id} p={p} />)}
        </div>
      )}
    </section>
  );
}

function PipelineCard({ p }: { p: Pipeline }) {
  return (
    <article className="relative overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-7 transition-colors hover:border-[var(--color-line-2)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[12px] uppercase tracking-[0.1em] text-[var(--color-muted)]">{TRACK_LABEL[p.track]}</div>
          <h2 className="mt-1.5 font-display italic text-[34px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
            {p.name}
          </h2>
          <div className="mt-1 font-mono text-[12px] text-[var(--color-muted)]">{p.id}</div>
        </div>
        <span className="font-display italic text-[48px] leading-none text-[var(--color-forge)]/60">{p.glyph}</span>
      </div>

      <p className="mt-5 max-w-[60ch] text-[14.5px] leading-relaxed text-[var(--color-text-2)]">{p.tagline}</p>

      <div className="mt-6 grid grid-cols-2 gap-6 border-t border-[var(--color-line)] pt-5">
        <div>
          <div className="text-[12px] text-[var(--color-muted)]">Needs</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {p.needs.length === 0
              ? <span className="text-[13px] text-[var(--color-faint)]">just a project</span>
              : p.needs.map((n) => <Pill key={n} tone="forge">{n}</Pill>)}
          </div>
        </div>
        <div>
          <div className="text-[12px] text-[var(--color-muted)]">Produces</div>
          <ul className="mt-2 space-y-0.5 font-mono text-[12px] text-[var(--color-text-2)]">
            {p.produces.slice(0, 5).map((f) => <li key={f}>{f}</li>)}
          </ul>
        </div>
      </div>

      <div className="mt-6 border-t border-[var(--color-line)] pt-5">
        <div className="text-[12px] text-[var(--color-muted)]">Configs · {p.configs.length}</div>
        <ul className="mt-2 space-y-1.5">
          {p.configs.map((c) => (
            <li key={c.id} className="flex items-baseline gap-3 text-[13.5px]">
              <span className="font-mono text-[12px] text-[var(--color-forge)]">{c.id}</span>
              <span className="text-[var(--color-text-2)]">{c.description}</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
