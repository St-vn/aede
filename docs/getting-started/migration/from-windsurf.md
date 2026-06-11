---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from Windsurf

Windsurf stores agents as plain markdown rules files, skills in YAML frontmatter files, and MCP config in JSON.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents (Rules) | `~/.windsurf/rules/*.md` | `/import agent <path> --source windsurf` |
| Skills | `~/.windsurf/skills/` (flat `.md` files) | `/import skill <path> --source windsurf` |
| MCP | `~/.codeium/windsurf/mcp_config.json` | `/import mcp --source windsurf` |

Note the MCP config is under `~/.codeium/`, not `~/.windsurf/`.

## Quick Start

```
/import all --source windsurf
```

This imports all `.md` rule files from `~/.windsurf/rules/`, all skills from `~/.windsurf/skills/`, and MCP servers from `~/.codeium/windsurf/mcp_config.json`.

## Importing Agents

Windsurf rules are plain markdown files with no YAML frontmatter:

```
/import agent ~/.windsurf/rules/python-standards.md --source windsurf
```

Name synthesis: when the filename is not `AGENTS.md` or `GEMINI.md`, the name is derived from the file stem. `python-standards.md` → name `python-standards`.

The import adds fresh frontmatter:

```yaml
---
name: python-standards
description: Imported from Windsurf
model: inherit
---
```

## Importing Skills

Windsurf skills are flat `.md` files with YAML frontmatter:

```
/import skill ~/.windsurf/skills/search.md --source windsurf
```

Field renames:

| Windsurf | aede |
|---|---|
| `allowed-tools` | `allowed_tools` |
| `trigger` | `trigger_phrases` |

The `hidden` field is commented out.

## Importing MCP Servers

```
/import mcp --source windsurf
```

Reads `~/.codeium/windsurf/mcp_config.json`. The `serverUrl` field is mapped to aede's `url`. Windsurf-style `${env:VAR}` and `${file:path}` interpolation tokens are preserved verbatim.

## What Gets Dropped

Nothing from agents (plain markdown, no frontmatter to drop). Skills drop `hidden`. MCP drops no Windsurf-specific fields.

## Limitations

- Agent names are synthesised from the filename — not from file content.
- MCP config is in a different tree (`~/.codeium/windsurf/`) from rules (`~/.windsurf/rules/`).
- MCP env vars with `${env:VAR}` and `${file:path}` syntax are passed through verbatim.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
