---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Tool System

**File:** `aede/tools/router.py` (523 lines)

## ToolRouter (`aede/tools/router.py:38`)

Central registry mapping `name → Callable`. Built at construction via `_build_registry()`. Manages gating, validation, execution, truncation, and schema serving.

## Gated tools (`aede/tools/router.py:18`)

```python
GATE_TOOLS = {"powershell", "write_file", "create_file", "write_learning"}
```

## Core tools

| Tool | File | Gate | Description |
|------|------|------|-------------|
| `powershell` | `tools/powershell.py:run_powershell()` | Yes | Execute shell command (powershell/cmd/wsl) |
| `read_file` | `tools/files.py:read_file()` | No | UTF-8 file read |
| `write_file` | `tools/files.py:write_file()` | Yes | Overwrite existing file |
| `create_file` | `tools/files.py:create_file()` | Yes | Create new file (fails if exists) |
| `list_dir` | `tools/files.py:list_dir()` | No | Directory listing with depth |
| `search_files` | `tools/search.py:search_files()` | No | ripgrep wrapper |
| `fetch_url` | `tools/web.py:fetch_url()` | No | HTTP GET (rejects HTML/SPA) |
| `web_search` | `tools/web.py:web_search()` | No | DuckDuckGo search |

## Extended tools

| Tool | File | Gate | Description |
|------|------|------|-------------|
| `spawn_subagent` | `router.py:112-146` | No | Delegates to loaded agent, depth=1 |
| `session_search` | `tools/search.py:session_search()` | No | FTS5 search over past messages |
| `write_learning` | `router.py:326-357` | Yes | Persist learning + verifier integration |

## MCP tools

Auto-discovered as `mcp__<server>__<name>` prefix. Gate status depends on server's `trusted` flag (`aede/tools/router.py:263-276`). Registered via `register_mcp_tools()` (line 195). Lazy bridge resolution via `_resolve_bridge()` (line 74) enables WebSocket sessions to survive bridge restarts.

## ToolResult (`aede/tools/router.py:29-35`)

```python
@dataclass
class ToolResult:
    status: str       # "success" | "error"
    output: str
    duration_ms: int
```

## Tool validation (`aede/tools/router.py:217-261`)

- `validate_name()` — raises `UnknownToolError` if not in registry (`aede/tools/router.py:217-220`)
- `validate_args()` — checks required fields + JSON schema types via lazy Pydantic (`aede/tools/router.py:222-261`). Errors return to model as `ToolResult(status="error")`.

## Tool schemas (`aede/tools/router.py:360-522`)

`_TOOL_SCHEMAS` dict — Anthropic-format JSON schemas. Single source of truth for both LLM function-calling and Pydantic validation.

## Output truncation (`aede/tools/router.py:307-313`)

Tool outputs capped at `tool_output_max_tokens * 4` characters. Truncated output includes token count note.
