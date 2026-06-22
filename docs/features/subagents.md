---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# Subagents

Subagents are specialized agents that can be spawned by the main agent to work on tasks independently. They run in isolated agent loops with filtered tools and optional model overrides.

## Defining an Agent

Create an `AGENT.md` file in `~/.aede/agents/` (global) or `./agents/` (project):

```yaml
---
name: researcher
description: Web research specialist
model: claude-sonnet-4-20250514
skills: [web-research]
tools: [web_search, fetch_url]
disallowedTools: [powershell]
maxTurns: 5
systemPrompt: "You are a research assistant. Find and summarize information."
---
```

Available frontmatter fields:

| Field | Default | Description |
|-------|---------|-------------|
| `name` | required | Unique agent name |
| `description` | required | What this agent does |
| `model` | `inherit` | Model override (uses orchestrator model by default) |
| `skills` | `[]` | Skills to inject into the subagent |
| `tools` | `null` (all) | Explicit tool allowlist |
| `disallowedTools` | `[]` | Tools to exclude |
| `maxTurns` | 20 | Maximum conversation turns |
| `systemPrompt` | `""` | Custom system prompt override |

## Using Subagents

The agent can spawn subagents via the `spawn_subagent` tool. The agent decides when to delegate work — for example, asking a research agent to look something up while the main agent continues planning.

Subagents get:

- A fresh session linked to the parent session via `parent_id`
- A filtered ToolRouter based on their `tools` / `disallowedTools`
- An optional per-agent model override
- A maximum depth of 1 (subagents cannot spawn further subagents)

The subagent session is archived on completion, and results are returned to the main agent.

## Managing Agents

- `/agents` — list loaded agents in the REPL
- `/import agent <path>` — import an agent from Claude Code or OpenCode format
