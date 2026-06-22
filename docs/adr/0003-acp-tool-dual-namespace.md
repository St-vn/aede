# ADR 0003 — ACP tool names kept verbatim; provenance via `provider` tag, not rename

**Status:** Accepted · 2026-06-18

## Context

When aede drives Claude Code (or any agent) through the ACP provider, the
foreign agent's tools execute **inside its own subprocess**. aede observes and
displays them but does not run them. The token audit surfaced `Edit`, `Read`,
`Write` rows in `tool_calls` whose names are PascalCase — Claude Code's
convention — not aede's snake_case (`edit`, `read_file`, `write_file`).

The question raised: should these be renamed to match aede's conventions for
consistency?

Two facts make renaming wrong:

1. **The raw name is a renderer key.** `_acp_tool_name` (`provider.py:770`)
   resolves the name from `_meta.claudeCode.toolName` *specifically so the UI's
   diff renderer can match it* (see the comment at `provider.py:774`).
   `_acp_edit_start_line` (`provider.py:806`) keys off Claude Code's
   `structuredPatch` response shape. Renaming `Edit`→`edit` on the ACP path
   breaks patch extraction and diff rendering.
2. **It would misrepresent provenance.** That row genuinely *is* Claude Code's
   tool, run by Claude Code. Relabeling it as an aede tool conflates two distinct
   surfaces: tools aede **runs** vs tools aede **observes**.

## Decision

Keep ACP tool names verbatim. Add a `provider` field to tool-call records
(`"aede"` for native, `"claude-code-acp"` / the agent id for ACP). The UI may
render a provenance label (e.g. "Edit (Claude Code)") using the tag, while the
renderer and patch-extraction continue to key on the raw `toolName`.

aede's snake_case naming convention applies to **native** tools registered in
`router.py` (`edit`, `read_file`, `glob`, …). ACP tools are a foreign surface
passed through. The two namespaces coexist deliberately.

## Consequences

- **Positive:** Diff renderer and `structuredPatch` extraction keep working
  unchanged. Provenance is honest and queryable (filter token usage by provider).
  Native-tool naming stays clean without leaking into the observed surface.
- **Negative:** Two naming conventions appear in the `tool_calls` table. This is
  intentional but must be documented so it isn't "fixed" later. UI must read the
  `provider` tag to label correctly.
- **Follow-up:** Add the `provider` column/field; document the dual-namespace
  rule in `docs-internal/systems/tools.md` and the web-ui tool-call-card doc.
