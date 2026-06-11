---
type: internal-doc
tags: [docs-internal, design-decisions]
date_updated: 2026-06-10
---

# Locked Architecture Decisions

From `docs/SOURCE_OF_TRUTH.md` section 26 (line 1247-1263). These decisions are considered locked — reversing them requires a new ADR.

| Decision | Rationale |
|---|---|
| SQLite + WAL + FTS5 as default session store | Migrate-to pattern across Codex, OpenCode, Hermes, OpenClaw |
| Hide-don't-delete compaction | Audit trail preserved; `compacted_at` in schema |
| Two-phase compaction (O(n) pass first, LLM second) | O(n) pass reclaims 30-50% for free |
| Dual storage: JSONL rollouts + SQLite state | JSONL for crash-safe append/replay; SQLite for query/search |
| Asymmetric critic over multi-agent debate | Debate costs 3-5× without reliable advantage |
| Graph memory deferred to Phase 3+ | LOCOMO: graph adds ~2% accuracy at 2× tokens, 3× latency |
| GEPA over GRPO for skill evolution | +6pp average, up to 35× fewer rollouts |
| Self-improvement read step is load-bearing | Reflexion's +8% comes from the read step |
| Stable prompt prefix for KV-cache | 10× cost difference cached vs uncached |
| No LLM retry on hallucinated tool names | Unknown name cannot become valid by retrying |
| Pydantic validation on every tool call | Typed gate; retry once on param errors |
| Tool errors return to model as results | Never hide errors; model decides retry vs report |
| Heavy imports are lazy | `anthropic`, `pydantic`, `rich` — loaded inside functions |
