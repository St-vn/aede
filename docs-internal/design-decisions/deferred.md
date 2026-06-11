---
type: internal-doc
tags: [docs-internal, design-decisions]
date_updated: 2026-06-10
---

# Deferred Decisions

## ACP Chat Routing

ACP agent switching and message routing via the chat UI is not yet wired (`SOURCE_OF_TRUTH.md` section 26 notes this). The backend `acp_manager` exists with connect/disconnect/register endpoints, but the chat UX doesn't route messages through ACP agents — all messages go through aede's native `AgentLoop`. Deferred because the core CLI integration takes priority and the UX for multi-agent chat is non-trivial.

## Web UI Polish Features

Several UI features identified but not yet implemented:
- SlashCommandPicker is implemented but not bound to keyboard shortcut in all contexts
- SettingsModal has 10 tabs but some tabs (Keybinds, Context) are stubs or incomplete
- Full keyboard navigation / accessibility pass not completed
- E2E test suite exists in `ui/e2e/` but not wired into CI

## Graph Memory

Graph-based memory retrieval deferred to Phase 3+. LOCOMO benchmarks show graphs add ~2% accuracy at 2× token cost and 3× latency — not worth the complexity at current stage.

## Semantic File Search

Currently uses ripgrep (`search_files`) and FTS5 (`session_search`). Semantic/embedding-based file search is not implemented in the web UI.
