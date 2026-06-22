---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from Cursor

Cursor uses `.mdc` files with YAML frontmatter for rules (agents) and a JSON config for MCP servers. It does not have a skills system.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents (Rules) | `~/.cursor/rules/*.mdc` | `/import agent <path> --source cursor` |
| Skills | — | Not supported |
| MCP | `~/.cursor/mcp.json` | `/import mcp --source cursor` |

## Quick Start

```
/import all --source cursor
```

This imports all `.mdc` files from `~/.cursor/rules/` and MCP servers from `~/.cursor/mcp.json`.

## Importing Agents

Cursor `.mdc` files have YAML frontmatter with `description`, `globs`, and `alwaysApply` fields:

```
/import agent ~/.cursor/rules/python-rules.mdc --source cursor
```

The name is derived from the file stem (slugified): `python-rules.mdc` → `python-rules`.

Output frontmatter:

```yaml
---
name: python-rules
description: Python best practices
model: inherit
# globs:
#   - '**/*.py'
# alwaysApply: true
---
```

Auto-detection: if `--source` is omitted and the file has `.mdc` extension, aede automatically uses the Cursor importer.

## What Gets Dropped

Two Cursor-specific fields are **commented out** in the output frontmatter:

| Dropped Field | Reason |
|---|---|
| `globs` | aede doesn't scope agents to file glob patterns |
| `alwaysApply` | aede agents are always available when selected |

## Importing MCP Servers

```
/import mcp --source cursor
```

Reads `~/.cursor/mcp.json` and merges servers into `~/.aede/config.yml`. The `url` field (used by remote Cursor MCP servers) maps directly to aede's `url`.

## Limitations

- No skills import available.
- Cursor's `globs` field has no aede equivalent — rules apply to all files.
- `alwaysApply` has no equivalent — all aede agents are manually selected.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
