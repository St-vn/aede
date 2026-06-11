---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# CodeBlock

**File:** `ui/components/chat/CodeBlock.tsx`

## Purpose

Syntax-highlighted code block using Shiki. Rendered by `AssistantMessage` for fenced code content.

## Highlighting

Uses `shiki` with `github-dark` theme. Language auto-detection via `createHighlighter`. On error (unknown language or WASM issue), falls back to raw `<pre>` display.

## Copy Button

Hover-reveal copy button in the top-right corner using `lucide-react` `Copy`/`Check` icons. Toggles to check mark for 2 seconds after copy.

## Integration

Referenced from `AssistantMessage.tsx` — parses message content for code fences and renders each as a `CodeBlock` with the appropriate language tag.
