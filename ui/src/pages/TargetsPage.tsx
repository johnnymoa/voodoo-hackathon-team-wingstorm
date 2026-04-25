import { useEffect, useState } from "react";
import { api, type Target } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";
import { EmptyState } from "../components/EmptyState";

export default function TargetsPage() {
  const [list, setList] = useState<Target[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.targets()
      .then((r) => !cancelled && setList(r))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-in">
      <PageHeader
        index="02"
        eyebrow="reusable input bundles"
        title="Targets"
        accent={list ? `${list.length.toString().padStart(2, "0")} on disk` : undefined}
      />

      {err && (
        <div className="border border-[var(--color-rust)]/60 bg-[var(--color-rust)]/5 p-4 text-[12px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {list && list.length === 0 && !err && (
        <EmptyState
          title="No targets yet."
          body="Add a target by creating targets/<id>/ with a target.json. Drop in video.mp4 and assets/ if the pipeline needs them."
        />
      )}

      {list && list.length > 0 && (
        <div className="stagger grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {list.map((t) => <TargetCard key={t.id} t={t} />)}
        </div>
      )}
    </section>
  );
}

function TargetCard({ t }: { t: Target }) {
  return (
    <article className="group relative overflow-hidden border border-[var(--color-line)] bg-[var(--color-surface)] p-5 transition-colors hover:border-[var(--color-line-2)]">
      <div className="absolute inset-x-0 top-0 h-px bg-[var(--color-forge)] opacity-0 transition-opacity group-hover:opacity-100" />

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">target</div>
          <h3 className="mt-1 font-display italic text-[24px] leading-tight tracking-[-0.01em] text-[var(--color-text)]">
            {t.name}
          </h3>
          <div className="mt-1 font-mono text-[11.5px] text-[var(--color-faint)]">{t.id}</div>
        </div>
        <div className="shrink-0 text-[var(--color-forge)] text-[28px] font-display italic leading-none opacity-30 group-hover:opacity-90 transition-opacity">
          §
        </div>
      </div>

      {t.notes && (
        <p className="mt-4 border-l-2 border-[var(--color-line-2)] pl-3 text-[12px] leading-relaxed text-[var(--color-text-2)]">
          {t.notes}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Pill tone={t.has_video ? "emerald" : "muted"}>
          {t.has_video ? "✓" : "—"} video
        </Pill>
        <Pill tone={t.has_assets ? "emerald" : "muted"}>
          {t.has_assets ? "✓" : "—"} assets
        </Pill>
      </div>

      <div className="mt-5 flex items-center gap-2 border-t border-[var(--color-line)] pt-4 text-[10.5px] uppercase tracking-[0.14em]">
        <CopyCmd cmd={`uv run adforge run creative --target ${t.id}`} label="creative" enabled />
        <CopyCmd cmd={`uv run adforge run playable --target ${t.id}`} label="playable" enabled={t.has_video} />
        <CopyCmd cmd={`uv run adforge run full --target ${t.id}`}     label="full"     enabled={t.has_video} />
      </div>
    </article>
  );
}

function CopyCmd({ cmd, label, enabled }: { cmd: string; label: string; enabled: boolean }) {
  const handle = async () => {
    if (!enabled) return;
    try { await navigator.clipboard.writeText(cmd); } catch { /* ignore */ }
  };
  return (
    <button
      onClick={handle}
      disabled={!enabled}
      title={enabled ? `copy: ${cmd}` : "missing video"}
      className={`flex-1 truncate border px-2 py-1.5 transition-colors ${
        enabled
          ? "border-[var(--color-line-2)] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
          : "border-[var(--color-line)] text-[var(--color-faint)] cursor-not-allowed"
      }`}
    >
      copy ⧉ {label}
    </button>
  );
}
