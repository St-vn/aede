---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Windsurf Import

## Agent Files

Windsurf stores rules as plain `.md` files under `~/.windsurf/rules/`. These have no frontmatter — processed by `import_agents_md()` (`aede/import_/agents_md.py:19`) with name derived from the file stem. Windsurf is in the `_AGENTS_MD_SOURCES` set (`aede/commands.py:852`).

## Skills

Skills from `~/.windsurf/skills/`. Uses `import_claude_code_skill()` with `source="Windsurf"`.

## MCP Config

From `~/.codeium/windsurf/mcp_config.json` — JSON format. Uses `import_mcp_from_json()` with `serverUrl` → `url` mapping (Windsurf uses the `serverUrl` key, same as Antigravity).

## Layout

`_IMPORT_ALL_LAYOUT` (`aede/commands.py:1079-1082`) defines:
- Agents: `((".windsurf", "rules"), "agents_dir")` — glob all `.md` files in the rules directory
- Skills: `(".windsurf", "skills")`
- MCP: via `_MCP_DEFAULT_PATHS` pointing to `.codeium/windsurf/mcp_config.json`
