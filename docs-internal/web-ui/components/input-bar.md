---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# InputBar

**File:** `ui/components/input/InputBar.tsx`

## Purpose

Compose and send messages. Supports rich input features.

## Input Handling

- **Auto-resize** textarea up to 200px via `useEffect` on `text` changes
- **Enter** to submit (not Shift+Enter), **Slash** (`/`) at position 0 opens slash picker
- **@ mentions** — `@` triggers `WorkspaceMentionPicker` for file references
- **Drag & drop** — files dropped into input area are read as text (`FileAttachment[]`) and injected as fenced code blocks; images are added as `ImageAttachment[]`
- **Paste** — Ctrl+V pastes images as inline attachments; text pasted with `>` blockquote formatting
- **URL prompt** — Popover for entering URLs via `handleAddUrl`

## Send Flow

`submit()` → `buildMessageText(text, images)` (appends inline markdown images) → `onSend(message, model)` → resets text, images, mentions. The caller handles session creation (new) or WebSocket send (existing).

## Children

- `ModelSelector` — model picker dropdown
- `AcpConnectChip` — ACP connection indicator
- `SlashCommandPicker` — `/` command autocomplete
- `WorkspaceMentionPicker` — `@` file mention autocomplete
- `FileChipBar` — chips for `@[file]` mentions
- `ImagePreviewBar` — thumbnail previews for pasted/dropped images
- `ContextButton` — attach file, paste from clipboard, add URL actions

## Drag Overlay

A dashed border overlay with "Drop files here to attach" appears during drag-and-drop.
