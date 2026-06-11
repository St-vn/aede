---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-10
---

# CLI

## Invocation Modes

| Command | Mode | Description |
|---------|------|-------------|
| `aede` | REPL | Interactive prompt loop, starts a new session |
| `aede "task"` | REPL + task | Same as above, with the first message pre-filled |
| `aede --serve` | Server | Starts the FastAPI backend for the Web UI |
| `aede memory list\|show\|delete\|edit` | Memory CLI | Manage stored learnings without REPL |
| `aede --import <source> --src <path>` | Import | Import agents, skills, or MCP servers from other harnesses |

## REPL Loop

The interactive loop:

1. Bootstraps config and infrastructure (database, credentials, session)
2. Loads skills from `~/.aede/skills/` and `./skills/`
3. Loads agents from `~/.aede/agents/` and `./agents/`
4. Spawns configured MCP servers
5. Presents a prompt for your input

Each message you type is sent to the agent, which can reply with text, request tool execution, or both. The loop continues until you use `/exit`, `Ctrl+C`, or `Ctrl+D`.

## Session Branching

`/resume [id]` creates a new branch session with the selected session as its parent. The original session remains intact and independently resumable. The branch inherits the conversation history up to the point of branching, with tool round-trips collapsed.

## Shutdown Behavior

- `/exit` or `Ctrl+D` — session status set to `archived` (fully saved, resumable)
- `Ctrl+C` — session status set to `active` (saved, resumable)
- Sessions with no messages are deleted entirely
