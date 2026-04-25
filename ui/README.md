# ui/

Read-only viewer for adforge runs. Vite + React + TypeScript + Tailwind v4.

## Architecture

```
ui/
├── index.html
├── vite.config.ts        proxies /api and /artifacts → http://127.0.0.1:8765
├── src/
│   ├── main.tsx          router (3 routes)
│   ├── index.css         design tokens (Fraunces + JetBrains Mono, forge-orange palette)
│   ├── lib/
│   │   ├── api.ts        typed fetch helpers, mirrors src/adforge/api.py
│   │   └── format.ts     time / bytes / run_id helpers
│   ├── components/
│   │   ├── Layout.tsx    sticky nav + page header primitive
│   │   ├── Pill.tsx      status / tag pills
│   │   ├── Mono.tsx      click-to-copy mono value
│   │   ├── EmptyState.tsx
│   │   └── ArtifactView.tsx   switches by kind: html → iframe, md → markdown,
│   │                          json → pretty-print, txt → pre, png/jpg → img
│   └── pages/
│       ├── RunsPage.tsx       /runs       — engineering log table
│       ├── RunDetailPage.tsx  /runs/:id   — manifest + artifact viewer
│       ├── TargetsPage.tsx    /targets    — input bundle cards
│       └── ReferencePage.tsx  /reference  — placeholder
```

## Run

Both the API and the UI must be up. From the repo root:

```bash
# in one terminal
uv run adforge api                  # http://127.0.0.1:8765

# in another
cd ui && npm install && npm run dev # http://localhost:5173
```

Vite proxies `/api` and `/artifacts` to the FastAPI port, so the SPA can fetch
manifests and load run artifacts (HTML/MD/JSON/PNG) without CORS pain.

## Design language

Engineering logbook / industrial blueprint:

- **Display** Fraunces italic — section titles, run names
- **Everything else** JetBrains Mono — UI labels, ids, code, table cells
- **Palette** warm charcoal canvas, single forge-orange accent (`#ff5722`),
  status colors only on pills (emerald / saffron / rust)
- **Composition** dense by design: hairline tables, ruler ticks, `§` glyphs
  as section markers, generous negative space around the serif heads
