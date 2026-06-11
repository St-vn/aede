---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# Web UI Testing

## Test Framework

Vitest 4.1.8 with `@testing-library/react` and `jsdom`. Configuration in `ui/vitest.config.ts`. E2E tests via Playwright 1.60 in `ui/e2e/`.

## Unit/Integration Tests

Located in `ui/__tests__/`:

| Directory | Contents |
|---|---|
| `ui/__tests__/` root | `AgentPage.test.tsx`, `Layout.test.tsx` |
| `ui/__tests__/chat/` | Chat component tests |
| `ui/__tests__/input/` | Input component tests |
| `ui/__tests__/sidebar/` | Sidebar component tests |
| `ui/__tests__/empty/` | Empty state tests |
| `ui/__tests__/hooks/` | Hook tests |
| `ui/__tests__/lib/` | Utility tests |
| `ui/__tests__/contexts/` | Context tests |

## Coverage Gaps

- No tests for `SettingsModal` tabs (ConfigTab, ModelsTab, etc.)
- No tests for `GateCard` decision flows
- No tests for `ToolCallCard` streaming output rendering
- No tests for `CodeBlock` Shiki integration
- No tests for WebSocket `useWebSocket` retry/connectivity edge cases
- E2E tests in `ui/e2e/` but not documented in package.json scripts
