---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Trace Logger

**File:** `aede/trace/logger.py` (83 lines)

## TraceLogger class

Append-only JSONL logger for GEPA (Generative Execution Path Audit) traces. Each agent turn is serialised as one JSON line into `<traces_dir>/<session_id>.jsonl`.

## Trace record fields

| Field | Description |
|-------|-------------|
| `session_id` | ULID session identifier |
| `turn_number` | Zero-based turn index |
| `timestamp` | UTC ms |
| `input_tokens` | Prompt tokens consumed |
| `output_tokens` | Completion tokens produced |
| `cached_tokens` | Tokens read from KV cache |
| `tool_calls` | `[{name, args, result, duration_ms, score, passed}]` |
| `reasoning_text` | Model's chain-of-thought |
| `outcome` | `"completed"` \| `"stuck"` |
| `schema_version` | `"phase2-draft"` — placeholder until schema stabilises |

## Design

- Append-only, crash-safe: `open(mode="a") + flush` per write (`aede/trace/logger.py:81-83`)
- Directory created lazily on first write (`aede/trace/logger.py:79`)
- No heavy imports at module level (json / pathlib / time are stdlib)
- Written by `AgentLoop._write_turn_trace()` (`aede/agent.py:575-598`) — defensive, never crashes `run_turn`

## Integration with rollout

The trace logger is complementary to the [[database.md|JSONL Rollout]]. Rollout captures all events (session lifecycle, messages, tool calls). Trace captures per-turn GEPA analysis (scores, outcomes, reasoning). Both are crash-safe append-only logs.
