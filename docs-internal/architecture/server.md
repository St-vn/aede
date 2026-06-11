---
type: internal-doc
tags: [docs-internal, architecture]
date_updated: 2026-06-10
---

# Web Server

**File:** `aede/server.py` (1573 lines)

## FastAPI application

Serves the web UI (`ui/out/` as static files) and exposes REST + WebSocket endpoints for browser-based interaction with the agent.

## REST endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/sessions` | GET/POST | List/create sessions |
| `/api/sessions/{id}` | GET/DELETE/PATCH | Session CRUD |
| `/api/sessions/{id}/messages` | GET | Message history (includes inherited parent messages via `_walk_parent_messages` at line 439) |
| `/api/sessions/{id}/tokens` | GET | Per-turn token usage |
| `/api/config` | GET/PUT | Read/update config |
| `/api/config/sources` | GET | Config source tracking |
| `/api/config/open` | POST | Open config in OS editor |
| `/api/projects` | GET/POST | Project CRUD |
| `/api/projects/{id}` | DELETE | Delete project |
| `/api/credentials` | GET/POST/DELETE | Credentials vault |
| `/api/learnings` | GET/POST/DELETE | Learnings store |
| `/api/agents` | GET/POST/PUT/DELETE | Agent file CRUD + upload |
| `/api/skills` | GET/POST/PUT/DELETE | Skill file CRUD + upload |
| `/api/models` | GET/POST/DELETE/PUT | Model preset management |
| `/api/mcp/servers` | GET/POST/PUT/DELETE | MCP server management |
| `/api/acp/configs` | GET | ACP agent configs |
| `/api/acp/connect` | POST | Connect ACP agent |
| `/api/acp/disconnect` | POST | Disconnect ACP agent |
| `/api/acp/status` | GET | ACP connection status |
| `/api/workspace/pick-directory` | POST | Native OS directory picker |
| `/api/workspace/browse` | POST | Directory traversal for picker |
| `/api/workspace/info` | GET | Workspace metadata |
| `/api/workspace/files` | GET | Tracked + untracked file list |

## WebSocket endpoint

`/ws/sessions/{session_id}` — handles interactive agent turns:

- **Receives** `user_message` with content + optional per-turn model override
- **Sends** `text_delta` (streamed tokens), `thinking_delta`, `console_message`, `tool_output_delta`, `gate_request`, `error`, `turn_completed`, `context_usage`, `learnings_injected`
- **Receives** `gate_response` with decision + redirect_msg
- Runs `agent.run_turn()` in an `asyncio.create_task()` background task
- On disconnect, cancels the running turn task (`aede/server.py:277-278`)

## WebSocket Gate Backend (`aede/server.py:27-56`)

Sends gate requests as `gate_request` JSON messages, waits for response via `asyncio.Future`. Non-blocking — the UI presents the tool approval prompt while the agent awaits the future.

## WebSocket Console (`aede/server.py:59-94`)

Redirects `console.print()` output to Web UI. Streaming tokens (`end=""`) sent as `text_delta` events. Full lines sent as `console_message`. Tool output streaming via `stream_tool_output()`.

## CORS

Allow origins: `http://localhost:3000`, `http://127.0.0.1:3000` (`aede/server.py:18-24`)

## Directory picker (`aede/server.py:1366-1380`)

Server-side Python script using `tkinter.filedialog.askdirectory()` — launches a native OS directory picker on the server.

## @[filename] resolution (`aede/server.py:1438-1462`)

`_resolve_file_mentions()` replaces `@[filename]` markers in user messages with file content from the session's project directory. Only resolves within the project root; files >100KB skipped.
