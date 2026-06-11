---
type: internal-doc
tags: [docs-internal, architecture]
date_updated: 2026-06-10
---

# Database & Persistence

**File:** `aede/db.py` (532 lines)

## SQLite configuration

- **Path:** `~/.aede/data/aede.db`
- **Journal:** WAL (`PRAGMA journal_mode=WAL`) — concurrent reads/writes without locking
- **Foreign keys:** ON (`PRAGMA foreign_keys=ON`)
- **Row factory:** Custom dict factory (`_row_factory` at line 112)

## Tables

| Table | Columns | Description |
|-------|---------|-------------|
| `sessions` | id (ULID PK), parent_id, title, created_at, updated_at, model, status, project_dir | Top-level conversation unit. Status: `active`\|`archived`. Branching via parent_id FK. |
| `messages` | id (ULID PK), session_id FK, role, content, created_at, token_count, compacted_at, thinking | User + assistant messages. `compacted_at` enables hide-don't-delete. |
| `tool_calls` | id (ULID PK), message_id FK, tool_name, args JSON, result, status, duration_ms, created_at | Per-tool-call record with timings. |
| `token_usage` | id (ULID PK), session_id FK, turn_number, input_tokens, output_tokens, cached_tokens, created_at, role | Per-turn usage. `role` = `"agent"` \| `"critic"`. |
| `learnings` | id (ULID PK), type, content, source, created_at, trusted, lower_trust, verifier_outcome, embedding BLOB | Phase 2 memory store. Embedding is `struct.pack` float array. |
| `projects` | id (ULID PK), project_dir UNIQUE, display_name, created_at, updated_at | Persistent workspace directories, survives session deletion. |

## FTS5 virtual tables

- `messages_fts` — full-text search on `messages.content` (`aede/db.py:63-67`)
- `learnings_fts` — full-text search on `learnings.content` (`aede/db.py:89-93`)
- Sync triggers: `AFTER INSERT`, `AFTER DELETE`, `AFTER UPDATE` on both source tables (`aede/db.py:68-77`, `94-103`)
- FTS index rebuild on first connection (`aede/db.py:137-139`)

## Migration handling (`aede/db.py:141-175`)

Graceful `ALTER TABLE ADD COLUMN` via try/except — SQLite has no `IF NOT EXISTS` for column additions:

| Migration | Change | Line |
|-----------|--------|------|
| BC-06 | `role` column on `token_usage` | 143-149 |
| WS-01 | `project_dir` column on `sessions` | 150-155 |
| PJ-01 | `projects` table creation | 156-169 |
| TH-01 | `thinking` column on `messages` | 170-175 |

## JSONL Rollout (`aede/rollout.py`)

- **Path:** `~/.aede/data/sessions/YYYY/MM/DD/rollout-<session_id>.jsonl`
- **Purpose:** Crash-safe append-only audit trail independent of SQLite
- **Schema:** Versioned JSON (`"v":1`) with UTC millisecond timestamps
- **Events:** `session_start`, `session_end`, `user_message`, `assistant_message`, `tool_call`, `tool_result`, `compaction`, `subagent_start`, `subagent_end`
- **Writer:** `Rollout.write(record)` — opens, appends, flushes each write (`aede/rollout.py:30-34`)
