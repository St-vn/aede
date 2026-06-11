---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# Hooks Reference

14 custom hooks in `ui/hooks/`. All use TanStack Query (useQuery/useMutation) wrapping `apiFetch()` from `ui/lib/api.ts`.

| File | Hook Exports | Purpose | Query Keys |
|---|---|---|---|
| `useSession.ts` | `useSessions`, `useSessionMessages`, `useCreateSession`, `useDeleteSession`, `useRenameSession` | Session CRUD and message history | `['sessions']`, `['messages', sessionId]` |
| `useConfig.ts` | `useConfig`, `useConfigSources`, `useUpdateConfig` | Config read/write | `['config']`, `['config', 'sources']` |
| `useModels.ts` | `useModels`, `useAddModel`, `useDeleteModel`, `useUpdateModels`, `useResetModels` | Model presets CRUD | `['models']` |
| `useAgents.ts` | `useAgents`, `useCreateAgent`, `useUpdateAgent`, `useUploadAgent`, `useDeleteAgent` | Agent definitions CRUD | `['agents']` |
| `useSkills.ts` | `useSkills`, `useCreateSkill`, `useUpdateSkill`, `useUploadSkill`, `useDeleteSkill` | Skill definitions CRUD | `['skills']` |
| `useMcpServers.ts` | `useMcpServers`, `useAddMcpServer`, `useUpdateMcpServer`, `useDeleteMcpServer`, `useRestartMcpServers` | MCP server management | `['mcp', 'servers']` |
| `useProjects.ts` | `useProjects`, `useAddProject`, `useRemoveProject`, `useDeleteProjectFolder`, `useRemoveProjectRepo` | Project directory management | `['projects']` |
| `useCredentials.ts` | `useCredentials`, `useAddCredential`, `useDeleteCredential` | Credential vault (names only) | `['credentials']` |
| `useMemory.ts` | `useLearnings`, `useAddLearning`, `useDeleteLearning` | Learning store CRUD | `['learnings']` |
| `useTokens.ts` | `useSessionTokens` | Per-session token usage | `['tokens', sessionId]` |
| `useWebSocket.ts` | `useWebSocket` | WebSocket connection and send | — (no queries) |
| `useWorkspaceInfo.ts` | `useWorkspaceInfo` | CWD, git root, project name | `['workspaceInfo', sessionId?, projectDir?]` (60s staleTime) |
| `useWorkspaceFiles.ts` | `useWorkspaceFiles` | File list in workspace | `['workspaceFiles', sessionId?, projectDir?]` |
| `useAcpAgents.ts` | `useConfigs`, `useStatus`, `useConnect`, `useDisconnect`, `useRegister`, `useDeleteAgent` | ACP agent lifecycle | `['acp', 'configs']`, `['acp', 'status']` (polls every 5s) |
