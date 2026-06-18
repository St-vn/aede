---
type: doc
tags: [docs, features, web-ui]
date_updated: 2026-06-16
---

# Web UI

aede includes a browser-based interface built with Next.js, React, and shadcn/ui.

## Starting

```bash
aede --serve
```

Open `http://localhost:8000` in your browser.

## Chat Interface

The main view is a chat panel where you type messages and see the agent's streaming responses. Tool calls are displayed inline, and the approval gate appears as a dialog with Allow/Deny/Redirect buttons instead of CLI keypresses.

## Settings Modal

A settings panel with 12 tabs accessed from the chat interface:

| Tab | Description |
|-----|-------------|
| **Config** | View and edit YAML configuration |
| **Models** | Select model, add/edit/delete model presets |
| **MCP** | Add/remove servers, enable/disable per-tool, set trusted status |
| **Context** | Token budget and compaction settings |
| **Memory** | View and manage learnings |
| **Agents** | Create, edit, delete, and upload agent definitions (global or project scope) |
| **Skills** | Create, edit, delete, and upload skill definitions (global or project scope) |
| **Instructions** | Edit project instructions (AGENTS.md / CLAUDE.md) with global/project scope |
| **Import** | Instructions for importing from other harnesses |
| **Soul** | Agent identity, persona, voice settings (ASR model, wake word, API keys) |
| **Keybinds** | Keyboard shortcut reference |
| **Projects** | Project management |

## ACP Connection

Through the Web UI you can manage ACP agents — register, connect, and switch between external agent backends.

## Differences from CLI

- Graphical tool approval instead of keypress-based
- Incremental streaming token rendering in chat
- Settings editing through forms rather than YAML
- Slash commands available with autocomplete suggestions
- Voice input (push-to-talk and wake word) available in Web UI only
- Some advanced CLI commands (e.g., `/extract`) are not available in the Web UI

## Collapsible Blocks

All code blocks, thinking blocks, and tool call cards use a unified collapsible format with a consistent header, ChevronDown toggle, and grid-rows height animation. Thinking blocks show a "Thinking" label with character count meta and a yellow pulsing dot during streaming (no brain icon).

## Tool Call Cards with Inline Diffs

Tool calls render as status cards during streaming. Edit operations (`write_file`, `create_file`) show a unified inline diff viewer with file name header, `+N/-N` line counts, and green/red line-level diffs with real line numbers. Non-edit tools show JSON arguments. Tool calls and their results persist in the message view after streaming ends.

## Scope Selectors

Settings tabs for Soul and Instructions include a **ScopeSelector** dropdown to switch between **Global** and **Project** scope, allowing you to edit the same file type at different levels (e.g., `~/.aede/SOUL.md` vs `./SOUL.md`).
