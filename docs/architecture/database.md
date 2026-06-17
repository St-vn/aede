---
type: doc
tags: [docs, architecture]
date_updated: 2026-06-16
---

# Database

aede uses SQLite for persistence with WAL journal mode and FTS5 full-text search.

## Location

The database is at `~/.aede/data/aede.db`. WAL mode provides better concurrent read performance.

## Key Tables

### sessions

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (PK) | ULID session identifier |
| `parent_id` | TEXT | Links to parent session for branching |
| `title` | TEXT | Auto-derived from first message |
| `created_at` | INTEGER | Unix millisecond timestamp |
| `updated_at` | INTEGER | Last activity timestamp |
| `model` | TEXT | Model used for this session |
| `status` | TEXT | `active` or `archived` |
| `project_dir` | TEXT | Optional project association |

### messages

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (PK) | ULID |
| `session_id` | TEXT (FK) | Parent session |
| `role` | TEXT | `user` or `assistant` |
| `content` | TEXT | Message body |
| `created_at` | INTEGER | Unix ms |
| `token_count` | INTEGER | Optional token count |
| `compacted_at` | INTEGER | Set when compaction hides this message |

### tool_calls

Tracks every tool execution: name, arguments (JSON), result, status (`success`/`error`/`running`), and duration in milliseconds. Supports upsert semantics — ACP may re-emit the same call ID with updated args.

### thinking_segments

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (PK) | ULID |
| `message_id` | TEXT (FK) | Parent assistant message |
| `text` | TEXT | Per-step thinking block content |
| `seq` | INTEGER | Execution ordering (interleaved with tool calls) |
| `created_at` | INTEGER | Unix ms |

Stores per-step thinking blocks for ACP turns, keyed by message and ordered by `seq`. Rendered as separate `ThinkingBlock`s on page reload, matching the interleaved timeline the user saw during streaming.

### token_usage

Per-turn token accounting with separate rows for `agent` vs `critic` roles. Tracks input, output, and cached tokens.

### learnings

Persistent memory store with embedding BLOBs for vector search, lifecycle fields (`trusted`, `lower_trust`, `verifier_outcome`), and source tracking.

### projects

Persistent workspace directories with independent lifecycle (survives session deletion).

## FTS5 Full-Text Search

Two FTS5 virtual tables provide full-text search:

- `messages_fts` — search past conversation messages
- `learnings_fts` — search stored learnings

Sync triggers on `AFTER INSERT`, `AFTER DELETE`, and `AFTER UPDATE` keep the FTS indexes in sync.

## Rollout Logs

In addition to SQLite, each session gets an append-only JSONL audit trail at `~/.aede/data/sessions/YYYY/MM/DD/rollout-<id>.jsonl`. This provides crash-safe, replayable session history that survives database corruption. Events include session start/end, user messages, assistant messages, tool calls, tool results, compaction events, and subagent start/end.
