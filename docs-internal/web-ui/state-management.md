---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# State Management

## TanStack Query (Server State)

Query keys and cache invalidation strategy:

| Query Key | Endpoint | Invalidated By |
|---|---|---|
| `['sessions']` | `GET /api/sessions` | `useCreateSession`, `useDeleteSession`, `useRenameSession` |
| `['messages', sessionId]` | `GET /api/sessions/{id}/messages` | WebSocket `turn_completed` event |
| `['config']` | `GET /api/config` | `useUpdateConfig` |
| `['config', 'sources']` | `GET /api/config/sources` | — |
| `['agents']` | `GET /api/agents` | `useCreateAgent`, `useUpdateAgent`, `useDeleteAgent`, `useUploadAgent` |
| `['skills']` | `GET /api/skills` | `useCreateSkill`, `useUpdateSkill`, `useDeleteSkill`, `useUploadSkill` |
| `['mcp', 'servers']` | `GET /api/mcp/servers` | `useAddMcpServer`, `useUpdateMcpServer`, `useDeleteMcpServer`, `useRestartMcpServers` |
| `['models']` | `GET /api/models` | `useAddModel`, `useDeleteModel`, `useUpdateModels`, `useResetModels` |
| `['projects']` | `GET /api/projects` | `useAddProject`, `useRemoveProject`, `useDeleteProjectFolder`, `useRemoveProjectRepo` |
| `['credentials']` | `GET /api/credentials` | `useAddCredential`, `useDeleteCredential` |
| `['learnings']` | `GET /api/learnings` | `useAddLearning`, `useDeleteLearning` |
| `['tokens', sessionId]` | `GET /api/sessions/{id}/tokens` | — (read-only, enabled only when sessionId is set) |
| `['workspaceInfo', sessionId?, projectDir?]` | `GET /api/workspace/info` | — (60s staleTime) |
| `['workspaceFiles', sessionId?, projectDir?]` | `GET /api/workspace/files` | — |
| `['acp', 'configs']` | `GET /api/acp/configs` | `useConnect`, `useDisconnect`, `useRegister`, `useDeleteAgent` |
| `['acp', 'status']` | `GET /api/acp/status` | `useConnect`, `useDisconnect` (polls every 5s) |

## Client State (React State)

All in `AgentPage.tsx` and `ChatView.tsx`:

- `activeId` / `activeProjectDir` / `initialMessage` — navigation state
- `streamingText` / `streamingThinking` — incremental WebSocket text deltas
- `toolCalls` — running/completed tool calls with streaming output
- `gate` — active gate approval request
- `pendingMessages` — optimistically displayed user messages awaiting server round-trip
- `settingsOpen` / `settingsTab` — settings modal visibility

## Zustand / Context

`UserContext.tsx` provides additional client state. The `Class-variance-authority` and `tailwind-merge` utilities in `utils.ts` handle className merging.
