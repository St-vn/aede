---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# Tools

aede provides a set of built-in tools that the agent can invoke during a conversation.

## Core Tools

| Tool | Gated | Description |
|------|-------|-------------|
| `powershell` | Yes | Execute a PowerShell, CMD, or WSL command |
| `read_file` | No | Read a UTF-8 file at a given path |
| `write_file` | Yes | Overwrite an existing file |
| `create_file` | Yes | Create a new file (fails if it exists) |
| `list_dir` | No | List directory contents with configurable depth |
| `search_files` | No | Search for a regex pattern across files (ripgrep) |
| `fetch_url` | No | HTTP GET a URL, return content as text |
| `web_search` | No | Search the web via DuckDuckGo |

## Extended Tools

| Tool | Gated | Description |
|------|-------|-------------|
| `spawn_subagent` | No | Delegate a task to a loaded subagent |
| `session_search` | No | FTS5 search over past session messages |
| `select_context` | No | Pull relevant context from up to 4 sources (learnings, sessions, docs, files) in one call. See [context-selection](context-selection.md). |
| `write_learning` | Yes | Persist a learning to the memory store |

## Tool Approval

Gated tools require user approval before execution. The approval prompt shows the tool name and arguments, letting you allow once, allow permanently at various scopes, or deny. See [Security](../user-guide/security.md) for details.

## MCP Tools

Tools from MCP servers are auto-discovered and registered with the prefix `mcp__<server>__<name>`. Their gate status depends on the server's `trusted` flag. See [MCP](mcp.md).

## Output Truncation

Tool outputs are capped at `tool_output_max_tokens * 4` characters. Truncated output includes a note with the estimated token count.

## Error Handling

Errors are returned to the model as results (never hidden). The model decides whether to retry with corrected parameters, ask the user, or report failure. Never retry on hallucinated tool names — unknown names cannot become valid by retrying.
