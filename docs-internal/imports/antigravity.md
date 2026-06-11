---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Antigravity Import

**File:** `aede/import_/agents_md.py:19` — `import_agents_md()`

## Source Files

Antigravity stores agent definitions as plain markdown at `~/.gemini/AGENTS.md` and `~/.gemini/GEMINI.md`. These files have **no YAML frontmatter** — the entire content becomes the agent body.

## Name Synthesis

When the filename is a generic name (`agents.md` or `gemini.md`, case-insensitive), the agent name is derived from the parent directory name via `_slugify()`. Otherwise, the file stem is used. Falls back to `"imported-agent"` if the slug is empty.

## Generated Frontmatter

aede wraps the plain content in YAML frontmatter with:
- `name`: slugified from parent dir or stem
- `description`: `"Imported from {source}"`
- `model`: `"inherit"`

## Skills and MCP

Skills imported from `~/.gemini/skills/`. MCP config from `~/.gemini/config/mcp_config.json` (JSON format). Both use the shared `import_mcp_from_json()` and `import_claude_code_skill()` converters tagged with the Antigravity source label.
