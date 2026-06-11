---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Project Model

**File:** `aede/project.py` (56 lines)

## Project class

Persistent workspace directories with independent lifecycle — survives session deletion. ULID-based IDs.

| Method | Description | Line |
|--------|-------------|------|
| `create(db, project_dir, display_name)` | Create + DB insert. `display_name` defaults to directory basename. | 37-42 |
| `load(db, id)` | Load from DB. Raises `KeyError` if not found. | 44-49 |
| `list_all(db)` | All projects, ordered by `updated_at DESC` | 51-53 |
| `delete(db)` | Remove from DB only (no filesystem deletion) | 55-56 |

## DB table

Created under migration PJ-01 (`aede/db.py:156-169`). Columns: `id` (ULID PK), `project_dir` (UNIQUE TEXT), `display_name` (TEXT), `created_at`/`updated_at` (INTEGER).

## API endpoints

- `POST /api/projects` — create/register (idempotent — returns existing if path already registered)
- `GET /api/projects` — list all
- `DELETE /api/projects/{id}` — remove from list (no filesystem deletion)
- `POST /api/projects/{id}/delete-folder` — remove from list + delete directory
- `POST /api/projects/{id}/remove-git` — remove from list + delete `.git/`
