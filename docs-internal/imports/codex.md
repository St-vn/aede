---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Codex Import

## Agent Files

Codex stores agent definitions as plain markdown at `~/.codex/AGENTS.md`. Processed by `import_agents_md()` (`aede/import_/agents_md.py:19`) similarly to Antigravity — no frontmatter, name synthesised from parent directory.

## Skills

Skills from `~/.codex/skills/`. Uses `import_claude_code_skill()` with `source="Codex"`.

## MCP Config

Codex is unique among supported sources — its MCP config uses **TOML** (`~/.codex/config.toml`) instead of JSON. Handled by `import_mcp_from_toml()` in `aede/import_/mcp.py:134`.

### TOML Mapping

MCP servers live under the `[mcp_servers]` table in TOML. The converter maps `command`, `args`, `env`, `url`, `enabled`, and `disabled_tools` 1:1.

### Dropped Codex Fields

`_CODEX_DROPPED_FIELDS` (`aede/import_/mcp.py:10-21`): `bearer_token_env_var`, `startup_timeout_sec`, `startup_timeout_ms`, `tool_timeout_sec`, `tool_timeout_ms`, `cwd`, `required`, `enabled_tools`, `scopes`, `oauth_resource` (10 fields total). These are Codex-specific with no aede equivalent.
