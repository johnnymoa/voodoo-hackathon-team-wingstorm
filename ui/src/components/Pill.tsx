import type { ReactNode } from "react";

const TONES = {
  default:   "border-[var(--color-line-2)] text-[var(--color-text-2)] bg-transparent",
  forge:     "border-[var(--color-forge)]/60 text-[var(--color-forge)] bg-[var(--color-forge)]/10",
  emerald:   "border-[var(--color-emerald)]/60 text-[var(--color-emerald)] bg-[var(--color-emerald)]/10",
  rust:      "border-[var(--color-rust)]/60 text-[var(--color-rust)] bg-[var(--color-rust)]/10",
  saffron:   "border-[var(--color-saffron)]/60 text-[var(--color-saffron)] bg-[var(--color-saffron)]/10",
  muted:     "border-[var(--color-line)] text-[var(--color-muted)] bg-transparent",
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
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] text-[11.5px] ${TONES[tone]} ${className}`}
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
