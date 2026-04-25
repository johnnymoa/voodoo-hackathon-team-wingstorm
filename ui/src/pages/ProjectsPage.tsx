import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Project } from "../lib/api";
import { PageHeader } from "../components/Layout";
import { Pill } from "../components/Pill";

export default function ProjectsPage() {
  const [list, setList] = useState<Project[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.projects()
      .then((r) => !cancelled && setList(r))
      .catch((e) => !cancelled && setErr(String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="page-in">
      <PageHeader
        eyebrow="Projects"
        title="Your games."
        subtitle="A project is one game and everything you know about it. Open one to run pipelines and see past runs."
      />

      {err && (
        <div className="mb-6 rounded-md border border-[var(--color-rust)]/40 bg-[var(--color-rust)]/5 p-4 text-[14px] text-[var(--color-rust)]">
          {err}
        </div>
      )}

      {list && list.length === 0 && !err && (
        <div className="rounded-md border border-dashed border-[var(--color-line-2)] p-10 text-center">
          <p className="font-display italic text-[24px] text-[var(--color-text)]">No projects yet.</p>
          <p className="mt-3 text-[14px] text-[var(--color-text-2)]">
            Create one in 30 seconds:
          </p>
          <pre className="mx-auto mt-3 inline-block rounded border border-[var(--color-line)] bg-[var(--color-surface)] p-3 text-left font-mono text-[12.5px] text-[var(--color-text)]">
{`mkdir projects/royal_match
echo '{"name":"Royal Match"}' > projects/royal_match/project.json`}
          </pre>
        </div>
      )}

      {list && list.length > 0 && (
        <div className="stagger grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {list.map((p) => <ProjectCard key={p.id} p={p} />)}
        </div>
      )}
    </section>
  );
}

function ProjectCard({ p }: { p: Project }) {
  return (
    <Link
      to={`/projects/${encodeURIComponent(p.id)}`}
      className="group relative block overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] p-6 transition-colors hover:border-[var(--color-forge)]/60"
    >
      <h2 className="font-display italic text-[28px] leading-tight tracking-[-0.01em] text-[var(--color-text)] group-hover:text-[var(--color-forge)] transition-colors">
        {p.name}
      </h2>
      <div className="mt-1 font-mono text-[12px] text-[var(--color-muted)]">{p.id}</div>

      {p.genre && (
        <div className="mt-3 text-[13.5px] text-[var(--color-text-2)]">{p.genre}</div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Pill tone={p.has_video ? "emerald" : "muted"}>
          {p.has_video ? "video ✓" : "no video"}
        </Pill>
        <Pill tone={p.has_assets ? "emerald" : "muted"}>
          {p.has_assets ? "assets ✓" : "no assets"}
        </Pill>
      </div>

      <div className="mt-5 text-[13px] text-[var(--color-muted)] group-hover:text-[var(--color-forge)] transition-colors">
        Open →
      </div>
    </Link>
  );
}
