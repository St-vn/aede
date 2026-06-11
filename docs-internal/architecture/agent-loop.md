---
type: internal-doc
tags: [docs-internal, architecture]
date_updated: 2026-06-10
---

# Agent Loop

**File:** `aede/agent.py` (845 lines)

## AgentLoop class (`aede/agent.py:200-845`)

Stateful multi-turn coordinator bridging provider, tools, gate, and DB. Constructed with references to all subsystems; lazily resolves provider and trace logger. Key state: `self._messages` (conversation history as Anthropic-format dicts), `self._turn` counter, `self._system_prompt` ([[compaction.md|SystemPrompt]] split).

### `run_turn(user_input)` (`aede/agent.py:316-573`)

The core method. Flow:

1. Increment turn counter, append user message to history (`aede/agent.py:327-328`)
2. Persist to DB + rollout (`aede/agent.py:330-339`)
3. Auto-compact if near context limit via `_maybe_compact()` (`aede/agent.py:341`)
4. Inner loop: while model emits tool calls:
   - `_stream_response()` calls the provider, streams text to console (`aede/agent.py:357`)
   - Record tokens in tracker (`aede/agent.py:361-366`)
   - Persist assistant message (text + thinking) (`aede/agent.py:378-393`)
   - For each tool call: validate name, run hard-deny hooks, run critic (if enabled + code content), gate approval, validate params, execute synchronously (`aede/agent.py:408-560`)
5. Write GEPA trace record (`aede/agent.py:566-573`)

### System prompt construction (`aede/agent.py:19-159`)

Two-part split:
- **Stable** (`STABLE_SYSTEM_PROMPT` at line 19): Role definition, tool descriptions, research rule, tool error policy, tool output policy, session notes instruction. Identical across all sessions — eligible for Anthropic KV-cache.
- **Dynamic** (`build_system_prompt()` at line 72): Configuration block, session block, session notes, compaction summary, grounding instruction, skills list, learnings suffix. Per-session, changes between turns.

### API error handling (`aede/agent.py:605-650`)

`_stream_response()` retries up to 3× on transient status codes (429/500/502/503) with exponential backoff (`BACKOFF_BASE * 2^attempt`). Non-transient errors surface immediately. HTML body detection (`_is_html_body()` at line 189) prevents dumping rendered error pages.

### Stuck detection (`aede/agent.py:506-553`)

Two mechanisms:
- **Tool error retries**: same call (name + args key) fails 3× consecutively → breaks inner loop with `outcome="stuck"` (`aede/agent.py:547-551`)
- **Param validation failures**: same call fails validation 2× → stuck, return early (`aede/agent.py:492-496`)

### Batch approval (`aede/agent.py:451-458`)

Scoped to one assistant message's `tool_calls` list. Only honored when `len(tool_calls) <= batch_approval_max` (default 20). `BATCH_APPROVE` sets a flag that skips the gate for remaining tools in that batch.

### GEPA trace (`aede/agent.py:575-598`)

`_write_turn_trace()` accumulates per-turn: input/output/cached tokens, tool calls (name/args/result/duration_ms/score/passed), reasoning text, outcome. Written to TraceLogger via lazy `_get_trace_logger()` (line 309). Defensive — exceptions are swallowed with a dim warning.

### Compaction trigger (`aede/agent.py:731-845`)

`_maybe_compact()` (auto) and `compact()` (manual via `/compact`) share `_run_compaction_body()`. For non-Anthropic providers, falls back to a bare Anthropic client; skipped entirely if `ANTHROPIC_API_KEY` is not set (`aede/agent.py:789-803`). On LLM summary path, stamps `compacted_at` on middle DB rows (excludes head=3, tail=15) (`aede/agent.py:836-843`).
