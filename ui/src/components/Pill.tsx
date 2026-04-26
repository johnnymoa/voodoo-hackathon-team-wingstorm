import type { ReactNode } from "react";

const TONES = {
  default:   "border-[var(--color-line)] text-[var(--color-text)] bg-[var(--color-canvas)]",
  forge:     "border-[var(--color-line)] text-[var(--color-text)] bg-[var(--color-forge)]",
  emerald:   "border-[var(--color-line)] text-[var(--color-text)] bg-[#c9f2d8]",
  rust:      "border-[var(--color-line)] text-[var(--color-text)] bg-[var(--color-rust)]",
  saffron:   "border-[var(--color-line)] text-[var(--color-text)] bg-[var(--color-saffron)]",
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
      className={`inline-flex items-center gap-1.5 rounded border-2 px-2.5 py-[3px] text-[11.5px] font-bold ${TONES[tone]} ${className}`}
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
