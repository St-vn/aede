---
type: doc
tags: [docs, publishing]
date_updated: 2026-06-14
---

# Publishing docs

## Hosting on Vercel

The docs are part of the Next.js app in `ui/`, deployed to Vercel.

### Vercel configuration

1. Connect the repo to Vercel (already linked to `aede.dev`)
2. Framework preset: **Next.js**
3. Root directory: `ui/`
4. Build command: `npm run build`
5. Output directory: `.next` (automatic)

### Domain

The docs live at `https://aede.dev/docs/` alongside the web UI at `https://aede.dev/`.

### Local preview

```bash
cd ui
npm run dev
# Docs at http://localhost:3000/docs/
```

## How it works

- Markdown content lives in `docs/` at the repo root
- The Next.js app in `ui/` reads `../docs/` at build time
- `generateStaticParams` pre-renders every `.md` file as a static page
- Syntax highlighting via Shiki (github-dark theme)
- Sidebar nav is built automatically from the docs directory structure

### Excluded from nav

- `docs/plans/`, `docs/adr/`, `docs/kaizen/`, `docs/sdlc-engineer/` — internal planning docs, excluded from sidebar
- `docs/PUBLISHING.md`, `docs/SOURCE_OF_TRUTH.md` — not linked from nav (accessible by direct URL)

### Link format

All internal links use `.md` extensions in source. The build rewrites them to `/docs/slug` routes automatically.

### LLM ingestion

- `llms.txt` and `llms-full.txt` remain in `docs/` — they're accessible at `https://aede.dev/docs/llms.txt`
- They must be regenerated when docs change (manual for now)
