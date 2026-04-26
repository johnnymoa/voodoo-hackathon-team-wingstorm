import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { api, type Project, type RunSummary } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";
import { fmtTime, parseRunId } from "../lib/format";

export default function ProjectsPage() {
  const [list, setList] = useState<Project[] | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [uploaderOpen, setUploaderOpen] = useState(false);

  const refresh = useCallback(() => {
    return Promise.all([api.projects(), api.runs()])
      .then(([projects, runList]) => {
        setList(projects);
        setRuns(runList);
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    refresh()
      .then(() => {
        if (cancelled) return;
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, [refresh]);

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="projects"
        title="your games"
        subtitle="each card is a quick marketing read of the game folder: what it is, what it looks like, what source material is available, and what has already been made."
        right={
          <button
            type="button"
            onClick={() => setUploaderOpen(true)}
            className="btn-primary px-5 py-2.5 text-[14px] font-bold"
          >
            add project
          </button>
        }
      />

      {err && (
        <div className="mb-6 rounded-md border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] p-4 text-[14px] text-[var(--color-text)]">
          {err}
        </div>
      )}

      {list && list.length === 0 && !err && (
        <div className="card-pop bg-[var(--color-surface)] p-10 text-center">
          <p className="font-display text-[26px] font-bold text-[var(--color-text)]">no projects yet</p>
          <p className="mt-3 text-[14px] text-[var(--color-text-2)]">
            add a game folder with a title, pitch, screenshots, video, and design notes.
          </p>
        </div>
      )}

      {list && list.length > 0 && (
        <div className="stagger grid grid-cols-1 gap-7 xl:grid-cols-2">
          {list.map((p) => (
            <ProjectCard
              key={p.id}
              p={p}
              runs={(runs ?? []).filter((r) => r.project_id === p.id)}
            />
          ))}
        </div>
      )}

      {uploaderOpen && (
        <ProjectUploader
          onClose={() => setUploaderOpen(false)}
          onUploaded={() => refresh()}
        />
      )}
    </section>
  );
}

function ProjectUploader({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded: () => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [folderName, setFolderName] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [created, setCreated] = useState<Project | null>(null);
  const directoryProps = { webkitdirectory: "", directory: "" } as Record<string, string>;

  const onPick = (picked: FileList | null) => {
    const next = Array.from(picked ?? []);
    setFiles(next);
    setCreated(null);
    setErr(null);
    const firstPath = next[0]?.webkitRelativePath || next[0]?.name || "";
    setFolderName(firstPath.includes("/") ? firstPath.split("/")[0] : firstPath || null);
  };

  const upload = async () => {
    if (!files.length) {
      setErr("choose a project folder first");
      return;
    }
    const body = new FormData();
    body.append("project_name", folderName || "new project");
    if (folderName) body.append("root_folder", folderName);
    for (const file of files) {
      body.append("files", file, file.webkitRelativePath || file.name);
    }

    setBusy(true);
    setErr(null);
    try {
      const res = await api.uploadProject(body);
      setCreated(res.project);
      await onUploaded();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/30 px-5">
      <section className="card-pop max-h-[88vh] w-full max-w-[720px] overflow-auto bg-[var(--color-canvas)] p-6">
        <div className="flex items-start justify-between gap-5">
          <div>
            <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">add project</div>
            <h2 className="mt-1 font-display text-[36px] font-bold leading-tight tracking-[-0.03em]">
              upload a game folder
            </h2>
            <p className="mt-2 max-w-[58ch] text-[14px] leading-relaxed text-[var(--color-text-2)]">
              choose a folder with screenshots, gameplay video, art, and any design notes. adforge
              will save it into projects and infer the card automatically.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border-2 border-[var(--color-line)] px-3 py-1 text-[13px] font-bold"
          >
            close
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => onPick(e.currentTarget.files)}
          {...directoryProps}
        />

        <div className="mt-6 rounded border-[3px] border-dashed border-[var(--color-line)] bg-[var(--color-surface)] p-6 text-center">
          <p className="text-[15px] font-bold">
            {folderName ? `selected: ${folderName}` : "no folder selected yet"}
          </p>
          <p className="mt-1 text-[13px] text-[var(--color-muted)]">
            {files.length ? `${files.length} files ready to upload` : "folder upload works best in chrome, edge, or safari."}
          </p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="btn-secondary mt-4 px-5 py-2 text-[14px] font-bold"
          >
            choose folder
          </button>
        </div>

        {err && (
          <div className="mt-4 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-rust)] p-3 text-[14px]">
            {err}
          </div>
        )}

        {created && (
          <div className="mt-4 rounded border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] p-4 text-[14px]">
            <div className="font-bold">project added: {created.name}</div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-[13px]">
              <span>genre: {created.genre || "could not infer"}</span>
              <span>subgenre: {created.subgenre || "could not infer"}</span>
              <span>screenshots: {created.screenshots?.length ?? 0}</span>
              <span>videos: {created.gameplay_videos?.length ?? 0}</span>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          {created && (
            <Link
              to={`/projects/${encodeURIComponent(created.id)}`}
              onClick={onClose}
              className="btn-secondary px-5 py-2 text-[14px] font-bold"
            >
              open project
            </Link>
          )}
          <button
            type="button"
            onClick={upload}
            disabled={busy || files.length === 0}
            className={`px-5 py-2 text-[14px] font-bold ${
              busy || files.length === 0
                ? "cursor-not-allowed rounded border-[3px] border-[var(--color-line)] bg-[var(--color-surface)] text-[var(--color-muted)]"
                : "btn-primary"
            }`}
          >
            {busy ? "uploading..." : "add project"}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  );
}

function ProjectCard({ p, runs }: { p: Project; runs: RunSummary[] }) {
  const screenshots = p.screenshots ?? [];
  const videos = p.gameplay_videos ?? [];
  const docs = p.design_documents ?? [];
  const palette = p.color_palette ?? [];

  return (
    <article className="card-pop bg-[var(--color-surface)] p-5">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[220px_1fr]">
        <div>
          {screenshots[0] ? (
            <img
              src={api.projectFileUrl(p.id, screenshots[0].rel_path)}
              alt={`${p.name} screenshot`}
              className="aspect-[4/5] w-full rounded border-[3px] border-[var(--color-line)] object-cover"
            />
          ) : (
            <div className="grid aspect-[4/5] place-items-center rounded border-[3px] border-dashed border-[var(--color-line)] bg-[var(--color-canvas)] p-4 text-center text-[13px] text-[var(--color-muted)]">
              no screenshot or image found
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            <Pill tone={videos.length ? "emerald" : "muted"}>{videos.length ? "gameplay video" : "no video"}</Pill>
            <Pill tone={docs.length ? "saffron" : "muted"}>{docs.length ? "design doc" : "no design doc"}</Pill>
          </div>
        </div>

        <div className="min-w-0">
          <Link
            to={`/projects/${encodeURIComponent(p.id)}`}
            className="group inline-block"
          >
            <h2 className="font-display text-[34px] font-bold leading-tight tracking-[-0.03em] text-[var(--color-text)] group-hover:underline">
              {p.name}
            </h2>
          </Link>

          <div className="mt-3 grid grid-cols-1 gap-3 text-[14px] sm:grid-cols-2">
            <Info label="genre" value={p.genre} />
            <Info label="subgenre" value={p.subgenre} />
            <Info label="art style" value={p.art_style} />
            <Info label="juice" value={p.juice} />
          </div>

          <div className="mt-4">
            <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">elevator pitch</div>
            <p className="mt-1 text-[18px] font-bold leading-snug text-[var(--color-text)]">
              {p.elevator_pitch || "could not infer a short pitch because no design doc or descriptive project notes were found."}
            </p>
          </div>

          <div className="mt-4">
            <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">summary</div>
            <p className="mt-1 text-[14px] leading-relaxed text-[var(--color-text)]">
              {p.summary || p.description || "could not infer a summary because no design doc or descriptive project notes were found."}
            </p>
          </div>

          <div className="mt-4">
            <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">color palette</div>
            {palette.length ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {palette.map((color) => <ColorChip key={color} label={color} />)}
              </div>
            ) : (
              <p className="mt-1 text-[13px] text-[var(--color-muted)]">could not infer without screenshots or images</p>
            )}
          </div>

          {screenshots.length > 1 && (
            <div className="mt-4 flex gap-2 overflow-hidden">
              {screenshots.slice(1, 5).map((shot) => (
                <img
                  key={shot.rel_path}
                  src={api.projectFileUrl(p.id, shot.rel_path)}
                  alt={shot.name}
                  className="h-16 w-16 rounded border-2 border-[var(--color-line)] object-cover"
                />
              ))}
            </div>
          )}

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {videos[0] && (
              <a
                href={api.projectFileUrl(p.id, videos[0].rel_path)}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary px-4 py-2 text-center text-[14px] font-bold"
              >
                open gameplay video
              </a>
            )}
            {docs[0] && (
              <a
                href={api.projectFileUrl(p.id, docs[0].rel_path)}
                target="_blank"
                rel="noreferrer"
                className="btn-tertiary px-4 py-2 text-center text-[14px] font-bold"
              >
                open design document
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 border-t-[3px] border-[var(--color-line)] pt-4">
        <div className="mb-2 text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">output history</div>
        {runs.length === 0 ? (
          <p className="text-[13px] text-[var(--color-muted)]">nothing made yet</p>
        ) : (
          <ul className="space-y-2">
            {runs.slice(0, 4).map((run) => (
              <li key={run.run_id}>
                <Link
                  to={`/runs/${encodeURIComponent(run.run_id)}`}
                  className="flex items-center justify-between gap-3 rounded border-2 border-[var(--color-line)] bg-[var(--color-canvas)] px-3 py-2 text-[13px] hover:bg-[var(--color-saffron)]"
                >
                  <span className="truncate">{friendlyPipeline(run.pipeline)}</span>
                  <span className="shrink-0 text-[var(--color-muted)]">{createdAt(run)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-[12px] font-bold tracking-[0.12em] text-[var(--color-muted)]">{label}</div>
      <div className="mt-0.5 text-[14px] text-[var(--color-text)]">{value || "could not infer from files"}</div>
    </div>
  );
}

function ColorChip({ label }: { label: string }) {
  const hex = label.match(/#[0-9a-f]{6}/i)?.[0];
  return (
    <span
      className="inline-flex items-center gap-2 rounded border-2 border-[var(--color-line)] px-2.5 py-[3px] text-[11.5px] font-bold"
      style={{ backgroundColor: hex ?? "var(--color-canvas)", color: textColor(hex) }}
    >
      <span
        className="inline-block size-3 rounded border border-[var(--color-line)]"
        style={{ backgroundColor: hex ?? "transparent" }}
      />
      {label}
    </span>
  );
}

function textColor(hex?: string) {
  if (!hex) return "var(--color-text)";
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? "#000" : "#fff";
}

function friendlyPipeline(pipeline: string | null) {
  if (pipeline === "creative_forge") return "video ad";
  if (pipeline === "playable_forge") return "playable ad";
  return pipeline || "marketing output";
}

function createdAt(run: RunSummary) {
  return parseRunId(run.run_id)?.ts ?? fmtTime(run.started_at);
}
