import { NavLink, Outlet, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

const NAV = [
  { to: "/runs",      label: "Runs",      glyph: "01" },
  { to: "/targets",   label: "Targets",   glyph: "02" },
  { to: "/reference", label: "Reference", glyph: "03" },
];

export function Layout() {
  const loc = useLocation();
  return (
    <div className="relative min-h-full">
      {/* Top fixed nav */}
      <header className="sticky top-0 z-20 border-b border-[var(--color-line)] bg-[color:var(--color-canvas)]/85 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1320px] items-center gap-6 px-6 h-12">
          <NavLink
            to="/runs"
            className="font-display italic text-[20px] leading-none tracking-[-0.02em] text-[var(--color-text)] hover:text-[var(--color-forge)] transition-colors"
          >
            adforge
          </NavLink>
          <span className="text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)]">
            engineering log
          </span>

          <nav className="ml-auto flex items-center gap-1">
            {NAV.map((n) => {
              const active = loc.pathname.startsWith(n.to);
              return (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={`group flex items-center gap-2 px-3 py-1.5 text-[11px] uppercase tracking-[0.14em] transition-colors ${
                    active
                      ? "text-[var(--color-forge)]"
                      : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
                  }`}
                >
                  <span className="text-[10px] text-[var(--color-faint)] group-hover:text-[var(--color-text-2)]">
                    {n.glyph}
                  </span>
                  {n.label}
                  {active && (
                    <span className="block h-[2px] w-3 bg-[var(--color-forge)]" />
                  )}
                </NavLink>
              );
            })}
          </nav>

          <a
            href="http://localhost:8233"
            target="_blank"
            rel="noreferrer"
            className="ml-2 flex items-center gap-1.5 border border-[var(--color-line-2)] px-2.5 py-1 text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
            title="Open Temporal Web UI"
          >
            <span>Temporal</span>
            <span className="text-[10px]">↗</span>
          </a>
        </div>
      </header>

      {/* Page body */}
      <main className="relative z-10 mx-auto max-w-[1320px] px-6 py-8">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-20 border-t border-[var(--color-line)]">
      <div className="mx-auto flex max-w-[1320px] items-center justify-between px-6 py-5 text-[10.5px] uppercase tracking-[0.14em] text-[var(--color-muted)]">
        <span>adforge / runs viewer</span>
        <span>v0.1.0 · localhost</span>
      </div>
    </footer>
  );
}

/** Page header used by all top-level routes. Bold serif italic title + thin orange tick. */
export function PageHeader({
  index, eyebrow, title, accent, right,
}: {
  index: string;
  eyebrow: string;
  title: string;
  accent?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-8 flex items-end justify-between gap-6 border-b border-[var(--color-line)] pb-6">
      <div className="min-w-0">
        <div className="mb-2 flex items-center gap-3 text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-muted)]">
          <span className="text-[var(--color-forge)]">§ {index}</span>
          <span className="h-px flex-1 bg-[var(--color-line)]" style={{ minWidth: 32 }} />
          <span>{eyebrow}</span>
        </div>
        <h1 className="font-display text-[44px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
          <span className="italic">{title}</span>
          {accent && (
            <span className="ml-3 text-[var(--color-forge)] not-italic">·</span>
          )}
          {accent && <span className="ml-2 italic text-[var(--color-text-2)]">{accent}</span>}
        </h1>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}
