---
type: doc
tags: [docs, features]
date_updated: 2026-06-20
---

# Tools

aede provides a set of built-in tools that the agent can invoke during a conversation.

## Core Tools

| Tool | Gated | Description |
|------|-------|-------------|
| `powershell` | Yes | Execute a PowerShell, CMD, or WSL command |
| `read_file` | No | Read a UTF-8 file at a given path (supports `offset`/`limit` for partial reads) |
| `write_file` | Yes | Overwrite an existing file |
| `create_file` | Yes | Create a new file (fails if it exists) |
| `edit` | Yes | Apply an exact string replacement to an existing file; prefer over `write_file` for modifications |
| `list_dir` | No | List directory contents with configurable depth |
| `glob` | No | Find files matching a glob pattern, sorted by newest first |
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

## User Interaction Tools

These tools do not require gate approval — they are part of the conversation flow:

| Tool | Description |
|------|-------------|
| `question` | Unified question tool. Supports `text`, `single`, and `multi` question types with optional custom answers, notes, and multiple questions per call. |
| `ask_user` | Legacy alias — free-form text question. |
| `ask_user_choices` | Legacy alias — single-choice from a list. |
| `ask_user_confirm` | Legacy alias — yes/no question. |

The three legacy tools are still accepted; prefer `question` for new agent definitions as it supports richer question types and batching.

In `auto` mode, these questions are answered automatically with safe defaults so the agent can keep running hands-free.

## Tool Approval

Gated tools require user approval before execution. The approval prompt shows the tool name and arguments, letting you allow once, allow permanently at various scopes, or deny. See [Security](../user-guide/security.md) for details.

## MCP Tools

Tools from MCP servers are auto-discovered and registered with the prefix `mcp__<server>__<name>`. Their gate status depends on the server's `trusted` flag. See [MCP](mcp.md).

## Output Truncation

Tool outputs are capped at `tool_output_max_tokens * 4` characters. Truncated output includes a note with the estimated token count.

## Error Handling

Errors are returned to the model as results (never hidden). The model decides whether to retry with corrected parameters, ask the user, or report failure. Never retry on hallucinated tool names — unknown names cannot become valid by retrying.
