---
type: doc
tags: [docs, architecture]
date_updated: 2026-06-16
---

# Architecture Overview

## High-Level Architecture

aede is organized as a layered system. From the outside in:

```
User ──► CLI / WebSocket ──► AgentLoop ──► Provider ──► LLM API
                                │
                          ┌─────┴──────┐
                          │    Tools    │
                          │ ┌────────┐ │
                          │ │ Router │ │
                          │ └───┬────┘ │
                          │  ┌──┴───┐  │
                          │  │ MCP  │  │
                          │  └──────┘  │
                          └─────┬──────┘
                                │
                     ┌──────────┴──────────┐
                     │    Gate + Hooks     │
                     │  (approval + deny)  │
                     └─────────────────────┘
```

## Component Relationships

| Component | File | Responsibility |
|-----------|------|----------------|
| `cli.py` | Entry point | REPL loop, parsing args, bootstrap |
| `agent.py` | Core | Multi-turn conversation orchestration |
| `provider.py` | LLM abstraction | Provider selection (Anthropic / OpenAI) |
| `tools/router.py` | Tool system | Registry, dispatch, validation |
| `gate.py` | Security | Approval prompts, permission storage |
| `hooks.py` | Security | Hard-deny pattern matching |
| `config.py` | Config | YAML merge (defaults > global > project) |
| `db.py` | Persistence | SQLite with WAL + FTS5 |
| `session.py` | State | Session lifecycle (ULID, branching) |
| `server.py` | HTTP | FastAPI + WebSocket backend |
| `tokens.py` | Tracking | Per-turn token accounting + cost |

## Package Structure

```
aede/
├── cli.py              # Entry point, REPL
├── agent.py            # Core agent loop
├── provider.py         # LLM provider abstraction
├── config.py           # Configuration system
├── db.py               # SQLite persistence
├── session.py          # Session management
├── commands.py         # Slash commands
├── gate.py             # Approval gate
├── hooks.py            # Safety hooks
├── tokens.py           # Token tracking
├── critic.py           # Code reviewer
├── credentials.py      # Credential vault
├── server.py           # FastAPI server
├── rollout.py          # JSONL audit trail
├── compaction.py       # Context compaction
├── models.py           # Model presets
├── project.py          # Project management
├── tools/              # Tool implementations
├── skills/             # Skills system
├── agents/             # Subagent system
├── memory/             # Memory system
├── mcp/                # MCP client
├── acp/                # ACP client
├── trace/              # GEPA trace logger
└── import_/            # Import converters
```

## Data Flow

1. **User input** arrives via CLI prompt or WebSocket message
2. **AgentLoop** builds the system prompt (stable prefix + dynamic configuration, skills, and learnings), pre-allocates an assistant message row for reliable FK targets
3. **Provider** sends the conversation to the LLM and streams the response — text, thinking blocks (with seq ordering), and tool calls (with inline diffs for edits) are forwarded to the UI in real time via callbacks
4. If the LLM requests a tool, **AgentLoop** validates the name, runs safety hooks, gates approval, validates parameters, and executes
5. Tool results are appended to the conversation and sent back to the LLM
6. The loop repeats until the LLM produces a final text response
7. Turn data is persisted to SQLite, JSONL rollout, and GEPA trace
