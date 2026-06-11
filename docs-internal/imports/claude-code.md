---
type: internal-doc
tags: [docs-internal, imports]
date_updated: 2026-06-10
---

# Claude Code Agent Import

**File:** `aede/import_/claude_code.py:21` — `import_claude_code_agent()`

## Format

Claude Code agents are `.md` files with YAML frontmatter delimited by `---`. The converter performs a 1:1 mapping of all supported fields into aede's AGENT.md format.

## Supported Fields

All frontmatter keys except the unsupported set are copied verbatim. The body (after the closing `---`) is preserved.

## Dropped Fields

`_UNSUPPORTED_FIELDS` (`aede/import_/claude_code.py:7-10`): `permissionMode`, `mcpServers`, `memory`, `isolation`, `effort`, `color`, `hooks`. These are commented out (prefixed with `#`) in the output frontmatter rather than silently dropped, preserving fidelity for the user to review.

## Overwrite Protection

If the destination file already exists, the user is prompted: "Overwrite {dest_path}? [y/N]". Accepts an `_input_fn` callable for test injection. Declining returns a report with `was_skipped=True`.

## ImportReport

Returns `ImportReport(name, dest_path, was_skipped, format)` where `format` is `"Claude Code"`.
