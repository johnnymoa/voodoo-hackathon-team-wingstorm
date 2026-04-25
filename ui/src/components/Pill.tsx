import type { ReactNode } from "react";

const TONES = {
  default:   "border-[var(--color-line-2)] text-[var(--color-text-2)]",
  forge:     "border-[var(--color-forge)] text-[var(--color-forge)]",
  emerald:   "border-[var(--color-emerald)] text-[var(--color-emerald)]",
  rust:      "border-[var(--color-rust)] text-[var(--color-rust)]",
  saffron:   "border-[var(--color-saffron)] text-[var(--color-saffron)]",
  muted:     "border-[var(--color-line)] text-[var(--color-muted)]",
} as const;

export function Pill({
  children, tone = "default", title, className = "",
}: {
  children: ReactNode;
  tone?: keyof typeof TONES;
  title?: string;
  className?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 border px-2 py-[2px] text-[10.5px] uppercase tracking-[0.12em] ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

const STATUS_TONE: Record<string, keyof typeof TONES> = {
  completed: "emerald",
  failed:    "rust",
  running:   "saffron",
  unknown:   "muted",
};

export function StatusPill({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? "muted";
  const dotClass = status === "running" ? "pulse-dot" : "";
  const dotColor =
    tone === "emerald" ? "var(--color-emerald)" :
    tone === "rust"    ? "var(--color-rust)" :
    tone === "saffron" ? "var(--color-saffron)" :
                         "var(--color-muted)";
  return (
    <Pill tone={tone}>
      <span
        className={`inline-block size-[6px] rounded-full ${dotClass}`}
        style={{ background: dotColor }}
      />
      {status}
    </Pill>
  );
}
