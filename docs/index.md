---
type: doc
tags: [docs]
date_updated: 2026-06-10
---

# aede

aede is a personal CLI agent harness for LLM-powered workflows. It wraps large language models (Anthropic primary, OpenAI-compatible secondary) into a configurable agent that can edit code, run shell commands, search files, browse the web, delegate to subagents, and persist knowledge across sessions.

## Quick Start

```bash
uv run aede
```

Set `ANTHROPIC_API_KEY` in your environment first. See [Installation](getting-started/installation.md).

## Features

- **Agent loop** — multi-turn conversation with streaming output, tool execution, and context compaction
- **Tools** — file operations, shell execution, ripgrep search, web search and fetch
- **Skills** — reusable instruction templates injected into the system prompt
- **Subagents** — delegate tasks to specialized agents with isolated tool access and model overrides
- **Memory** — learnings persist across sessions, retrieved via hybrid vector + FTS search
- **MCP servers** — integrate any Model Context Protocol server for extended tool capabilities
- **ACP** — Agent Client Protocol support for connecting to external agent processes
- **Code critic** — asymmetric LLM pass that reviews code for correctness before writes
- **Web UI** — browser-based interface with chat, settings (10 tabs), and ACP connection management
- **Session management** — ULID-based sessions with branching, resume, and full-text search
- **Token tracking** — per-turn usage with cost estimation and cache hit rate

## Documentation

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started/installation.md) | Installation, configuration, and first steps |
| [User Guide](user-guide/cli.md) | CLI usage, configuration, sessions, tokens, security |
| [Features](features/tools.md) | Tools, subagents, memory, skills, MCP, ACP, critic, web UI, server |
| [Architecture](architecture/overview.md) | System design, agent loop, providers, database |
| [Reference](reference/slash-commands.md) | Slash commands, config keys, tool reference |
| [Developer](developer/tests.md) | Tests and conventions |
