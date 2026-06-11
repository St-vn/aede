---
type: doc
tags: [docs, reference]
date_updated: 2026-06-10
---

# Slash Commands

## Session Management

| Command | Description | Syntax |
|---------|-------------|--------|
| `/clear` | Start a new session (prompts confirmation) | `/clear` |
| `/exit` | End the current session (archived) | `/exit` |
| `/resume [id]` | Resume a session by ID (creates a branch) | `/resume <session-id>` |
| `/sessions` | List the 20 most recent sessions | `/sessions` |
| `/delete-session [id]` | Delete a session, its rollout log, and notes | `/delete-session <id>` |
| `/rm [id]` | Alias for `/delete-session` | `/rm <id>` |

## Information

| Command | Description | Syntax |
|---------|-------------|--------|
| `/help` | Print the list of available commands | `/help` |
| `/keybinds` | Show keyboard shortcuts | `/keybinds` |
| `/tools` | List available tools and their approval status | `/tools` |
| `/skills` | List all loaded skills | `/skills` |
| `/agents` | List all loaded agents | `/agents` |
| `/mcp` | List MCP servers and their tools | `/mcp` |
| `/tokens` | Show token usage, cost estimate, and cache hit rate | `/tokens` |

## Configuration

| Command | Description | Syntax |
|---------|-------------|--------|
| `/config` | View effective config with source tracking | `/config` |
| `/config <scope>` | View config at a scope (`global` or `project`) | `/config global` |
| `/config <scope> <key> <value>` | Set a config value | `/config project model claude-sonnet-4-20250514` |
| `/config <scope> <key> +<value>` | Add to a list key | `/config project auto_approve +powershell` |
| `/config <scope> <key> -<value>` | Remove from a list key | `/config project auto_approve -powershell` |
| `/setkey <NAME> <value>` | Save a credential to the vault | `/setkey OPENAI_API_KEY sk-...` |

## Agent Control

| Command | Description | Syntax |
|---------|-------------|--------|
| `/compact` | Manually trigger context compaction | `/compact` |
| `/extract [id]` | Extract learnings from a session trace | `/extract <session-id>` |

## ACP

| Command | Description | Syntax |
|---------|-------------|--------|
| `/acp register <name> <cmd...>` | Register an ACP agent | `/acp register codex npx codex` |
| `/acp connect <name>` | Connect to an ACP agent | `/acp connect claude-code` |
| `/acp disconnect` | Disconnect from ACP agent, return to normal mode | `/acp disconnect` |
| `/acp list` | List connected ACP agents | `/acp list` |
| `/acp configs` | Show registered ACP agent configs | `/acp configs` |

## Import

| Command | Description | Syntax |
|---------|-------------|--------|
| `/import agent <path>` | Import an agent/rules file | `/import agent ~/.claude/agents/my-agent.md` |
| `/import skill <path>` | Import a skill | `/import skill ~/.claude/skills/my-skill/SKILL.md` |
| `/import mcp` | Import MCP servers from Claude Code | `/import mcp` |
| `/import all` | Import everything from Claude Code | `/import all` |
