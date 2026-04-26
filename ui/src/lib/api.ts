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

export interface ProjectFile {
  name: string;
  rel_path: string;
  size_bytes: number;
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
  completed_at: string | null;
  params: Record<string, unknown>;
  artifacts: Artifact[];
}

export interface Project {
  id: string;
  name: string;
  genre?: string | null;
  subgenre?: string | null;
  elevator_pitch?: string | null;
  summary?: string | null;
  art_style?: string | null;
  color_palette?: string[];
  juice?: string | null;
  description?: string | null;
  category_id?: string;
  country?: string;
  has_video: boolean;
  has_assets: boolean;
  screenshots?: ProjectFile[];
  gameplay_videos?: ProjectFile[];
  design_documents?: ProjectFile[];
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

export interface PipelineInput {
  id: string;
  kind: "file" | "dir" | "metadata" | string;
  description: string;
  required: boolean;
}

export interface Pipeline {
  id: string;
  name: string;
  description: string;
  inputs: PipelineInput[];
  outputs: string[];
  cli: string;
  configs: PipelineConfig[];
}

export interface StartRunResponse {
  run_id: string;
  pipeline: string;
  project_id: string;
  config_id: string;
  started_at: string;
  status: string;
}

export interface UploadProjectResponse {
  project_id: string;
  project: Project;
}

export type FeedbackStatus = "open" | "fulfilled" | "wontfix";

export interface Feedback {
  run_id: string;
  status: FeedbackStatus | string;
  created_at: string | null;
  updated_at: string | null;
  addressed_in_run: string | null;
  addressed_by_config: string | null;
  body: string;
  exists: boolean;
}

async function jget<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`);
  return res.json() as Promise<T>;
}

async function jpost<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j?.detail) detail = String(j.detail);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health:        () => jget<{ status: string }>("/api/health"),
  pipelines:     () => jget<Pipeline[]>("/api/pipelines"),
  projects:      () => jget<Project[]>("/api/projects"),
  project:       (id: string) => jget<ProjectDetail>(`/api/projects/${encodeURIComponent(id)}`),
  uploadProject: async (body: FormData) => {
    const res = await fetch("/api/projects/upload", { method: "POST", body });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const j = await res.json();
        if (j?.detail) detail = String(j.detail);
      } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json() as Promise<UploadProjectResponse>;
  },
  projectRuns:   (id: string) => jget<RunSummary[]>(`/api/projects/${encodeURIComponent(id)}/runs`),
  runs:          () => jget<RunSummary[]>("/api/runs"),
  run:           (run_id: string) => jget<RunManifest>(`/api/runs/${encodeURIComponent(run_id)}`),
  startRun:      (pipeline_id: string, project_id: string, config_id = "default") =>
    jpost<StartRunResponse>("/api/runs", { pipeline_id, project_id, config_id }),
  getFeedback:   (run_id: string) =>
    jget<Feedback>(`/api/runs/${encodeURIComponent(run_id)}/feedback`),
  saveFeedback:  (run_id: string, body: string, status?: FeedbackStatus) =>
    jpost<Feedback>(`/api/runs/${encodeURIComponent(run_id)}/feedback`, { body, status }),
  text:          async (run_id: string, rel: string) => {
    const res = await fetch(`/api/runs/${encodeURIComponent(run_id)}/text/${rel}`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.text();
  },
  artifactUrl:   (run_id: string, rel: string) => `/artifacts/${encodeURIComponent(run_id)}/${rel}`,
  projectFileUrl: (project_id: string, rel: string) => `/project-files/${encodeURIComponent(project_id)}/${rel}`,
  temporalUrl:   (run_id: string, namespace = "default") =>
    `http://localhost:8233/namespaces/${namespace}/workflows/${encodeURIComponent(run_id)}`,
};
