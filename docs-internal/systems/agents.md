---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Agents & Subagent Orchestration

**Files:** `aede/agents/schema.py` (74 lines), `aede/agents/loader.py` (59 lines), `aede/agents/orchestration.py` (130 lines)

## Agent definition (AGENT.md)

YAML frontmatter + body in markdown. Canonical keys use camelCase in YAML, mapped to snake_case in Python:

```yaml
---
name: researcher
description: Web research specialist
model: claude-sonnet-4-20250514
skills: [web-research]
tools: [web_search, fetch_url]
disallowedTools: [powershell]
maxTurns: 5
systemPrompt: "custom system prompt override"
---
Custom body text...
```

## AgentDef dataclass (`aede/agents/schema.py:11-74`)

Fields: `name`, `description`, `model` (default `"inherit"`), `skills`, `tools` (None = all tools), `disallowed_tools`, `max_turns` (default 20), `system_prompt`, `body`, `source_path`. Post-init validation requires non-empty `name` and `description`.

## load_agents() (`aede/agents/loader.py:10-59`)

Scans `~/.aede/agents/` and `./agents/`. Validates:
- All referenced skills exist in `skill_registry`
- All referenced tools exist in `all_tool_names` (raises `AgentLoadError` on mismatch)
Project agents shadow globals with same name.

## run_subagent() (`aede/agents/orchestration.py:41-130`)

Creates isolated AgentLoop:
1. Builds sub-config with optional model override (`aede/agents/orchestration.py:22-38`)
2. Creates filtered ToolRouter via `from_allowlist()` — only declared tools, minus disallowed
3. Opens fresh SQLite DB connection for the sub-session
4. Creates new Session linked via `parent_id` = orchestrator's session id
5. Rolls out `subagent_start` / `subagent_end` events
6. Iterates up to `agent_def.max_turns` (line 114)
7. Returns final assistant text or error string

`MAX_SPAWN_DEPTH = 1` guard (`aede/agents/orchestration.py:15`). Deeper spawns return error string.

## spawn_subagent tool (`aede/tools/router.py:112-146`)

Registered dynamically in ToolRouter when config + agent_registry + gate_store are available. Calls `run_subagent()` with `depth=1`. Runs in its own event loop (`asyncio.new_event_loop().run_until_complete()`).

## Import

Agents importable from Claude Code or OpenCode. Fidelity: ~40% — core identity fields transfer; behavioral fields (permissionMode, mcpServers, memory, etc.) commented out.
