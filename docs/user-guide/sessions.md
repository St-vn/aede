---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-10
---

# Sessions

Sessions are the fundamental unit of interaction in aede. Each session is identified by a ULID and tracks the full conversation history.

## Starting a Session

Every REPL launch creates a new session automatically. Pass a task inline to pre-fill the first message:

```bash
aede "refactor the database module"
```

## Switching Sessions

List recent sessions:

```
/sessions
```

Resume a past session (creates a branch):

```
/resume <session-id>
```

Branching links the new session to the original via `parent_id`. The original remains intact.

## Session Storage

Sessions are stored in `~/.aede/data/aede.db` with tables for messages, tool calls, and token usage. Each session also gets a human-readable rollout log in `~/.aede/data/sessions/YYYY/MM/DD/rollout-<id>.jsonl` — an append-only audit trail that survives database corruption.

## Viewing History

Use `session_search` — the agent can search across past sessions using FTS5 full-text search. The tool returns matching messages with context windows.

## Session Lifecycle

- `/exit` — archives the session (status: `archived`)
- `Ctrl+C` — leaves the session active and resumable (status: `active`)
- `/delete-session <id>` — removes the session, its rollout log, and notes
- Empty sessions (no messages) are deleted automatically on exit
