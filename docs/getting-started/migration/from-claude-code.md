---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from Claude Code

Claude Code is the closest source to aede — both use YAML frontmatter `.md` files with the same agent schema. Most fields map 1:1.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents | `~/.claude/agents/*.md` | `/import agent <path>` |
| Skills | `~/.claude/skills/` (dirs with `SKILL.md`) | `/import skill <path>` |
| MCP | `~/.claude/mcp.json` | `/import mcp --source claude-code` |

## Quick Start

```
/import all --source claude-code
```

This imports everything from `~/.claude/agents/`, `~/.claude/skills/`, and `~/.claude/mcp.json` in one pass.

## Importing Agents Individually

Claude Code agent files have YAML frontmatter. aede maps them 1:1:

```
/import agent ~/.claude/agents/my-researcher.md
```

Output: `~/.aede/agents/my-researcher.md` with identical frontmatter (minus the dropped fields below).

## Importing Skills

```
/import skill ~/.claude/skills/kaizen
```

Skills can be either a directory containing `SKILL.md` or a standalone `.md` file. The import preserves the description, model, and body.

Field renames:

| Claude Code | aede |
|---|---|
| `allowed-tools` | `allowed_tools` |
| `trigger` | `trigger_phrases` |

## Importing MCP Servers

```
/import mcp --source claude-code
```

Reads `~/.claude/mcp.json` and merges servers into `~/.aede/config.yml`. When the source `command` is a list (e.g. `["npx", "-y", "server"]`), the first element becomes `command` and the rest become `args`.

## What Gets Dropped

Seven Claude Code agent fields are **commented out** (preserved as YAML comments in the output frontmatter, not lost):

| Dropped Field | Reason |
|---|---|
| `permissionMode` | aede doesn't have tool permission levels |
| `mcpServers` | MCP servers are configured globally in `config.yml`, not per-agent |
| `memory` | aede uses a different memory architecture |
| `isolation` | Not supported |
| `effort` | Not supported |
| `color` | Not supported |
| `hooks` | Not supported |

One skill field is commented out:

| Dropped Field | Reason |
|---|---|
| `hidden` | No equivalent concept in aede |

## Limitations

- MCP env vars with `${env:VAR}` syntax are passed through verbatim — aede does not interpolate them.
- Prompts before overwriting existing files; `--dest` lets you control the output directory.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
