---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# Agent Client Protocol (ACP)

ACP allows aede to connect to external agent processes as backends, using their own models, subscriptions, and tool sets. Instead of calling an LLM API directly, aede delegates turns to another agent process.

## How It Works

When the configured model is an ACP agent (e.g., `claude-code`, `codex`, `goose`, `gemini`, `agy`, `cline`, `cursor`, `opencode`), aede routes conversation turns to that agent via JSON-RPC over a subprocess's stdio.

The ACP client uses an async message-pump design:

1. Spawns the agent subprocess with `asyncio.create_subprocess_exec`
2. Reads NDJSON lines from stdout in a background task
3. Sends JSON-RPC requests (e.g., `session/prompt`) and awaits responses
4. Streams agent response chunks back to the user via `agent_message_chunk` notifications

## Capabilities

- **Session management** — create sessions, send prompts, cancel in-progress turns
- **Streaming** — receives incremental text from the agent and forwards it to the UI
- **Reentrant requests** — handles agent-to-client requests during a turn (e.g., file reads, permission requests)
- **Sub-model routing** — use notation like `claude-code/opus-4-8` to specify which model the agent should use
- **Auth flow** — `drive_auth` async generator handles the connection authentication (browser login, API key, or existing session)

## Managing ACP Agents

```
/acp register <name> <cmd...>  — register a new ACP agent
/acp connect <name>            — connect and use this agent as backend
/acp disconnect                — return to normal LLM mode
/acp list                      — show connected agents
/acp configs                   — show registered agent configs
```

## Configuration

ACP agent definitions are stored in `~/.aede/agents.json`. The 7 base agents are seeded automatically at startup and are ready to connect.

## Future Plans

- Full permission routing through aede's approval gate instead of auto-approve
- Enhanced streaming with richer event types
- Long-running agent coordination patterns
