---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# Web UI Architecture

## Routing

The UI is a **single-page application** with no Next.js routes beyond the root. `ui/app/page.tsx` renders `AgentPage.tsx`, which manages all navigation through React state:

- `activeId: string | null` — the active session ID
- `activeProjectDir: string | null` — the active project directory
- `initialMessage: string` — message to send when entering a new session
- `settingsOpen: boolean` — settings modal visibility

When `activeId` is null and no project is active, `EmptyState` is shown. When a session is active, `ChatView` renders.

## Page Layout

`AgentPage.tsx` (`ui/app/app/AgentPage.tsx`) renders:
1. `Layout` — two-column flex container with sidebar + center pane
2. `Sidebar` — left panel with session list grouped by project, navigation, settings button
3. `ChatView` or `EmptyState` — center content
4. `InputBar` — message input at bottom (always visible in empty state, inside ChatView for active sessions)
5. `SettingsModal` — overlay triggered from sidebar or slash commands

## State Flow

1. User types in `InputBar` → `handleSendNewSession()` or `handleSend()` → creates session via `useCreateSession` mutation → sets `activeId`
2. `AgentPage` calls `useSessionMessages(activeId)` which fetches `GET /api/sessions/{id}/messages`
3. User sends message → `ChatView` sends via WebSocket → backend streams `text_delta`, `tool_call`, `gate_request` events
4. On `turn_completed`, `ChatView` invalidates the `['messages', sessionId]` query → refetches messages

## Providers

`ui/app/providers.tsx` wraps the app with `QueryClientProvider` (TanStack Query), `ThemeProvider` (next-themes), and `UserContext`.
