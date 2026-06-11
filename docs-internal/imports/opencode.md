---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# OpenCode Agent Import

**File:** `aede/import_/opencode.py:8` — `import_opencode_agent()`

## Format

OpenCode agent schema is structurally identical to Claude Code's — YAML frontmatter `.md` files with the same field semantics.

## Delegation

The entire function is a thin wrapper that delegates to `import_claude_code_agent()`, then overrides `report.format = "OpenCode"` (`aede/import_/opencode.py:23`). All field mapping, unsupported field handling, and overwrite logic is inherited from the Claude Code converter.

## Rationale

Rather than duplicating the converter, OpenCode reuse signals that both harnesses share the same agent definition schema. If they diverge in the future, the delegation can be replaced with a dedicated parser.
