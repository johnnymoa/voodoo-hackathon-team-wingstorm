import type { ReactNode } from "react";

export function EmptyState({
  title, body, hint,
}: {
  title: string;
  body: string;
  hint?: ReactNode;
}) {
  return (
    <div className="relative overflow-hidden border border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="bp-grid absolute inset-0 opacity-50" />
      <div className="relative flex flex-col items-start gap-4 p-10">
        <div className="flex items-center gap-2 text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-forge)]">
          <span>—</span><span>void</span><span>—</span>
        </div>
        <h2 className="font-display italic text-[28px] leading-tight tracking-[-0.01em] text-[var(--color-text)]">
          {title}
        </h2>
        <p className="max-w-[60ch] text-[13px] text-[var(--color-text-2)] leading-relaxed">
          {body}
        </p>
        {hint && (
          <div className="mt-2 w-full max-w-[680px] border border-[var(--color-line)] bg-[var(--color-canvas)] p-4 text-[12px] text-[var(--color-text-2)]">
            {hint}
          </div>
        )}
      </div>
    </div>
  );
}
