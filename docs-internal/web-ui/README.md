---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# Web UI Overview

The web UI is a **Next.js 15.5** application with **Turbopack** for dev bundling and **React 19**. Located in `ui/`.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 15.5.19 |
| Build | Turbopack (dev), next build (prod) |
| React | 19.1.0 |
| Styling | Tailwind CSS 4 + `tw-animate-css` |
| UI Components | shadcn/ui (base-ui/react primitives) |
| Server State | TanStack React Query 5.101 |
| Client State | Zustand (via context) |
| Icons | lucide-react |
| Markdown | react-markdown + remark-gfm |
| Math | remark-math + rehype-katex |
| Code Highlighting | shiki |
| Charts | recharts |
| Notifications | sonner |
| Drag & Drop | @dnd-kit |
| Date | date-fns |
| Testing | Vitest + @testing-library/react |
| E2E | Playwright |

## Component Tree

```
app/layout.tsx          — Root layout, providers
app/page.tsx            — Entry page shell
  app/AgentPage.tsx     — Main page component
    Layout.tsx          — Two-column layout (sidebar + center)
      Sidebar.tsx       — Left nav: sessions, projects
      ChatView.tsx      — Center: message list + input
      SettingsModal.tsx — Overlay: 10-tab settings
```

## State Management

**Server state** (sessions, messages, config, agents, skills, MCP, models, projects, credentials, learnings, tokens) via TanStack Query with automatic cache invalidation after mutations. **Client state** (active session ID, streaming text, tool calls, gate requests, pending messages) via React `useState` in `AgentPage.tsx` and `ChatView.tsx`.

## Directory Structure

- `app/` — Next.js pages and layout
- `components/` — React components (chat, input, sidebar, settings, workspace, empty, ui)
- `hooks/` — 14 custom hooks wrapping TanStack Query
- `contexts/` — React context providers (`UserContext.tsx`)
- `lib/` — Utilities (`api.ts` fetch wrapper, `utils.ts`)
- `config/` — App configuration
- `__tests__/` — Vitest test files
