/* Small format helpers — keep view code lean. */

export function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  const k = 1024;
  if (n < k) return `${n} B`;
  if (n < k * k) return `${(n / k).toFixed(1)} KB`;
  if (n < k * k * k) return `${(n / k / k).toFixed(2)} MB`;
  return `${(n / k / k / k).toFixed(2)} GB`;
}

export function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fmtDuration(startISO: string | null, endISO: string | null): string {
  if (!startISO || !endISO) return "—";
  const ms = new Date(endISO).getTime() - new Date(startISO).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${pad2(s)}s`;
}

function pad2(n: number) { return String(n).padStart(2, "0"); }

/** "20260425-143207__creative__castle_clashers" → ["2026.04.25 14:32:07", "creative", "castle_clashers"] */
export function parseRunId(rid: string): { ts: string; pipeline: string; target: string } | null {
  const m = rid.match(/^(\d{8})-(\d{6})__([^_][^_]*?)__(.+)$/);
  if (!m) return null;
  const [, d, t, pipeline, target] = m;
  const ts = `${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)} ${t.slice(0, 2)}:${t.slice(2, 4)}:${t.slice(4, 6)}`;
  return { ts, pipeline, target };
}

export function shortenRunId(rid: string): string {
  // For tight columns: keep only the timestamp + last 4 chars of target
  const parsed = parseRunId(rid);
  if (!parsed) return rid;
  return `${parsed.ts.replace(/[. ]/g, "").slice(0, 12)}…${parsed.target.slice(-6)}`;
}

export const PIPELINE_GLYPH: Record<string, string> = {
  creative_forge: "✦",
  playable_forge: "▲",
  full_forge:     "◆",
};

export function pipelineGlyph(pipeline: string | null | undefined): string {
  if (!pipeline) return "·";
  return PIPELINE_GLYPH[pipeline] ?? "·";
}
