---
type: doc
tags: [docs, architecture]
date_updated: 2026-06-10
---

# Agent Loop

The agent loop is the core runtime that orchestrates multi-turn conversations between the user and the LLM.

## Turn Flow

Each turn follows this sequence:

1. **User input** — appended to conversation history, persisted to DB + rollout
2. **Auto-compaction check** — if token usage exceeds the threshold, compact before proceeding
3. **Inner loop** — while the model requests tools:
   - Stream LLM response (text and tool calls)
   - Record token usage
   - Persist assistant message
   - For each tool call:
     - Validate tool name (reject unknown without retry)
     - Run hard-deny safety hooks
     - Run code critic (if enabled + gated file write with code)
     - Gate approval (allow/deny/redirect/batch)
     - Validate parameters with Pydantic (one retry on failure)
     - Execute tool synchronously
     - Collect result, detect stuck state (3 consecutive failures → break)
   - Append tool results and repeat
4. **GEPA trace** — write turn trace record

## System Prompt

The system prompt has two parts:

- **Stable** — role definition, tool descriptions, rules. This is identical across sessions and eligible for prompt caching (Anthropic KV-cache with `cache_control: ephemeral`).
- **Dynamic** — per-session configuration, session notes, compaction summary, grounding instruction, skills, and learnings. Built fresh each turn.

## Error Handling

- **Transient API errors** (429/500/502/503) — retry up to 3 times with exponential backoff (0.5s, 1s, 2s)
- **Non-transient errors** — surfaced immediately to the user
- **HTML body detection** — prevents rendering error pages as if they were API responses

## Stuck Detection

The loop detects when it's stuck:

- Same tool call fails 3 times consecutively → prints warning and returns
- Parameter validation fails twice on the same call → marks stuck and returns early

## Context Compaction

When the conversation approaches the context limit (default 200k tokens at 85% threshold), compaction runs automatically:

1. **Memory flush** — LLM writes session notes before compaction
2. **String pass** — stubs old tool outputs with `[tool output — ~N tokens — compacted]` placeholders
3. **Re-check** — if below threshold after string pass, stop
4. **LLM summary** — preserves head (3) and tail (15) messages, collapses the middle via structured handoff
5. **Stamp** — marks compacted messages with `compacted_at` timestamp (hide-don't-delete)

Compaction can also be triggered manually with `/compact`.
