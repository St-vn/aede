---
type: doc
tags: [docs, features]
date_updated: 2026-06-16
---

# HTTP Server

aede includes a built-in FastAPI HTTP server that powers the Web UI and can be used for integrations.

## Starting

```bash
aede --serve --host 127.0.0.1 --port 8000
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ws/sessions/{id}` | WebSocket | Interactive agent turns with streaming |
| `/api/sessions` | GET | List sessions |
| `/api/sessions/{id}` | DELETE | Delete a session |
| `/api/config` | GET/PUT | Get or update effective config |
| `/api/gate/respond` | POST | Approval gate response from UI |
| `/api/acp/configs` | GET/POST | ACP agent configuration management |
| `/api/acp/connect` | POST | Connect an ACP agent |
| `/api/acp/disconnect` | POST | Disconnect an ACP agent |
| `/api/mcp/servers` | GET/POST | List or add MCP servers |
| `/api/mcp/servers/{name}` | PUT/DELETE | Update or remove MCP servers |
| `/api/mcp/restart` | POST | Restart the MCP bridge |
| `/api/soul` | GET/PATCH | Read or update SOUL.md at requested scope (`?scope=global\|project&project_dir=...`) |
| `/api/soul/open` | POST | Open SOUL.md in OS default editor |
| `/api/project-instructions` | GET/PUT | Read or write AGENTS.md / CLAUDE.md at requested scope |
| `/api/project-instructions/open` | POST | Open instructions file in OS editor |

## WebSocket

The WebSocket endpoint at `/ws/sessions/{id}` provides real-time bidirectional communication:

- Client sends user messages as JSON
- Server streams token deltas as `text_delta` events
- Console output is sent as `console_message` events
- Thinking blocks are streamed as `thinking_delta` events (with `seq` for per-step ordering)
- Tool calls are streamed as `tool_call` events (with `seq` for execution order, inline diffs for Edit operations)
- Tool results are streamed as `tool_result` events (with `status`, `output`, `duration_ms`)
- Gate requests are sent as `gate_request` events, and the client responds with `gate_response`
- Turn completion sends `turn_completed`, `context_usage`, and `learnings_injected` events
- Turns with pending gates survive WebSocket disconnect/reconnect — the gate rebinds to the new socket and re-sends unanswered gate requests

## CORS

The server allows requests from `http://localhost:3000` and `http://127.0.0.1:3000` for development with the Web UI dev server.
