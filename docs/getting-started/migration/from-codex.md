---
type: doc
tags: [docs, migration]
date_updated: 2026-06-10
---

# Migrating from Codex (OpenAI CLI)

Codex (OpenAI CLI) stores agents as plain markdown with no frontmatter, skills in YAML frontmatter files, and MCP configs in TOML format — the only source using TOML.

## Supported

| Artifact | Source Location | Import Command |
|---|---|---|
| Agents | `~/.codex/AGENTS.md` | `/import agent <path> --source codex` |
| Skills | `~/.codex/skills/` (dirs with `SKILL.md`) | `/import skill <path> --source codex` |
| MCP | `~/.codex/config.toml` | `/import mcp --source codex` |

## Quick Start

```
/import all --source codex
```

This imports `~/.codex/AGENTS.md`, all skills in `~/.codex/skills/`, and MCP servers from `~/.codex/config.toml`.

## Importing Agents

Codex AGENTS.md is plain markdown with no YAML frontmatter:

```
/import agent ~/.codex/AGENTS.md --source codex
```

Name synthesis: when the filename is `AGENTS.md` (case-insensitive), the name is derived from the parent directory. For example, `~/.codex/AGENTS.md` produces name `codex`.

The import adds fresh frontmatter:

```yaml
---
name: codex
description: Imported from Codex
model: inherit
---
```

## Importing Skills

```
/import skill ~/.codex/skills/search --source codex
```

Skills use the standard YAML frontmatter `SKILL.md` format. The source tag is set to "Codex".

Field renames:

| Codex | aede |
|---|---|
| `allowed-tools` | `allowed_tools` |
| `trigger` | `trigger_phrases` |

The `hidden` field is commented out.

## Importing MCP Servers

Codex MCP configs use TOML format, unique among the six supported sources:

```
/import mcp --source codex
```

Reads `~/.codex/config.toml` and merges servers under the `[mcp_servers]` table into `~/.aede/config.yml`.

### What Gets Dropped (10 TOML Fields)

Ten Codex-specific TOML fields are silently dropped — they have no equivalent in aede:

| Dropped Field | Reason |
|---|---|
| `bearer_token_env_var` | No OAuth bearer token flow |
| `startup_timeout_sec` | Not supported |
| `startup_timeout_ms` | Not supported |
| `tool_timeout_sec` | Not supported |
| `tool_timeout_ms` | Not supported |
| `cwd` | Working directory is managed by the server |
| `required` | No concept of required servers |
| `enabled_tools` | Use `disabled_tools` instead |
| `scopes` | No OAuth scope system |
| `oauth_resource` | No OAuth resource system |

### What Maps 1:1

| Codex TOML | aede YAML |
|---|---|
| `command` | `command` |
| `args` | `args` |
| `env` | `env` |
| `url` | `url` |
| `enabled` | `enabled` (defaults to `true`) |
| `disabled_tools` | `disabled_tools` |

## Dry Run

Preview what would be imported without writing anything:

```
/import mcp --source codex --dry-run
```

## Limitations

- Agent name is synthesised from the parent directory, not from file content.
- TOML inline tables for `env` are handled correctly, including nested `[mcp_servers.x.env]` sections.
- MCP env values are passed through verbatim with no interpolation.

## See Also

- [`/import` command reference](../reference/import-commands)
- [Migration overview](./index)
