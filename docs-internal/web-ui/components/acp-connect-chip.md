---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# AcpConnectChip

**File:** `ui/components/input/AcpConnectChip.tsx`

## Purpose

Auto-connects to an ACP agent when the selected model belongs to a known ACP-capable agent. Displays connection status as a compact chip next to the model selector.

## Supported Agents

`ACP_AGENTS` (line 7): `['codex', 'claude-code', 'gemini', 'agy', 'cline', 'cursor', 'goose']`

## Behavior

- **Auto-connect**: On mount, if the model prefix matches a supported agent and no connection exists, automatically triggers `useConnect().mutate(agent)`.
- **Connected state**: Green WiFi icon + "Connected" label with disconnect button.
- **Pending state**: Spinner + "Connecting" label.
- **Error state**: Red "Failed" label — clickable to retry.
- **Unsupported**: Returns `null` when model doesn't match any ACP agent.
