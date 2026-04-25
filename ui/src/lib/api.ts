/* Backend types + fetch helpers. Mirrors src/adforge/api.py exactly. */

export type RunStatus = "completed" | "failed" | "running" | "unknown";

export interface RunSummary {
  run_id: string;
  pipeline: string | null;
  project_id: string | null;
  config_id: string | null;
  status: RunStatus | string;
  started_at: string | null;
  completed_at: string | null;
  artifact_count: number;
  has_manifest: boolean;
}

export interface Artifact {
  name: string;
  kind: string;
  size_bytes: number;
}

export interface RunManifest {
  run_id: string;
  pipeline: string;
  project_id: string;
  config_id: string;
  status: string;
  started_at: string;
  completed_at: string;
  params: Record<string, unknown>;
  artifacts: Artifact[];
}

export interface Project {
  id: string;
  name: string;
  genre?: string | null;
  description?: string | null;
  category_id?: string;
  country?: string;
  has_video: boolean;
  has_assets: boolean;
  notes?: string | null;
}

export interface ProjectDetail extends Project {
  app_id: string | null;
  store_urls: Record<string, string>;
  project_dir: string;
  video_path: string | null;
  asset_dir: string | null;
}

export interface PipelineConfig {
  id: string;
  name: string;
  description: string;
  params: Record<string, unknown>;
}

export interface Pipeline {
  id: string;
  name: string;
  glyph: string;
  tagline: string;
  track: "track-2" | "track-3";
  needs: string[];
  produces: string[];
  cli: string;
  configs: PipelineConfig[];
}

async function jget<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json() as Promise<T>;
}

export const api = {
  health:        () => jget<{ status: string }>("/api/health"),
  pipelines:     () => jget<Pipeline[]>("/api/pipelines"),
  projects:      () => jget<Project[]>("/api/projects"),
  project:       (id: string) => jget<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`),
  projectRuns:   (id: string) => jget<RunSummary[]>(`/api/projects/${encodeURIComponent(id)}/runs`),
  runs:          () => jget<RunSummary[]>("/api/runs"),
  run:           (run_id: string) => jget<RunManifest>(`/api/runs/${encodeURIComponent(run_id)}`),
  text:          async (run_id: string, rel: string) => {
    const res = await fetch(`/api/runs/${encodeURIComponent(run_id)}/text/${rel}`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.text();
  },
  artifactUrl:   (run_id: string, rel: string) => `/artifacts/${encodeURIComponent(run_id)}/${rel}`,
  temporalUrl:   (run_id: string, namespace = "default") =>
    `http://localhost:8233/namespaces/${namespace}/workflows/${encodeURIComponent(run_id)}`,
};
