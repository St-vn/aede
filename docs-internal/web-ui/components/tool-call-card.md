---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# ToolCallCard

**File:** `ui/components/chat/ToolCallCard.tsx`

## Purpose

Displays a tool invocation with status, output, and streaming content. Rendered inline between messages in ChatView.

## States

| Status | Icon | Label | Expandable |
|---|---|---|---|
| `running` | Spinner (`Loader2`) | "running..." | No |
| `success` | Check (`CheckCircle2`) | — | Yes (collapsible output) |
| `error` | X (`XCircle`) | "error" | Yes (collapsible error) |
| `denied` | Ban (`Ban`) | "denied" | No |

## Running/Streaming

During execution, `streamingOutput` is rendered as a monospace block. The card shows a chevron + tool name + status icon.

## Collapsed/Expanded

On success or error, the card becomes a `Collapsible` — clickable to reveal tool output in a `pre` block with `durationMs` displayed in the bottom-right corner.
