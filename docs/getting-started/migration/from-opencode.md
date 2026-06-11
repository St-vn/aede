---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from OpenCode

OpenCode uses the same YAML frontmatter agent format as Claude Code. aede imports OpenCode agents by delegating to the same Claude Code import logic.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents | `~/.opencode/agents/*.md` | `/import agent <path> --source opencode` |
| Skills | — | Not supported |
| MCP | — | Not supported |

OpenCode does not have a skills directory or MCP config format.

## Quick Start

```
/import agent ~/.opencode/agents/my-agent.md --source opencode
```

There is no `/import all` support for OpenCode since it only supports agents.

## Importing Agents

```
/import agent ~/.opencode/agents/code-helper.md --source opencode
```

The agent schema is structurally identical to Claude Code. The same 7 unsupported fields (`permissionMode`, `mcpServers`, `memory`, `isolation`, `effort`, `color`, `hooks`) are commented out in the output.

Auto-detection also works: if you pass a `.md` file with YAML frontmatter and `--source` is omitted, aede tries Claude Code format first, then falls back to OpenCode.

## What Gets Dropped

Same 7 fields as [Claude Code](./from-claude-code#what-gets-dropped): `permissionMode`, `mcpServers`, `memory`, `isolation`, `effort`, `color`, `hooks`.

## Limitations

- No skills or MCP import available.
- OpenCode's own configuration (`opencode.json`, `opencode.jsonc`) is not imported — only agent files are supported.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
- [Migrating from Claude Code](./from-claude-code)
