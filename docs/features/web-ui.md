---
type: doc
tags: [docs, features, web-ui]
date_updated: 2026-06-20
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

### Input Bar Controls

| Control | Description |
|---------|-------------|
| **Model selector** | Switch model mid-conversation; ACP agents warm up automatically on selection |
| **Mode selector** | Switch permission mode (`plan`, `normal`, `allow_write_read`, `execution`, `auto`) without a slash command |
| **Stop (Square button)** | Interrupt the running turn immediately |
| **Send (Arrow-up button)** | Submit a message; while a turn is running, the message is queued and sent after the current turn completes |
| **Image attach (Link button)** | Attach one or more images to the next message; supported on vision-capable models |
| **Voice button** | Push-to-talk or wake-word voice input (requires `voice_input_enabled`) |

### Message Queue

Sending a message while the agent is still responding queues it. Queued messages are listed below the input and are sent automatically in order after each turn completes, with no additional interaction required.

### Image Input

Attach images via the Link button in the input bar. Images are embedded as base64 data URIs in the message content and forwarded to the LLM as vision content blocks. Vision-capable models: claude-sonnet-4-6, claude-opus-4-8, claude-fable-5, GPT-5.5, Gemini series, and others (see `VISION_MODELS` in code).

### Rewind / Fork

Every user message has a hover action menu (Undo icon) with three options:

| Option | Behavior |
|--------|---------|
| Rewind in place | Truncate history back to before this message and re-populate the input bar with the original text |
| Rewind in place + revert code | Same as above, also reverting any file writes made during the rewound turns |
| Fork to new branch | Create a new session branching from this message; a branch-point marker is shown in the original session |

### Copy

User messages show a copy button on hover that copies the message text to the clipboard.

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
