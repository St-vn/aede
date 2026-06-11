---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# GateCard

**File:** `ui/components/chat/GateCard.tsx`

## Purpose

Approval gate UI — requests user permission before executing a tool. Rendered in ChatView when the server sends `gate_request`.

## States

- **Allow once**: Single-click approve for this invocation.
- **Always** dropdown: `allow_session`, `allow_project`, `allow_global` scopes.
- **Deny**: Reject tool execution.
- **Redirect**: Collapsible text input to tell the model what to do instead.

## Visual

Yellow warning accent border, `TriangleAlert` icon, tool name in monospace, args in a `pre` block, and action buttons in a flex row.

## Decision Flow

`onDecision({gateId, decision, message?})` → ChatView sends `gate_response` JSON over WebSocket → server resolves the `asyncio.Future` → agent resumes.
