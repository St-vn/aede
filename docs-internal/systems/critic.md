---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Code Critic

**File:** `aede/critic.py` (162 lines)

## Architecturally Unique: Asymmetric Critic

Phase 2 Basic Correctness: a separate LLM invocation with a "ruthless code reviewer" persona that reviews proposed code before the approval gate. Advisory only — findings displayed to user, who decides at the existing gate.

## evaluate() (`aede/critic.py:70-124`)

Creates a separate LLM provider (or falls back to the main agent's model via `get_critic_provider()` at line 49), sends code with task context, parses JSON response into `CriticFinding` objects. Recorded with `role="critic"` for separate token tracking.

## Critic persona (`aede/critic.py:21-39`)

"Correctness bugs only" — no style/formatting feedback. Outputs strict JSON array: `[{"severity": "HIGH"|"MEDIUM"|"LOW", "message": "..."}]`.

## Severity levels

`HIGH` (bold red) — crashes, data loss, wrong output, broken contracts, security holes. `MEDIUM` (yellow) — wrong results in some cases. `LOW` (dim) — edge cases, potential issues.

## Non-fatal design

All exceptions return empty list — the agent loop proceeds regardless. Critic runs before the gate for `write_file`/`create_file` with code-like content (`aede/agent.py:442-447`). Uses `role="critic"` for separate token tracking via `tracker.record(role="critic")`.
