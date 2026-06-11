---
type: doc
tags: [docs, reference]
date_updated: 2026-06-10
---

# Tool Reference

## powershell

Execute a shell command.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cmd` | string | yes | The command to execute |

Gated. Uses the configured shell backend (`powershell`, `cmd`, or `wsl`).

## read_file

Read the contents of a file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | yes | Absolute or relative file path |

Returns the file content as UTF-8 text.

## write_file

Overwrite an existing file. Fails if the file does not exist — use `create_file` for new files.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | yes | File path |
| `content` | string | yes | New file content |

Gated.

## create_file

Create a new file. Fails if the file already exists — use `write_file` to overwrite.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | yes | File path |
| `content` | string | yes | File content |

Gated.

## list_dir

List directory contents with file names, sizes, and modification times.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | yes | Directory path |
| `depth` | integer | no | Recursion depth (default: 1) |

## search_files

Search for a regex pattern across files using ripgrep.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pattern` | string | yes | Regex pattern to search for |
| `path` | string | yes | Directory to search in |

Returns matches with file path and line number.

## fetch_url

HTTP GET a URL and return the page content as text. Does not execute JavaScript.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | yes | URL to fetch |

HTML pages return extracted visible text. Use `web_search` first to find URLs.

## web_search

Search the web using DuckDuckGo. No API key required.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Search query |
| `count` | integer | no | Number of results (default: 5) |

Returns titles, URLs, and snippets.

## spawn_subagent

Spawn a subagent to work on a task independently.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_name` | string | yes | Name of a loaded agent |
| `task` | string | yes | Task description for the subagent |

The subagent runs in an isolated loop with its own filtered tools and model.

## session_search

Search past session message history by keyword using FTS5 full-text search.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | yes | Keyword or phrase to search for |
| `limit` | integer | no | Max results (default: 10) |

Returns matching messages with ±5 message context window.

## write_learning

Persist a learning to the long-term memory store.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | yes | `anti-pattern`, `failed-approach`, `root-cause`, or `config-correction` |
| `content` | string | yes | Free-text body of the learning |
| `source` | string | yes | `user`, `auto_learned`, `test_failure`, or `tool_error` |
| `source_session_id` | string | no | Session that produced this learning |

Gated. The verifier runs automatically after writing.
