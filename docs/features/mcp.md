---
type: doc
tags: [docs, features]
date_updated: 2026-06-10
---

# MCP Server Support

aede supports the Model Context Protocol (MCP), allowing you to extend the agent's toolset with any MCP-compatible server.

## Configuration

Add MCP servers to your config (`~/.aede/config.yml` or `./aede.yml`):

```yaml
mcp_servers:
  my-server:
    command: node
    args: ["path/to/server.js"]
    env:
      MY_KEY: "${SECRET_KEY}"
    trusted: false
    enabled: true
    disabled_tools: []
```

| Field | Default | Description |
|-------|---------|-------------|
| `command` | required | Executable command |
| `args` | `[]` | Command arguments |
| `env` | `{}` | Environment variables (supports `${VAR}` expansion) |
| `trusted` | `false` | If true, tools skip the approval gate |
| `enabled` | `true` | If false, server is not started |
| `disabled_tools` | `[]` | Specific tools to hide |

## How MCP Works

On startup, aede spawns each configured MCP server as a subprocess. The server announces its available tools, which are registered with the prefix `mcp__<server>__<toolname>`. When the agent calls one of these tools, the request is forwarded to the MCP server and the result is returned.

MCP servers run in background daemon threads with their own asyncio event loops.

## Tool Naming

MCP tools use the format `mcp__<server>__<name>` to prevent name collisions between servers.

## Managing MCP

- `/mcp` — list connected servers and their tools
- Servers can be enabled/disabled per-tool through the Web UI settings

## Importing from Claude Code

```bash
aede --import mcp
```

This reads `~/.claude/mcp.json`, normalizes server configs, and merges them into your aede config without clobbering existing entries. Stdio transport (command + args + env) transfers cleanly with approximately 90% fidelity.
