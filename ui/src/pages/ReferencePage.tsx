import { PageHeader } from "../components/Layout";
import { EmptyState } from "../components/EmptyState";

export default function ReferencePage() {
  return (
    <section className="page-in">
      <PageHeader
        index="03"
        eyebrow="canonical playables to study"
        title="Reference"
      />
      <EmptyState
        title="Study the masters."
        body="Reference playables live at reference/ in the repo and aren't served by the API yet. Open them directly in your editor or browser to see the CONFIG-block pattern in action."
        hint={
          <>
            <div className="mb-2 text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-muted)]">on disk</div>
            <div className="font-mono text-[var(--color-text)]">
              reference/MarbleSort.html<br />
              reference/CupHeroes.html
            </div>
          </>
        }
      />
    </section>
  );
}
