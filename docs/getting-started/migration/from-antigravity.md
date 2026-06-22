---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from Antigravity (Gemini CLI)

Antigravity (Gemini CLI) stores agents as plain markdown files with no YAML frontmatter. aede synthesises a name and adds frontmatter during import.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents | `~/.gemini/AGENTS.md` and `~/.gemini/GEMINI.md` | `/import agent <path> --source antigravity` |
| Skills | `~/.gemini/skills/` (dirs with `SKILL.md`) | `/import skill <path> --source antigravity` |
| MCP | `~/.gemini/config/mcp_config.json` | `/import mcp --source antigravity` |

## Quick Start

```
/import all --source antigravity
```

This imports `~/.gemini/AGENTS.md`, `~/.gemini/GEMINI.md`, all skills in `~/.gemini/skills/`, and MCP servers from `~/.gemini/config/mcp_config.json`.

## Importing Agents

Antigravity agent files have no frontmatter — they are plain markdown instructions:

```
/import agent ~/.gemini/AGENTS.md --source antigravity
```

Name synthesis:

| Source Filename | Synthesised Name |
|---|---|
| `~/.gemini/AGENTS.md` | Parent dir name → `gemini` |
| `~/.gemini/GEMINI.md` | Parent dir name → `gemini` |
| `my-project/rules.md` | Stem → `rules` |

The import adds fresh frontmatter:

```yaml
---
name: <synthesised-name>
description: Imported from Antigravity
model: inherit
---
```

The entire original file content becomes the agent body.

## Importing Skills

```
/import skill ~/.gemini/skills/deploy --source antigravity
```

Skills use the same YAML frontmatter `SKILL.md` format as Claude Code. The source tag is set to "Antigravity" in the import report.

Field renames:

| Antigravity | aede |
|---|---|
| `allowed-tools` | `allowed_tools` |
| `trigger` | `trigger_phrases` |

The `hidden` field is commented out.

## Importing MCP Servers

```
/import mcp --source antigravity
```

Reads `~/.gemini/config/mcp_config.json`. The `serverUrl` field is mapped to aede's `url` field. Remote servers (URL-based) need no `command` in aede.

## What Gets Dropped

Nothing from agents (plain markdown, no frontmatter to drop). Skills drop `hidden`. MCP drops no fields specific to Antigravity.

## Limitations

- Agent names are synthesised from the parent directory name — not from file content.
- Multiple agents cannot be defined in a single AGENTS.md file.
- MCP env vars with `${env:VAR}` syntax are passed through verbatim.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
- [Migrating from Claude Code](./from-claude-code)
