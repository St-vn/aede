---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# ChatView

**File:** `ui/components/chat/ChatView.tsx`

## Purpose

Renders the message history, streaming assistant output, tool calls, gate approval cards, and the input bar for an active session.

## Message Rendering

Messages from the server query `useSessionMessages(sessionId)` are rendered as:
- `UserMessage` — user text messages
- `AssistantMessage` — assistant responses with optional `thinking` block
- Branch point dividers — horizontal rule with "Branch point" label when `is_branch_point` is true

## Streaming

`useWebSocket(sessionId, onEvent)` handles events:
- `text_delta` → appended to `streamingText`
- `thinking_delta` → appended to `streamingThinking`
- `tool_call` → added to `toolCalls[]` array with `status: 'running'`
- `tool_output_delta` → appended to the matching tool call's `streamingOutput`
- `tool_result` → updates tool call status and output
- `gate_request` → shows `GateCard`
- `turn_completed` → resets streaming state, invalidates messages query

## Pending Messages

User messages sent via WebSocket are optimistically added to `pendingMessages[]` and displayed as `UserMessage` until the server round-trip completes and messages refetch.

## Scrolling

Auto-scrolls to bottom when `messages` or `streamingText` changes, using the ScrollArea viewport element.
