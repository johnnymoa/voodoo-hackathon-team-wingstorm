/* Backend types + fetch helpers. Mirrors src/adforge/api.py exactly. */

export type RunStatus = "completed" | "failed" | "running" | "unknown";

export interface RunSummary {
  run_id: string;
  pipeline: string | null;
  target_id: string | null;
  status: RunStatus | string;
  started_at: string | null;
  completed_at: string | null;
  artifact_count: number;
  has_manifest: boolean;
}

export interface Artifact {
  name: string;       // path relative to run_dir
  kind: string;       // "html" | "json" | "md" | "txt" | "png" | …
  size_bytes: number;
}

export interface RunManifest {
  run_id: string;
  pipeline: string;
  target_id: string;
  status: string;
  started_at: string;
  completed_at: string;
  params: Record<string, unknown>;
  children: string[];
  artifacts: Artifact[];
}

export interface Target {
  id: string;
  name: string;
  has_video: boolean;
  has_assets: boolean;
  notes?: string | null;
}

export interface TargetDetail {
  id: string;
  name: string;
  app_id: string | null;
  store_urls: Record<string, string>;
  notes: string | null;
  target_dir: string;
  video_path: string | null;
  asset_dir: string | null;
}

async function jget<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json() as Promise<T>;
}

export const api = {
  health:     () => jget<{ status: string }>("/api/health"),
  targets:    () => jget<Target[]>("/api/targets"),
  target:     (id: string) => jget<TargetDetail>(`/api/targets/${encodeURIComponent(id)}`),
  runs:       () => jget<RunSummary[]>("/api/runs"),
  run:        (run_id: string) => jget<RunManifest>(`/api/runs/${encodeURIComponent(run_id)}`),
  text:       async (run_id: string, rel: string) => {
    const res = await fetch(`/api/runs/${encodeURIComponent(run_id)}/text/${rel}`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.text();
  },
  artifactUrl: (run_id: string, rel: string) => `/artifacts/${encodeURIComponent(run_id)}/${rel}`,
  temporalUrl: (run_id: string, namespace = "default") =>
    `http://localhost:8233/namespaces/${namespace}/workflows/${encodeURIComponent(run_id)}`,
};
