---
type: internal-doc
tags: [docs-internal, roadmap]
date_updated: 2026-06-10
---

# Roadmap Overview

The aede project is organized in phases:

## Phase 1 — Agent Core (✓ Complete)
- Agent loop with tool calling
- Multi-provider support (Anthropic, OpenAI, DeepSeek, OpenRouter, Google)
- Compaction (5-step heuristic + API-native)
- SQLite persistence (sessions, messages, rollouts, tool calls)
- Tool system (built-in + router + gating + MCP bridge)
- Server mode (FastAPI REST + WebSocket)
- CLI (argparse, ANSI streaming)

## Phase 2 — Knowledge & Quality (In Progress)
- **Skills system** (loading from files, injection into system prompt) — complete
- **Agents & subagents** (AGENT.md, run_subagent, spawn_subagent tool) — complete
- **Code critic** (asymmetric reviewer before gate) — complete
- **Memory** (LearningsStore, Ollama embeddings, hybrid retrieval, verifier, extractor) — complete
- **Credentials vault** (JSON encrypted vault) — complete
- **Trace logger** (GEPA per-turn JSONL) — complete

## Phase 3 — Agent Collaboration (Planned)
- Multi-agent orchestration
- ACP integration

## Key design constraints

- All components are decoupled via dependency injection (no globals)
- No heavy imports at module level (lazy inside functions)
- Tool errors return to the model as results
- SQLite with WAL + FTS5 for persistence and search
- Modular Monolith — everything is importable as a library
