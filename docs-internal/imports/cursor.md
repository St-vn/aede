---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Cursor Import

**File:** `aede/import_/cursor.py:19` — `import_cursor_mdc()`

## Source Files

Cursor stores rules as `.mdc` files in `~/.cursor/rules/`. These files have YAML frontmatter with `description`, `globs`, and `alwaysApply` fields followed by markdown body.

## Auto-Detection

The `.mdc` extension triggers Cursor import automatically in `_import_one_agent()` (`aede/commands.py:926`).

## Field Mapping

- `description` → preserved as agent description
- `globs` → commented out (`# globs: ...`) in output frontmatter
- `alwaysApply` → commented out (`# alwaysApply: ...`)

`_UNSUPPORTED_FIELDS` (`aede/import_/cursor.py:8`): `{"globs", "alwaysApply"}`.

The agent `name` is slugified from the file stem. `model` defaults to `"inherit"`.

## Skills

Cursor has no skills entry (`_IMPORT_ALL_LAYOUT` assigns `None` at `aede/commands.py:1077`).

## MCP Config

From `~/.cursor/mcp.json` — standard JSON format with `mcpServers` dict. Uses `import_mcp_from_json()` with `url` field mapping (Cursor uses `url` key, not `serverUrl`).
