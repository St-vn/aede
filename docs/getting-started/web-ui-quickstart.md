---
type: doc
tags: [docs, getting-started, web-ui]
date_updated: 2026-06-10
---

# Web UI Quickstart

aede includes a browser-based interface built with Next.js and shadcn/ui.

## Start the Server

```bash
aede --serve
```

By default the server binds to `127.0.0.1:8000`. Override with `--host` and `--port`:

```bash
aede --serve --host 0.0.0.0 --port 8080
```

## Open the Browser

Navigate to `http://localhost:8000` (or whatever port you specified). The Web UI connects to the backend via WebSocket and provides:

- **Chat interface** — type messages, see streaming responses, approve or deny tool calls through a graphical gate
- **Settings modal** — 10 tabs (Config, Models, MCP, Context, Memory, Agents, Skills, Import, Keybinds, Projects) for managing every aspect of aede
- **Slash commands** — autocomplete for built-in commands, skills, agents, and MCP servers

## Differences from CLI

- Tool approval is graphical (buttons instead of keypresses)
- Streaming tokens render incrementally in the chat view
- Settings are editable through forms rather than config YAML
- Some features are only available in the CLI (e.g., `/extract`, editing config via `$EDITOR`)
