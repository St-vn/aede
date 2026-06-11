---
type: internal-doc
tags: [docs-internal, imports, tests]
date_updated: 2026-06-10
---

# Import Test Coverage

8 dedicated test files covering the import system:

## `test_import_claude_code.py` (3 tests)
- `test_import_claude_code_fidelity`: Verifies 1:1 field mapping — supported fields preserved, 7 unsupported fields commented out, body intact.
- `test_import_claude_code_prompt_before_overwrite`: Confirms overwrite prompt fires and "y" replaces content.
- `test_import_claude_code_skip_on_no_overwrite`: Confirms "n" preserves original, `was_skipped=True`.

## `test_import_opencode.py`
- Delegates to claude_code logic. Tests format override.

## `test_import_cursor.py`
- `.mdc` frontmatter parsing, slug generation, dropped fields.

## `test_import_agents_md.py`
- Plain markdown import, name synthesis from parent dir, generic filename handling.

## `test_import_mcp.py` (4 tests)
- `test_import_mcp_server_basic`: Single server with command, args, env.
- `test_import_mcp_merge_existing`: Duplicate detection, overwrite prompt, skip behavior.
- `test_import_mcp_multiple_servers`: Two servers both written correctly.
- `test_import_mcp_no_mcp_servers_key`: Empty/absent key returns `[]`.

## `test_import_mcp_sources.py`
- Covers JSON sources: Claude Code, Antigravity, Cursor, Windsurf URL mapping.

## `test_import_skills.py`
- Skill file import, field name mapping (`allowed-tools` → `allowed_tools`, `trigger` → `trigger_phrases`), dropped `hidden` field.

## `test_import_skills_sources.py`
- Skills sourced from non-Claude-Code harnesses.

## Gaps
- No end-to-end tests for `import all` orchestrator loop.
- No tests for `_handle_import_all()` with real directory traversal.
- No dry-run tests for `/_handle_import_mcp_dry_run`.
- No TOML malformed-input tests for Codex MCP.
