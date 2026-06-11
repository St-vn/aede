---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migration Overview

aede can import agents, skills, and MCP server configurations from six popular agent harnesses. Use the `/import` command to bring your existing setup into aede.

## Supported Sources

| Source | Agents | Skills | MCP | Config Format |
|---|---|---|---|---|
| [Claude Code](./from-claude-code) | ✓ | ✓ | ✓ | YAML frontmatter + JSON |
| [OpenCode](./from-opencode) | ✓ | — | — | YAML frontmatter |
| [Antigravity](./from-antigravity) | ✓ | ✓ | ✓ | Plain markdown + JSON |
| [Codex](./from-codex) | ✓ | ✓ | ✓ | Plain markdown + TOML |
| [Cursor](./from-cursor) | ✓ | — | ✓ | `.mdc` frontmatter + JSON |
| [Windsurf](./from-windsurf) | ✓ | ✓ | ✓ | Plain markdown + JSON |

## Quick Start

Migrate everything in one command:

```
/import all --source claude-code
/import all --source antigravity
/import all --source codex
/import all --source windsurf
```

Replace `--source` with any of the six harnesses listed above. The command discovers agents, skills, and MCP servers at their standard locations and imports them without overwriting existing files.

## Import Types

- **`/import agent <path> [--source X] [--dest DIR]`** — Import an agent or rules file
- **`/import skill <path> [--source X] [--dest DIR]`** — Import a skill file
- **`/import mcp [path] [--source X] [--dry-run]`** — Import MCP servers from a config file
- **`/import all [--source X] [--dry-run]`** — Import everything from standard locations

## What Gets Imported

**Agents** become aede agent files (`~/.aede/agents/<name>.md`) with YAML frontmatter. Name is preserved from the source when available, or synthesised from the filename/directory.

**Skills** become aede skill files (`~/.aede/skills/<name>.md`) with YAML frontmatter. Field mappings and dropped fields vary by source — see the source-specific guide for details.

**MCP servers** are merged into `~/.aede/config.yml` under the `mcp_servers` key. The importer prompts before overwriting an existing server with the same name.

## See Also

- [`/import` command reference](../reference/import-commands)
