---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Shared MCP Import Logic

**File:** `aede/import_/mcp.py`

## JSON Normalizer (`import_mcp_from_json()`, line 24)

Handles JSON configs from Claude Code, Antigravity, Cursor, and Windsurf. Reads the `mcpServers` dict and normalizes per-server fields:

- `serverUrl` (Antigravity/Windsurf) → `url`
- `url` (Cursor) → `url`
- `command` (list form → first element + `args`) — Claude Code sometimes uses array form
- `env` — passed through verbatim (no `${env:}` / `${file:}` interpolation)
- `trusted` — passed through
- `disabled_tools` — passed through
- `enabled` — always set to `True`

## Codex TOML Parser (`import_mcp_from_toml()`, line 134)

Reads `[mcp_servers]` table from TOML. Same field mapping as JSON, plus `enabled` defaults to `True` when absent. Drops 10 Codex-specific fields silently (`_CODEX_DROPPED_FIELDS`, line 10-21).

## Duplicate Detection

Both JSON and TOML parsers check if a server with the same name already exists in the dest config. If so, prompts "MCP server {name!r} already exists. Overwrite? [y/N]". Declining sets `was_skipped=True`.

## Dry-Run Mode

`/import mcp --dry-run` (`aede/commands.py:1008-1040`) lists servers that would be imported without writing anything. Iterates each JSON key or TOML key and prints name + command/URL.

## Output

All MCP servers are written to `~/.aede/config.yml` under the `mcp_servers` key. The config is serialized as YAML via `yaml.dump()`.
