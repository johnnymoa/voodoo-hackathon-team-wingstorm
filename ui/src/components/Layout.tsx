import { NavLink, Outlet, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

const NAV = [
  { to: "/projects",  label: "Projects" },
  { to: "/pipelines", label: "Pipelines" },
  { to: "/runs",      label: "Runs" },
];

export function Layout() {
  const loc = useLocation();
  return (
    <div className="relative min-h-full">
      <header className="sticky top-0 z-20 border-b border-[var(--color-line)] bg-[color:var(--color-canvas)]/85 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-[1320px] items-center gap-7 px-7">
          <NavLink
            to="/"
            className="font-display italic text-[22px] leading-none tracking-[-0.02em] text-[var(--color-text)] hover:text-[var(--color-forge)] transition-colors"
          >
            adforge
          </NavLink>
          <span className="hidden text-[12px] text-[var(--color-muted)] md:inline">
            project → pipeline → run
          </span>

          <nav className="ml-auto flex items-center gap-1">
            {NAV.map((n) => {
              const active = loc.pathname.startsWith(n.to);
              return (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={`relative px-4 py-2 text-[13.5px] transition-colors ${
                    active
                      ? "text-[var(--color-text)]"
                      : "text-[var(--color-muted)] hover:text-[var(--color-text-2)]"
                  }`}
                >
                  {n.label}
                  {active && (
                    <span className="absolute inset-x-3 -bottom-[1px] h-[2px] bg-[var(--color-forge)]" />
                  )}
                </NavLink>
              );
            })}
          </nav>

          <a
            href="http://localhost:8233"
            target="_blank"
            rel="noreferrer"
            className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-[var(--color-line-2)] px-3 py-1.5 text-[12px] text-[var(--color-text-2)] hover:border-[var(--color-forge)] hover:text-[var(--color-forge)]"
            title="Open Temporal Web UI"
          >
            Temporal
            <span aria-hidden>↗</span>
          </a>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-[1320px] px-7 py-10">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-[var(--color-line)]">
      <div className="mx-auto flex max-w-[1320px] items-center justify-between px-7 py-6 text-[12px] text-[var(--color-muted)]">
        <span>adforge</span>
        <span>v0.2 · localhost</span>
      </div>
    </footer>
  );
}

/** Page header used by all top-level routes. Bigger, less typographic noise. */
export function PageHeader({
  eyebrow, title, subtitle, right,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-10 flex items-end justify-between gap-6 border-b border-[var(--color-line)] pb-7">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-2 text-[12px] uppercase tracking-[0.12em] text-[var(--color-muted)]">
            {eyebrow}
          </div>
        )}
        <h1 className="font-display italic text-[44px] leading-[1.05] tracking-[-0.015em] text-[var(--color-text)]">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 max-w-[60ch] text-[15px] text-[var(--color-text-2)]">{subtitle}</p>
        )}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}
