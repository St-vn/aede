---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# MCP Bridge

**File:** `aede/mcp/client.py` (289 lines)

## MCPBridge class (`aede/mcp/client.py:82-289`)

Manages multiple MCP server subprocesses. Each server runs in its own background daemon thread with an `asyncio` event loop. Uses the `mcp` Python SDK for transport and session management.

### Key methods

| Method | Description | Line |
|--------|-------------|------|
| `spawn_all()` | Spawn all enabled servers concurrently; returns list of failed names | 165-195 |
| `discovered_tools()` | Return `[(full_name, server_name, cfg, schema)]` for ToolRouter registration | 197-218 |
| `call_sync(server, tool, args)` | Thread-safe synchronous call via `run_coroutine_threadsafe` | 220-242 |
| `shutdown_all()` | Graceful close + force-kill residual processes | 244-289 |

### Tool naming

MCP tools prefixed with `mcp__<server>__<name>` to avoid collisions with built-in tools (`aede/mcp/client.py:211`). Disabled tools per server filtered out (`aede/mcp/client.py:209`).

### Environment variable expansion (`aede/mcp/client.py:26-38`)

`expand_env_vars()` expands `${VAR}` and `${VAR:-default}` patterns in server command, args, env, and URL at spawn time. Raises `KeyError` if a `${VAR}` without default is not found in `os.environ`.

### Lazy bridge resolution

`ToolRouter._get_bridge` callable (`aede/tools/router.py:74-83`) enables lazy resolution — resolved on first tool call, not at router construction. This allows WebSocket sessions to survive bridge restarts.

### Config parsing (`aede/mcp/client.py:52-79`)

`_parse_mcp_servers()` supports both `mcp_servers` and `mcpServers` keys. Each server has: `command`, `args`, `env`, `trusted` (bool — determines gate behavior), `enabled` (bool — server skipped if false), `disabled_tools` (list — specific tools to hide), `url` (str — for SSE/WebSocket servers).

### Timeouts

| Constant | Value | Description |
|----------|-------|-------------|
| `MCP_TIMEOUT` | 10s | Per-server spawn/initialization |
| `CALL_TIMEOUT` | 60s | Per-tool-call timeout |
| `SHUTDOWN_GRACE` | 5s | Grace period for shutdown |

### Import

MCP servers can be imported from Claude Code (`~/.claude/mcp.json`) via `/import mcp`. Reads config, normalizes to aede YAML format, merges into `~/.aede/config.yml`. Supports stdio transport. Fidelity: ~90%.
