---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Import System Architecture

Entry point: `handle_import()` at `aede/commands.py:822`. Dispatches to four subcommands — `agent`, `skill`, `mcp`, `all` — via `_handle_import_agent()`, `_handle_import_skill()`, `_handle_import_mcp()`, and `_handle_import_all()`.

## Source Registry

`_IMPORT_SOURCES` (`aede/commands.py:855-857`): `{"claude-code", "opencode", "antigravity", "codex", "cursor", "windsurf"}`. Six source harnesses supported.

`_AGENTS_MD_SOURCES` (`aede/commands.py:852`): `{"antigravity", "codex", "windsurf"}` — sources whose agent/rules files are plain markdown without YAML frontmatter.

`_JSON_MCP_SOURCES` (`aede/commands.py:854`): `{"claude-code", "antigravity", "cursor", "windsurf"}` — sources whose MCP config uses the shared JSON `mcpServers` shape. Codex is the outlier, using TOML.

## Layout Registry

`_IMPORT_ALL_LAYOUT` (`aede/commands.py:1062-1083`) maps each source to its standard directory layout for `import all`. Each entry specifies agents (as files or glob directories), skills path, and MCP default. Cursor has no skills entry.

## MCP Default Paths

`_MCP_DEFAULT_PATHS` (`aede/commands.py:982-988`) defines per-source default MCP config locations relative to `$HOME`:

| Source | Path |
|---|---|
| claude-code | `.claude/mcp.json` |
| antigravity | `.gemini/config/mcp_config.json` |
| codex | `.codex/config.toml` |
| cursor | `.cursor/mcp.json` |
| windsurf | `.codeium/windsurf/mcp_config.json` |

## Agent Routing

`_import_one_agent()` (`aede/commands.py:914-947`) routes based on source and file extension. Auto-detection: `.mdc` → Cursor, YAML frontmatter present → Claude Code (fallback OpenCode on parse failure), plain markdown → `agents_md` handler.

## Import Converters

Six converter modules in `aede/import_/`:
- `claude_code.py` — YAML frontmatter `.md` → aede AgentDef
- `opencode.py` — delegates to `claude_code.py`
- `agents_md.py` — plain markdown → aede AgentDef with synthesised name
- `cursor.py` — `.mdc` files with frontmatter → aede AgentDef
- `skills.py` — skill `.md` files → aede SKILL.md
- `mcp.py` — JSON and TOML MCP config → aede `config.yml`

## Test Coverage

8 test files in `tests/`: `test_import_claude_code.py`, `test_import_opencode.py`, `test_import_cursor.py`, `test_import_agents_md.py`, `test_import_mcp.py`, `test_import_mcp_sources.py`, `test_import_skills.py`, `test_import_skills_sources.py`.
