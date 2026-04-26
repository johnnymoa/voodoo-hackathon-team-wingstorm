import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Artifact, type Feedback, type FeedbackStatus, type RunManifest } from "../lib/api";
import { fmtBytes, fmtDuration, fmtTime, parseRunId } from "../lib/format";
import { Pill, StatusPill } from "../components/Pill";
import { ArtifactView } from "../components/ArtifactView";

export default function RunDetailPage() {
  const { runId = "" } = useParams();
  const [m, setM] = useState<RunManifest | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = () => {
      api.run(runId)
        .then((res) => {
          if (cancelled) return;
          setM(res);
          setErr(null);
          setActive((cur) => cur ?? pickPrimary(res.artifacts)?.name ?? null);
          // Keep polling while the output is still being created.
          if (res.status === "running") {
            timer = setTimeout(tick, 2500);
          }
        })
        .catch((e) => {
          if (cancelled) return;
          // Right after start_run the summary may not exist for a beat.
          // Retry a few times before surfacing an error.
          setErr(String(e));
          timer = setTimeout(tick, 2500);
        });
    };
    tick();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [runId]);

  const parsed = useMemo(() => parseRunId(runId), [runId]);

  if (err && !m) {
    return (
      <section className="page-in">
        <Link to="/runs" className="text-[13px] text-[var(--color-muted)] hover:text-[var(--color-rust)]">back to history</Link>
        <div className="mt-6 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] p-6 text-[14px] text-[var(--color-text-2)]">
          waiting for the output to appear...
          <div className="mt-2 text-[12px] text-[var(--color-muted)]">{err}</div>
        </div>
      </section>
    );
  }

  if (!m) {
    return <section className="page-in"><div className="text-[14px] text-[var(--color-muted)]">loading output...</div></section>;
  }

  const activeArtifact = m.artifacts.find((a) => a.name === active) ?? null;

  return (
    <section className="page-in">
      <div className="mb-4 text-[13px] text-[var(--color-muted)]">
        <Link to="/runs" className="hover:text-[var(--color-rust)]">history</Link>
        <span className="mx-2 text-[var(--color-faint)]">/</span>
        <span className="text-[12.5px] text-[var(--color-text-2)]">{parsed?.ts ?? fmtTime(m.started_at)}</span>
      </div>

      <header className="mb-10 grid grid-cols-1 gap-8 border-b-[3px] border-[var(--color-line)] pb-8 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <StatusPill status={m.status} />
            <Pill tone="forge">{friendlyPipeline(m.pipeline)}</Pill>
            <Pill>style · {m.config_id || "default"}</Pill>
            <Link to={`/projects/${encodeURIComponent(m.project_id)}`}>
              <Pill className="cursor-pointer hover:bg-[var(--color-saffron)]">
                {m.project_id}
              </Pill>
            </Link>
          </div>
          <h1 className="font-display text-[48px] font-bold leading-[1.05] tracking-[-0.03em] text-[var(--color-text)]">
            {m.project_id}
            <span className="mx-3 text-[var(--color-rust)]">·</span>
            <span className="text-[var(--color-text-2)]">{parsed?.ts ?? fmtTime(m.started_at)}</span>
          </h1>
        </div>
        <div className="grid grid-cols-3 gap-5 self-end text-[13px]">
          <Stat label="started"   value={fmtTime(m.started_at)} />
          <Stat label="completed" value={fmtTime(m.completed_at)} />
          <Stat label="duration"  value={fmtDuration(m.started_at, m.completed_at)} accent />
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[300px_1fr]">
        <ArtifactList
          artifacts={m.artifacts}
          activeName={active}
          onSelect={setActive}
        />
        <div className="min-w-0">
          {activeArtifact ? (
            <ArtifactView runId={m.run_id} artifact={activeArtifact} />
          ) : m.status === "running" ? (
            <div className="rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] p-10 text-center">
              <div className="mx-auto mb-3 size-2 rounded-full bg-[var(--color-saffron)] pulse-dot" />
              <div className="text-[15px] text-[var(--color-text)]">making it...</div>
              <div className="mt-1 text-[13px] text-[var(--color-text-2)]">
                files will appear here as soon as they are ready.
              </div>
            </div>
          ) : (
            <div className="rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] p-10 text-center text-[14px] text-[var(--color-muted)]">
              no file selected.
            </div>
          )}
        </div>
      </div>

      <FeedbackPanel runId={m.run_id} />

      <details className="mt-10 overflow-hidden rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
        <summary className="cursor-pointer select-none border-b-[3px] border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[13px] text-[var(--color-muted)] hover:text-[var(--color-text)]">
          details used to make this
        </summary>
        <pre className="overflow-auto p-6 text-[12.5px] leading-relaxed text-[var(--color-text-2)]">
          {JSON.stringify(m.params, null, 2)}
        </pre>
      </details>
    </section>
  );
}

const STATUS_TONE: Record<FeedbackStatus, "saffron" | "emerald" | "muted"> = {
  open: "saffron",
  fulfilled: "emerald",
  wontfix: "muted",
};

function FeedbackPanel({ runId }: { runId: string }) {
  const [fb, setFb] = useState<Feedback | null>(null);
  const [body, setBody] = useState("");
  const [status, setStatus] = useState<FeedbackStatus>("open");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getFeedback(runId)
      .then((res) => {
        if (cancelled) return;
        setFb(res);
        setBody(res.body);
        setStatus((res.status as FeedbackStatus) || "open");
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, [runId]);

  const onSave = async () => {
    setBusy(true);
    setErr(null);
    try {
      const res = await api.saveFeedback(runId, body, status);
      setFb(res);
      setSaved(res.updated_at);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  };

  const dirty = fb !== null && (body !== fb.body || status !== fb.status);

  return (
    <section className="mt-12 overflow-hidden rounded-xl border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
      <header className="flex items-center justify-between gap-4 border-b-[3px] border-[var(--color-line)] px-6 py-4">
        <div>
          <div className="text-[12px] font-bold tracking-[0.1em] text-[var(--color-muted)]">feedback</div>
          <h2 className="mt-1 font-display text-[26px] font-bold tracking-[-0.02em] text-[var(--color-text)]">
            notes for the next version
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {fb && fb.exists && <Pill tone={STATUS_TONE[status as FeedbackStatus] ?? "muted"}>{status}</Pill>}
          {saved && !dirty && (
            <span className="text-[12px] text-[var(--color-muted)]">saved {fmtTime(saved)}</span>
          )}
        </div>
      </header>

      <div className="px-6 pt-5 text-[13.5px] text-[var(--color-text-2)]">
        write what did not land, what you want changed, or what would make this easier to use in a campaign.
      </div>

      <div className="p-6">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="example: the hook is too quiet. make the first three seconds clearer, brighter, and more dramatic."
          rows={8}
          className="w-full resize-y rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-canvas)] px-4 py-3 text-[13.5px] leading-relaxed text-[var(--color-text)] placeholder:text-[var(--color-faint)] focus:outline-none"
        />

        {fb?.addressed_in_run && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[13px] text-[var(--color-text-2)]">
            <Pill tone="emerald">addressed</Pill>
            <span>by</span>
            <Link
              to={`/runs/${encodeURIComponent(fb.addressed_in_run)}`}
              className="text-[12px] text-[var(--color-rust)] hover:underline"
            >
              {fb.addressed_in_run}
            </Link>
            {fb.addressed_by_config && (
              <>
                <span>·</span>
                <code className="text-[12px] text-[var(--color-text-2)]">{fb.addressed_by_config}</code>
              </>
            )}
          </div>
        )}

        {err && (
          <div className="mt-3 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] px-3 py-2 text-[13px] text-[var(--color-text)]">
            {err}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="text-[12px] font-bold tracking-[0.08em] text-[var(--color-muted)]">status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as FeedbackStatus)}
            className="rounded border-[3px] border-[var(--color-line)] bg-[var(--color-canvas)] px-3 py-1.5 text-[13.5px] text-[var(--color-text)] focus:outline-none"
          >
            <option value="open">open</option>
            <option value="fulfilled">fulfilled</option>
            <option value="wontfix">wontfix</option>
          </select>

          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={onSave}
              disabled={busy || body.trim().length === 0}
              className={`px-5 py-2 text-[14px] font-bold transition-opacity ${
                busy || body.trim().length === 0
                  ? "cursor-not-allowed border-[3px] border-[var(--color-line)] bg-[var(--color-canvas)] text-[var(--color-faint)]"
                  : "btn-primary"
              }`}
            >
              {busy ? "saving..." : fb?.exists ? "update feedback" : "save feedback"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[11.5px] text-[var(--color-muted)]">{label}</div>
      <div className={`mt-1 ${accent ? "font-bold text-[var(--color-rust)]" : "text-[var(--color-text)]"}`}>
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
    <aside className="overflow-hidden rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="border-b-[3px] border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-3 text-[12.5px] font-bold text-[var(--color-muted)]">
        files · {artifacts.length}
      </div>

      <ul>
        {grouped.map(({ kind, items }) => (
          <li key={kind}>
            <div className="px-5 pt-4 pb-1.5 text-[11px] font-bold tracking-[0.08em] text-[var(--color-faint)]">
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
                      ? "bg-[var(--color-canvas)] font-bold text-[var(--color-rust)]"
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
  html: "playable",
  md:   "documents",
  json: "supporting info",
  txt:  "prompts",
  png:  "images",
  jpg:  "images",
  jpeg: "images",
  webp: "images",
};

function friendlyPipeline(pipeline: string) {
  if (pipeline === "creative_forge") return "video ad";
  if (pipeline === "playable_forge") return "playable ad";
  return pipeline || "marketing output";
}

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
