---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Session Management

**File:** `aede/session.py` (120 lines)

## Session class

Top-level unit of conversation history in the DB.

- **ID:** ULID via `generate_session_id()` (`aede/session.py:15-17`)
- **Factory methods:** `Session.create()`, `Session.load()`, `Session.list_recent()` — no direct constructor. `Session.load()` raises `KeyError` if not found.
- **Branching:** `parent_id` links branch sessions to origin (set during `/resume`)
- **Constructor** (`aede/session.py:40-48`): reads from dict row, fields: `id`, `parent_id`, `title`, `model`, `status`, `created_at`, `updated_at`, `project_dir`

## Lifecycle methods

| Method | Description | Line |
|--------|-------------|------|
| `archive(db)` | Status → `archived` | 108-111 |
| `delete(db)` | Remove from DB entirely | 113-115 |
| `set_active(db)` | Status → `active` | 117-120 |
| `set_title(db, title)` | One-time title set | 99-106 |
| `set_project_dir(db, path)` | Associate project | 76-79 |
| `to_dict()` | Serialize to dict | 50-60 |

## make_title(text) (`aede/session.py:20-31`)

- Messages <10 chars: text + UTC timestamp for disambiguation (`"foo · 2026-06-10 23:00"`)
- Longer: truncated to 60 characters

## ULID-based IDs

Generated via the `ulid` library (`aede/session.py:12`). Sortable by time, URL-safe, no collisions at single-machine scale.

## Session lifecycle in CLI (`aede/cli.py:303-345`)

- `/resume` finds session by ID, creates a new branch session with `parent_id` pointing at the original
- `/exit` or EOF → status `archived`
- Ctrl+C → status `active` (resumable)
- Empty sessions (no messages) → deleted entirely
