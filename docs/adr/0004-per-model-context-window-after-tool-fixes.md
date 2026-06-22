# ADR 0004 — Per-model context window via static lookup; ships AFTER tool fixes

**Status:** Accepted · 2026-06-18

## Context

`context_window` is hardcoded to 200,000 in `config.py` and used as the
denominator for the compaction threshold (`0.85 × 200K = 170K`) and the
ContextBar `total`. Many models aede can drive have larger windows (Gemini
2.5 Flash: 1M) and some smaller.

A published model's context window is **fixed at release** — it does not change
for a given model ID. Only new model IDs or non-deterministic aliases ("latest")
introduce new values. So a table keyed on model ID is deterministic, not
drift-prone; the only fuzzy case is alias IDs, handled by a conservative default.

**Critical interaction with the token leak (ADR 0002):** the compaction
threshold scales with the window. With uncapped `read_file`/`write_file`,
raising the window from 200K to 1M moves the compaction trigger from 170K to
850K — meaning the per-turn re-billing leak runs *eight times longer* before
anything trims. The audited 3.75M session plateaued at ~129K live context just
under the 170K trigger; a 1M window would have let it climb toward 850K.
**Scaling the window before fixing the leak amplifies cost.**

## Decision

Introduce a static `MODEL_CONTEXT_WINDOWS` lookup keyed on model ID, with a
**conservative 200K default** for unknown/alias IDs. Only well-known large
windows are entered explicitly. `context_window` becomes a resolved value
(`lookup(model) or config override or 200K`) rather than a flat constant.

**Sequencing constraint (hard):** this change ships **only after** the
token-efficiency tool fixes in ADR 0002 (`edit`, partial `read_file`, dedup) are
landed and verified. The window table is harmless once the leak is plugged and
harmful before.

## Consequences

- **Positive:** Long-context models get their real window — fewer premature
  compactions, longer coherent sessions. Deterministic (no live fetch).
  Per-session cost ceiling now reflects the actual model.
- **Negative:** ~10-entry table to maintain as models ship; conservative default
  means new large-window models under-utilize until added. Accepted as cheap.
- **Risk if sequencing violated:** bigger window × uncapped tools = larger
  cumulative bill, the opposite of the goal. The constraint is non-negotiable.
- **Follow-up:** optional tiered tool-result cap (OpenClaw-style 16K/32K/64K by
  window) layered on once the table exists; lower the cheap collapse-pass trigger
  to ~50% independent of the 85% LLM-summary trigger.
