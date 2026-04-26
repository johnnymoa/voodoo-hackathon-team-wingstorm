import { useEffect, useMemo, useState } from "react";
import { api, type Pipeline } from "../lib/api";
import { PageHeader } from "../components/Layout";

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

  const grouped = useMemo(() => groupByOutput(list ?? []), [list]);

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="The forge"
        title="Pipelines."
        subtitle="One pipeline per output type. A config is just a knob preset on the same code path."
      />

      {err && (
        <div className="rounded border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {list && (
        <div className="overflow-hidden rounded-md border border-[var(--color-line)] bg-[var(--color-surface)]">
          {grouped.map((g) => (
            <PipelineGroup key={g.kind} kind={g.kind} pipelines={g.pipelines} />
          ))}
        </div>
      )}
    </section>
  );
}

const KIND_LABEL: Record<string, string> = {
  video:    "Video ad",
  playable: "Playable HTML",
  asset:    "Asset",
};

function groupByOutput(list: Pipeline[]): { kind: string; pipelines: Pipeline[] }[] {
  const PRIORITY = ["video", "playable", "asset"];
  const map = new Map<string, Pipeline[]>();
  for (const p of list) {
    const k = p.output_kind || "asset";
    map.set(k, [...(map.get(k) ?? []), p]);
  }
  const out: { kind: string; pipelines: Pipeline[] }[] = [];
  for (const k of PRIORITY) if (map.has(k)) { out.push({ kind: k, pipelines: map.get(k)! }); map.delete(k); }
  for (const [k, pipelines] of map) out.push({ kind: k, pipelines });
  return out;
}

function PipelineGroup({ kind, pipelines }: { kind: string; pipelines: Pipeline[] }) {
  return (
    <section>
      <header className="border-b border-[var(--color-line)] bg-[var(--color-surface-2)] px-6 py-3 text-[12px] uppercase tracking-[0.08em] text-[var(--color-muted)]">
        {KIND_LABEL[kind] ?? kind} · {pipelines.length}
      </header>
      <ul className="divide-y divide-[var(--color-line)]">
        {pipelines.map((p) => <PipelineRow key={p.id} p={p} />)}
      </ul>
    </section>
  );
}

function PipelineRow({ p }: { p: Pipeline }) {
  const inputSummary = p.inputs.length === 0
    ? "no inputs needed"
    : p.inputs.map((i) => i.id + (i.required ? "" : "?")).join(" · ");

  return (
    <li className="px-6 py-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="min-w-0">
          <h3 className="text-[18px] font-medium tracking-[-0.005em] text-[var(--color-text)]">{p.name}</h3>
          <div className="mt-0.5 font-mono text-[12px] text-[var(--color-faint)]">{p.id}</div>
        </div>
        <div className="font-mono text-[12px] text-[var(--color-muted)]">
          inputs: <span className="text-[var(--color-text-2)]">{inputSummary}</span>
        </div>
      </div>

      <p className="mt-2 max-w-[80ch] text-[13.5px] leading-relaxed text-[var(--color-text-2)]">
        {p.description}
      </p>

      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[13px]">
        {p.configs.map((c) => (
          <li key={c.id} className="flex items-baseline gap-2">
            <span className="font-mono text-[12px] text-[var(--color-forge)]">{c.id}</span>
            <span className="text-[var(--color-text-2)]">{c.description}</span>
          </li>
        ))}
      </ul>
    </li>
  );
}
