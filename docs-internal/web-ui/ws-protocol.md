---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# WebSocket Protocol

**Endpoint:** `ws://localhost:8000/ws/sessions/{session_id}` (derived from `API_BASE`, `ui/lib/api.ts:4`)

**Client:** `useWebSocket()` hook (`ui/hooks/useWebSocket.ts:7`)

## Client → Server Events

| type | Fields | Description |
|---|---|---|
| `user_message` | `content: string`, `model?: string` | Send a user message for an active session. `model` enables per-turn model override. |
| `user_turn` | `content: string`, `model?: string` | Alternative format; the hook maps `user_turn` → `user_message` before sending (`useWebSocket.ts:55-58`). |
| `gate_response` | `gate_id: string`, `decision: string`, `redirect_msg?: string` | Respond to a pending gate approval request. |

## Server → Client Events

| type | Fields | When |
|---|---|---|
| `text_delta` | `text: string` | Streaming token output during assistant response. |
| `thinking_delta` | `text: string` | Streaming thinking/reasoning block. |
| `console_message` | `content: string` | Non-streaming console output (tool header, status lines). Rich formatting stripped client-side. |
| `tool_call` | `id: string`, `name: string`, `args: object` | A tool was invoked. |
| `tool_output_delta` | `call_id: string`, `text: string` | Streaming tool output. |
| `tool_result` | `id: string`, `status: string`, `output?: string`, `duration_ms?: number` | Tool completed with result. |
| `gate_request` | `gate_id: string`, `tool_name: string`, `args: object`, `batch_count: number` | Tool needs approval. Client must respond with `gate_response`. |
| `turn_completed` | — | Agent finished processing; client should invalidate messages query. |
| `context_usage` | `used: number`, `total: number` | Context window usage after turn completion. |
| `learnings_injected` | `count: number` | Number of learnings injected after turn. |
| `error` | `message: string` | Error during processing. |

## Server Implementation

`aede/server.py:104-286` — `websocket_turn()` handler. Creates `WebSocketGateBackend` and `WebSocketConsole` adapters for each connection. Runs `agent.run_turn()` as an async task and uses `add_done_callback` to emit `turn_completed` on completion.

## Retry Logic

The client retries WebSocket sends up to 5 seconds (100ms intervals) if the socket isn't OPEN yet (`useWebSocket.ts:70-88`).
