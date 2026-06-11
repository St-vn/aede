---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Approval Gate

**File:** `aede/gate.py` (232 lines)

## GateDecision enum (`aede/gate.py:16-27`)

| Decision | Meaning |
|----------|---------|
| `ALLOW_ONCE` | Run once |
| `ALLOW_SESSION` | Allow for this process lifetime |
| `ALLOW_PROJECT` | Persist to `./aede.yml` |
| `ALLOW_GLOBAL` | Persist to `~/.aede/config.yml` |
| `DENY` | Reject |
| `REDIRECT` | Send user message to agent |
| `BATCH_APPROVE` | Approve all in batch |
| `BATCH_DENY` | Deny all in batch |

## PermissionStore (`aede/gate.py:29-87`)

Three scope layers: **Session** (in-memory), **Project** (`./aede.yml`), **Global** (`~/.aede/config.yml`). Session > Project > Global precedence. `load_from_config()` seeds from `auto_approve` list. Persistence via YAML write-back in `_persist_project()` / `_persist_global()`.

## GateBackend Protocol (`aede/gate.py:94-106`)

```python
@runtime_checkable
class GateBackend(Protocol):
    async def request(self, gate_id, tool_name, args, batch_count) -> tuple[GateDecision, str]: ...
```

Two implementations:
- **TerminalGateBackend** (`aede/gate.py:109-147`) — CLI implementation, runs `prompt_gate()` in a thread executor via `asyncio.get_event_loop().run_in_executor()`
- **WebSocketGateBackend** (`aede/server.py:27-56`) — sends gate request via WebSocket JSON, waits for response via `asyncio.Future`

## prompt_gate() (`aede/gate.py:167-211`)

Single-keypress approval via `_read_key()` which uses `msvcrt.getch()` on Windows, raw-mode `tty` on POSIX (`aede/gate.py:214-232`). Keys: A = allow once, W = always allow (then scope picker), D = deny, R = redirect (prompts for message), B = batch (then approve/deny).

## render_gate() (`aede/gate.py:150-164`)

Human-readable gate prompt string showing tool name, optional batch count, args, and available actions. MCP tools display `[server: <name>]` decoration.
