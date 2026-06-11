---
type: internal-doc
tags: [docs-internal, architecture]
date_updated: 2026-06-10
---

# Context Compaction

**File:** `aede/compaction.py` (169 lines)

## Five-step sequence

1. **Memory flush** — LLM writes session notes to `<session_id>-notes.md` before summarization, so critical context survives the compaction boundary (`aede/compaction.py:121-136`)
2. **O(n) string pass** — `collapse_old_tool_outputs()` replaces old tool results with `[tool output — ~N tokens — compacted]` placeholder. Keeps last 10 turns by default (`aede/compaction.py:43-74`)
3. **Re-check** — if below threshold after string pass, stop; return `method="string_pass_only"` (`aede/compaction.py:99-105`)
4. **LLM summary** — preserves head (first 3 messages) + tail (last 15 messages). Middle messages collapsed via structured handoff template (`aede/compaction.py:107-166`)
5. **Stamp** — `compacted_at` timestamp on DB rows in agent loop (`aede/agent.py:836-843`)

## COMPACTION_PROMPT (`aede/compaction.py:13-26`)

Structured template: Goal / Constraints / Progress / Key Decisions / Critical Context / Next Steps. Designed for lossless handoff — "nothing that a future instance of yourself would need to continue seamlessly."

## MEMORY_FLUSH_PROMPT (`aede/compaction.py:28-30`)

Runs BEFORE the summary pass. Writes free-form notes to a file that persists across compaction boundaries. Errors do not abort compaction.

## run_compaction() (`aede/compaction.py:77-169`)

Returns dict: `{"method", "messages", "summary", "tokens_reclaimed", "messages_compacted"}`. `method` is one of: `"string_pass_only"`, `"llm_summary"`, `"none"`.

## Trigger conditions

- **Automatic**: fires when `current_tokens >= context_window * compaction_threshold` (default 85% of 200K = 170K tokens)
- **Manual**: `/compact` CLI command calls `agent.compact()` which bypasses threshold check

## Provider fallback (`aede/agent.py:773-803`)

Non-Anthropic providers fall back to a bare Anthropic client (`anthropic.AsyncAnthropic`) using the default model from config. Skipped entirely if `ANTHROPIC_API_KEY` is not set. This is because `run_compaction` calls `anthropic_client.messages.create()` directly.
