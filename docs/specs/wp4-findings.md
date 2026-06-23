# WP-4 — Spec Coverage Findings
**Work package:** Track 6 — Spec coverage: index + Gherkin ACs
**Date:** 2026-06-22
**Branch:** `audit/holistic-wave1`
**GH issue:** [spec][holistic] No spec index + missing Gherkin ACs for new subsystems (filed 2026-06-22)
**Note:** Canonical location for this file is `_scratch/holistic-audit/02-findings/wp4-spec-coverage.md` — kept here because `_scratch/` is not in the worktree. The orchestrator should copy this file there.

---

## Summary

The aede codebase has a rich set of design and spec documents scattered across `.claude/docs/`, `docs-internal/`, and `docs/` with no index and no canonical Gherkin `.feature` file location. Seven new subsystems shipped in Phase 2 (memory, agent-system, MCP client, extractor, sandbox, ACP transport, server) had varying AC coverage quality. The security-critical web server endpoints (S2 rmtree exploit #19, G2 compound-command bypass #21, D1 DB thread-safety #22, W1 cfg.model race #24) had **zero spec-backing**: the fixes existed in code and GH issues but were not anchored to formal Gherkin ACs that could be regression-detected.

---

## Spec Index (summary)

| Subsystem | Has Gherkin? | Canonical AC file | Gaps |
|-----------|:------------:|:-----------------:|------|
| ACP transport | YES (in spec §4) | `docs/specs/ac-acp-transport.feature` | US-9/10 (graceful crash, stderr) not yet Gherkin |
| Sandbox (P0.2) | YES (AC-1..10 in spec §3) | `docs/specs/ac-sandbox.feature` | Consolidated; security audit ACs added |
| Daemon (P0.5) | PARTIAL (prose ACs in spec §3) | backlog | Needs .feature conversion |
| Memory + Extractor | YES (full Gherkin in specs §4/§2) | `docs/specs/ac-memory.feature`, `ac-extractor.feature` | Complete |
| MCP client | YES (Gherkin in spec §2) | `docs/specs/ac-mcp-client.feature` | NFR ACs missing |
| Agent system | YES (full Gherkin in spec §3) | `docs/specs/ac-agent-system.feature` | Q4/Q6/Q10 unresolved open questions lack ACs |
| Import (conversation) | NO (user stories only) | backlog | phase2-spec-import-expansion = prose only |
| Web server | NO | `docs/specs/ac-server-security.feature` | Written here for first time; product code endpoints have no spec |
| Web UI (L1/L2) | PARTIAL (prose) | backlog | Need .feature conversion |
| Credentials vault | NO | backlog | Only ADR + systems doc |
| Sessions / DB | NO | backlog | Schema described; no ACs |
| Gate / Safety classifier | NO | `docs/specs/ac-server-security.feature` | G2 codified here for first time |
| Soul / Persona (P0.8) | PARTIAL | backlog | |
| Voice / ASR (P0.9) | PARTIAL | backlog | |
| Context Selection (P0.4) | PARTIAL | backlog | |
| Observability (P0.6) | NO | backlog | Design doc only |
| Skills/Plugins (P0.3) | PARTIAL | backlog | Overlaps agent-system spec |

---

## Key Findings

### F1 — No canonical Gherkin location existed (CRITICAL for regression safety)

Before this audit, Gherkin ACs were embedded in spec markdown files under `.claude/docs/phase2/` with no `.feature` extension and no tooling to run them. The security-critical fixes (#19, #21, #22, #24) had no spec-backing at all. If those fixes are regressed (e.g., path guard removed in a future refactor), there is nothing to catch it in a spec-compliance review.

**Remediation:** `docs/specs/` created; 7 `.feature` files written; `docs/specs/INDEX.md` is the single entry point.

### F2 — Server spec is a description, not a requirements document

`docs-internal/architecture/server.md` describes current behavior (endpoints, WS protocol, CORS). It does not specify what **must be true** (path validation, CSRF protection, model validation). Security invariants are stated in comments in `server.py` (e.g., "do NOT mutate shared cfg") but not in any spec.

**Remediation:** `docs/specs/ac-server-security.feature` codifies the security properties for #19, #21, #22, #24.

### F3 — Gate / safety classifier has no Gherkin anywhere

`docs-internal/systems/gate.md` describes the SafetyClassifier behavior. The G2 compound-command bypass fix (issue #21) and the H1 hooks/gate drift fix are code-level only. No `.feature` file existed.

**Remediation:** Compound-command AC scenarios added to `ac-server-security.feature`.

### F4 — Memory spec has excellent Gherkin; extractor spec has partial Gherkin

`phase2-spec-memory-system.md §4` has complete, well-formed Gherkin with Feature/Scenario/Given/When/Then. The extractor spec §2 has scenarios without Feature block headings. Both consolidated into `.feature` files.

### F5 — Daemon spec (P0.5) is the largest Gherkin gap in new subsystems

AC-1..AC-10 in `.claude/docs/spec/p0.5-background-runtime.md` are structured in Given/When/Then prose but are not `.feature` format. Missed-fire recovery (AC-6), OS-service install (AC-2), and scheduler correctness (AC-4/AC-5) are complex behaviors that need formal Gherkin.

### F6 — Import subsystem has only user stories

`phase2-spec-import-expansion.md` has story-level requirements but no Gherkin. Not blocking (import not yet implemented per extractor-first pivot), but must be resolved before implementation.

### F7 — No RTM linking issues to specs to tests

No Requirements Traceability Matrix connects GH issues (audit findings) to spec ACs to test files. Audit-completeness risk: a fix can be verified in code but have no traceable spec coverage.

---

## Files Created (in worktree docs/specs/)

| Path | Purpose |
|------|---------|
| `docs/specs/INDEX.md` | Master spec index |
| `docs/specs/ac-server-security.feature` | Server security Gherkin — codifies #19, #21, #22, #24 fixes |
| `docs/specs/ac-acp-transport.feature` | ACP transport US-1..US-8 |
| `docs/specs/ac-sandbox.feature` | Sandbox AC-1..AC-10 |
| `docs/specs/ac-memory.feature` | Memory MEM-01..MEM-13 |
| `docs/specs/ac-extractor.feature` | Extractor US-01..US-07 |
| `docs/specs/ac-mcp-client.feature` | MCP client US-01..US-09 |
| `docs/specs/ac-agent-system.feature` | Agent system Phases A-D |
| `docs/specs/wp4-findings.md` | This file (copy to _scratch/holistic-audit/02-findings/wp4-spec-coverage.md) |

---

## COVERAGE-MATRIX.md Row Updates (for orchestrator)

| Track | WP | Status | Notes |
|-------|-----|--------|-------|
| 6 | WP-4 Spec Coverage | DONE | GH issue filed; 7 .feature files written; INDEX.md created; security findings spec-anchored to #19/#21/#22/#24 |

---

## Backlog Items

1. Convert P0.5 daemon prose ACs to Gherkin `.feature`
2. Write Gherkin for import subsystem before implementation begins
3. Write Gherkin for credentials vault (only ADR exists)
4. Write Gherkin for DB/sessions schema invariants
5. Create RTM document linking GH issues to spec ACs to test files
6. Convert P0.3/P0.4/P0.6/P0.8/P0.9 partial ACs to formal Gherkin
7. Add NFR acceptance tests for MCP client (NFR-01..NFR-09 not covered)
