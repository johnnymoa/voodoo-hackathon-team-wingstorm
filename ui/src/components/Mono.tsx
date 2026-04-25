import { useState } from "react";

/** Click-to-copy monospace value. Used for run_ids, paths, ids. */
export function Mono({ value, className = "" }: { value: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async (e) => {
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1100);
        } catch { /* clipboard may be unavailable; ignore */ }
      }}
      title={copied ? "copied" : "click to copy"}
      className={`group inline-flex items-center gap-2 font-mono text-[12.5px] text-[var(--color-text-2)] hover:text-[var(--color-forge)] transition-colors ${className}`}
    >
      <span className="truncate">{value}</span>
      <span className="text-[11px] text-[var(--color-faint)] group-hover:text-[var(--color-forge)]">
        {copied ? "copied" : "copy"}
      </span>
    </button>
  );
}
