import { useEffect, useState } from "react";
import { api, type Pipeline, type PipelineInput } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";

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
        eyebrow="The forge"
        title="Pipelines."
        subtitle="A pipeline declares its inputs, its outputs, and a few named configs you can A/B. Adding a new one is one PipelineSpec entry plus a workflow class — same UI, same CLI, no plumbing."
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

      <AddPipelinePanel />
    </section>
  );
}

function PipelineCard({ p }: { p: Pipeline }) {
  return (
    <article className="relative overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-7 transition-colors hover:border-[var(--color-line-2)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display italic text-[34px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
            {p.name}
          </h2>
          <div className="mt-1 font-mono text-[12.5px] text-[var(--color-muted)]">{p.id}</div>
        </div>
      </div>

      <p className="mt-5 max-w-[60ch] text-[15px] leading-relaxed text-[var(--color-text-2)]">{p.description}</p>

      <div className="mt-6 grid grid-cols-1 gap-5 border-t border-[var(--color-line)] pt-5 sm:grid-cols-2">
        <div>
          <div className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-muted)]">Inputs</div>
          <ul className="mt-2.5 space-y-2">
            {p.inputs.length === 0
              ? <li className="text-[13.5px] text-[var(--color-faint)]">just a project</li>
              : p.inputs.map((i) => <InputRow key={i.id} i={i} />)}
          </ul>
        </div>
        <div>
          <div className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-muted)]">Outputs</div>
          <ul className="mt-2.5 space-y-1 font-mono text-[12.5px] text-[var(--color-text-2)]">
            {p.outputs.slice(0, 6).map((f) => <li key={f}>{f}</li>)}
          </ul>
        </div>
      </div>

      <div className="mt-6 border-t border-[var(--color-line)] pt-5">
        <div className="text-[12px] uppercase tracking-[0.08em] text-[var(--color-muted)]">Configs · {p.configs.length}</div>
        <ul className="mt-2.5 space-y-2">
          {p.configs.map((c) => (
            <li key={c.id} className="flex items-baseline gap-3 text-[14px]">
              <span className="font-mono text-[12.5px] text-[var(--color-forge)]">{c.id}</span>
              <span className="text-[var(--color-text-2)]">{c.description}</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

function InputRow({ i }: { i: PipelineInput }) {
  return (
    <li className="flex items-baseline gap-3 text-[14px]">
      <span className="shrink-0">
        <Pill tone={i.required ? "forge" : "default"}>{i.id}</Pill>
      </span>
      <span className="min-w-0 text-[var(--color-text-2)]">{i.description}</span>
    </li>
  );
}

function AddPipelinePanel() {
  return (
    <section className="mt-14 overflow-hidden rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-line)] px-7 py-4">
        <div className="text-[12px] uppercase tracking-[0.1em] text-[var(--color-muted)]">Vibe-coding a new pipeline</div>
        <h2 className="mt-1.5 font-display italic text-[26px] tracking-[-0.01em] text-[var(--color-text)]">
          Three edits and you're shipped.
        </h2>
      </div>
      <ol className="grid grid-cols-1 divide-[var(--color-line)] md:grid-cols-3 md:divide-x">
        <Step
          n="1"
          title="Declare it."
          body="Add a PipelineSpec to PIPELINES with a name, description, inputs, outputs, and at least one config preset."
          path="src/adforge/pipelines/__init__.py"
        />
        <Step
          n="2"
          title="Write the workflow."
          body="Drop a Temporal workflow next to it. Each step is a workflow.execute_activity call — atomic, retryable, observable in Temporal Web."
          path="src/adforge/pipelines/<your_pipeline>.py"
        />
        <Step
          n="3"
          title="Branch on config_id."
          body="Inside an activity, switch on inp.config_id to swap models / prompts / behavior. New presets = new rows in the registry, not new code paths."
          path="src/adforge/activities/<step>.py"
        />
      </ol>
      <div className="border-t border-[var(--color-line)] bg-[var(--color-surface-2)] px-7 py-4 text-[13.5px] text-[var(--color-text-2)]">
        The CLI, API, and UI all read from the registry — your pipeline appears everywhere as soon as you save.
      </div>
    </section>
  );
}

function Step({ n, title, body, path }: { n: string; title: string; body: string; path: string }) {
  return (
    <div className="px-7 py-6">
      <div className="flex items-baseline gap-3">
        <span className="font-display italic text-[36px] leading-none text-[var(--color-forge)]/70">{n}</span>
        <h3 className="font-display italic text-[20px] tracking-[-0.005em] text-[var(--color-text)]">{title}</h3>
      </div>
      <p className="mt-3 text-[14px] leading-relaxed text-[var(--color-text-2)]">{body}</p>
      <div className="mt-3 break-all font-mono text-[11.5px] text-[var(--color-muted)]">{path}</div>
    </div>
  );
}
