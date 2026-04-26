import { useEffect, useState } from "react";
import { marked } from "marked";
import { api, type Artifact } from "../lib/api";

const TEXT_KINDS = new Set(["md", "txt", "json", "yaml", "yml", "csv"]);
const IMAGE_KINDS = new Set(["png", "jpg", "jpeg", "webp", "gif", "svg"]);

export function ArtifactView({
  runId, artifact,
}: { runId: string; artifact: Artifact }) {
  if (artifact.kind === "html") return <HtmlPlayable runId={runId} artifact={artifact} />;
  if (IMAGE_KINDS.has(artifact.kind)) return <ImagePane runId={runId} artifact={artifact} />;
  if (artifact.kind === "md") return <MarkdownPane runId={runId} artifact={artifact} />;
  if (artifact.kind === "json") return <JsonPane runId={runId} artifact={artifact} />;
  if (TEXT_KINDS.has(artifact.kind)) return <TextPane runId={runId} artifact={artifact} />;
  return <BinaryPane runId={runId} artifact={artifact} />;
}

/* ─── individual viewers ──────────────────────────────────────────── */

function HtmlPlayable({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const src = api.artifactUrl(runId, artifact.name);
  return (
    <Frame label="playable preview" actions={<OpenInTab href={src} />}>
      <div className="flex justify-center bg-[var(--color-canvas)] p-4">
        <div
          className="overflow-hidden border-[3px] border-[var(--color-line)] bg-black"
          style={{ width: 414, height: 736 }}    /* iPhone-ish portrait for playables */
        >
          <iframe
            src={src}
            title={artifact.name}
            sandbox="allow-scripts allow-same-origin"
            className="h-full w-full"
          />
        </div>
      </div>
    </Frame>
  );
}

function ImagePane({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const src = api.artifactUrl(runId, artifact.name);
  return (
    <Frame label="image preview" actions={<OpenInTab href={src} />}>
      <div className="flex items-center justify-center bg-[var(--color-canvas)] p-6">
        <img src={src} alt={artifact.name} className="max-h-[70vh] max-w-full border-[3px] border-[var(--color-line)]" />
      </div>
    </Frame>
  );
}

function MarkdownPane({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const text = useText(runId, artifact);
  if (text.kind === "loading") return <PaneLoading label="document" />;
  if (text.kind === "error") return <PaneError label="document" message={text.error} />;
  const html = marked.parse(text.value, { async: false }) as string;
  return (
    <Frame label="document" actions={<OpenInTab href={api.artifactUrl(runId, artifact.name)} />}>
      <article
        className="prose-studio p-8 max-w-[78ch] mx-auto"
        // marked output is from local files we wrote ourselves; OK to dangerouslySetInnerHTML in this internal tool
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </Frame>
  );
}

function JsonPane({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const text = useText(runId, artifact);
  if (text.kind === "loading") return <PaneLoading label="supporting info" />;
  if (text.kind === "error") return <PaneError label="supporting info" message={text.error} />;
  let pretty = text.value;
  try {
    pretty = JSON.stringify(JSON.parse(text.value), null, 2);
  } catch { /* leave as-is */ }
  return (
    <Frame label="supporting info" actions={<OpenInTab href={api.artifactUrl(runId, artifact.name)} />}>
      <pre className="overflow-auto p-6 text-[13px] leading-relaxed text-[var(--color-text-2)]">{pretty}</pre>
    </Frame>
  );
}

function TextPane({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const text = useText(runId, artifact);
  if (text.kind === "loading") return <PaneLoading label={artifact.kind} />;
  if (text.kind === "error") return <PaneError label={artifact.kind} message={text.error} />;
  return (
    <Frame label="text file" actions={<OpenInTab href={api.artifactUrl(runId, artifact.name)} />}>
      <pre className="whitespace-pre-wrap break-words p-6 text-[13px] leading-relaxed text-[var(--color-text-2)]">{text.value}</pre>
    </Frame>
  );
}

function BinaryPane({ runId, artifact }: { runId: string; artifact: Artifact }) {
  return (
    <Frame label="download file" actions={<OpenInTab href={api.artifactUrl(runId, artifact.name)} />}>
      <div className="p-10 text-center text-[12px] text-[var(--color-muted)]">
        this file cannot be previewed here. open it in a new tab.
      </div>
    </Frame>
  );
}

/* ─── primitives ──────────────────────────────────────────────────── */

function Frame({
  label, actions, children,
}: { label: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="border-[3px] border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="flex items-center justify-between border-b-[3px] border-[var(--color-line)] bg-[var(--color-surface-2)] px-5 py-2.5 text-[12px] font-bold text-[var(--color-muted)]">
        <span>{label}</span>
        <div>{actions}</div>
      </div>
      {children}
    </div>
  );
}

function OpenInTab({ href }: { href: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-[var(--color-text-2)] hover:text-[var(--color-rust)]"
    >
      open
    </a>
  );
}

function PaneLoading({ label }: { label: string }) {
  return (
    <Frame label={label}>
      <div className="p-10 text-center text-[12px] text-[var(--color-muted)]">loading...</div>
    </Frame>
  );
}

function PaneError({ label, message }: { label: string; message: string }) {
  return (
    <Frame label={label}>
      <div className="p-6 text-[12px] text-[var(--color-rust)]">failed: {message}</div>
    </Frame>
  );
}

type TextState =
  | { kind: "loading" }
  | { kind: "ok"; value: string }
  | { kind: "error"; error: string };

function useText(runId: string, artifact: Artifact): TextState {
  const [state, setState] = useState<TextState>({ kind: "loading" });
  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    api.text(runId, artifact.name)
      .then((v) => !cancelled && setState({ kind: "ok", value: v }))
      .catch((e) => !cancelled && setState({ kind: "error", error: String(e) }));
    return () => { cancelled = true; };
  }, [runId, artifact.name]);
  return state;
}
