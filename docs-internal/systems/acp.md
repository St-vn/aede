---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# ACP — Agent Client Protocol

**Files:** `aede/acp/`

## Overview

The Agent Client Protocol enables aede to route chat turns to external agent subprocesses (Codex, Claude Code, Gemini, Antigravity, Cline, Cursor, Goose, OpenCode). Each agent runs as a local subprocess and communicates via JSON-RPC 2.0 over stdio.

The ACP transport was rewritten from blocking `subprocess.Popen` + `ThreadPoolExecutor` into an async JSON-RPC message-pump, fixing thread-pool exhaustion, pipe races, and event-loop blocking issues.

## ACP Client (`aede/acp/client.py`, 436 lines)

Async JSON-RPC message-pump over `asyncio.create_subprocess_exec`:

- **Stream reader limit:** `_STREAM_LIMIT = 16 MB` — the asyncio default of 64 KB overflows on real ACP NDJSON lines (file contents, tool results) (`aede/acp/client.py:20`)
- **Message-pump:** `_read_loop()` reads NDJSON line-by-line, `_dispatch()` routes by message shape
- **Pending requests:** `_pending: dict[int|str, asyncio.Future]` — outstanding requests keyed by id
- **Write serialization:** `_write_lock: asyncio.Lock` — concurrent sends never interleave
- **Streaming:** per-session sinks via `_session_sinks`, `prompt()` supports `on_update` callback for `agent_message_chunk` text
- **Cancel:** `cancel(session_id)` → `session/cancel` notification
- **Reentrant handlers:** `_register_default_handlers()` handles `session/request_permission` (auto-approves), `fs/read_text_file`, `fs/write_text_file`
- **Lifecycle:** `start()`, `initialize()`, `new_session(timeout=60.0)`, `aclose()`

## ACP Registry (`aede/acp/registry.py`, 119 lines)

Persistent config at `~/.aede/agents.json`. `AgentConfig` dataclass stores name, transport, command, args, credentials_ref, model_override. `seed_default_agents()` adds 7 base agents at startup (idempotent, never clobbers user edits).

## ACP Manager (`aede/acp/manager.py`, 91 lines)

Orchestrates connect/disconnect/switch lifecycle. `connect()` drives `drive_auth()` async generator, adopts the session id created during auth handshake. Auto-fallback on disconnect.

## ACP Chat Routing (`aede/provider.py:522-646`)

`AcpProvider` implements `Provider.stream_turn()` for ACP agents. Receives model ids from `ACP_MODEL_IDS` frozenset. Resolves base agent + sub-model override, manages disconnect/reconnect on model switch, builds prompt text via `_build_prompt_text()`.

## Current state

ACP chat routing is wired and functional, but the permissions bridge (`aede/acp/permissions.py`) is not the active path — auto-approval happens inside the client (`_default_permission`). A future transport rewrite is planned to address edge cases.
