---
type: internal-doc
tags: [docs-internal, status]
date_updated: 2026-06-10
---

# Feature Inventory

## Phase 1 — Core Loop (Complete)

| Feature | Status | File |
|---------|--------|------|
| CLI entry point + arg parsing | [x] | `aede/cli.py:198` |
| REPL loop with prompt | [x] | `aede/cli.py:463-547` |
| Bootstrap sequence | [x] | `aede/cli.py:266` |
| Config merging (defaults > global > project) | [x] | `aede/config.py:103-147` |
| Session branching (/resume) | [x] | `aede/cli.py:303-345` |
| Slash commands | [x] | `aede/commands.py:15-19` |
| Provider selection | [x] | `aede/provider.py:488-530` |
| Anthropic streaming | [x] | `aede/provider.py:55-167` |
| OpenAI/OpenRouter streaming | [x] | `aede/provider.py:305-481` |
| AgentLoop multi-turn | [x] | `aede/agent.py:200-793` |
| System prompt (stable + dynamic) | [x] | `aede/agent.py:19-159` |
| ToolRouter (registry + dispatch) | [x] | `aede/tools/router.py:38` |
| Gated tools | [x] | `aede/tools/router.py:18` |
| Tool schemas (Anthropic format) | [x] | `aede/tools/router.py:360-508` |
| Tool output truncation | [x] | `aede/tools/router.py:293-299` |
| Tool validation (name + args) | [x] | `aede/tools/router.py:208-247` |
| Core tools (read_file, write_file, etc.) | [x] | `aede/tools/files.py` |
| powershell + cmd/wsl | [x] | `aede/tools/powershell.py` |
| web_search (DuckDuckGo) + fetch_url | [x] | `aede/tools/web.py` |
| search_files (ripgrep) | [x] | `aede/tools/search.py` |
| session_search (FTS5) | [x] | `aede/tools/search.py` |
| Approval gate (TerminalGateBackend) | [x] | `aede/gate.py:109-147` |
| PermissionStore (session/project/global) | [x] | `aede/gate.py:29-87` |
| Hard-deny safety hooks | [x] | `aede/hooks.py:44` |
| Context compaction (string pass + LLM) | [x] | `aede/compaction.py:77-169` |
| Compaction provider fallback | [x] | `aede/agent.py:733-751` |
| SQLite DB (WAL + FTS5) | [x] | `aede/db.py` |
| Sessions table | [x] | `aede/db.py:17-26` |
| Messages table | [x] | `aede/db.py:27-35` |
| Tool calls table | [x] | `aede/db.py:36-45` |
| Token usage table | [x] | `aede/db.py:46-55` |
| Migration handling | [x] | `aede/db.py:141-169` |
| Session model (ULID, lifecycle) | [x] | `aede/session.py` |
| TokenTracker + estimate_cost | [x] | `aede/tokens.py` |
| PriceCache (OpenRouter) | [x] | `aede/tokens.py:135-188` |
| JSONL Rollout audit log | [x] | `aede/rollout.py` |
| Credentials vault | [x] | `aede/credentials.py` |
| Clean shutdown (archived/active/delete) | [x] | `aede/cli.py:569` |

## Phase 2 — Extended (Mixed)

| Feature | Status | File |
|---------|--------|------|
| Memory system — LearningsStore | [x] | `aede/memory/store.py` |
| Memory — Ollama embeddings | [x] | `aede/memory/embeddings.py` |
| Memory — FTS + cosine + hybrid retrieval | [x] | `aede/memory/retrieval.py` |
| Memory — system prompt injection | [x] | `aede/memory/injection.py` |
| Memory — code + LLM verifier | [x] | `aede/memory/verifier.py` |
| Memory — TraceExtractor (post-task mining) | [x] | `aede/memory/extractor.py` |
| Memory — Admissibility (contradiction check) | [x] | `aede/memory/admissibility.py` |
| MCP bridge (multiple servers) | [x] | `aede/mcp/client.py` |
| MCP tool naming (mcp\_\_server\_\_tool) | [x] | `aede/mcp/client.py:197-218` |
| MCP env var expansion | [x] | `aede/mcp/client.py:26-38` |
| MCP lazy bridge resolution | [x] | `aede/tools/router.py:74-83` |
| ACP client (async JSON-RPC message-pump) | [x] | `aede/acp/client.py` |
| ACP registry + seed agents | [x] | `aede/acp/registry.py` |
| ACP manager (connect/disconnect/switch) | [x] | `aede/acp/manager.py` |
| ACP session wrapper | [x] | `aede/acp/session.py` |
| ACP auth engine (drive_auth) | [x] | `aede/acp/auth.py` |
| ACP permissions bridge | [ ] | `aede/acp/permissions.py` — exists, not active (auto-approve in client) |
| ACP chat routing (AcpProvider) | [x] | `aede/provider.py:522-646` |
| ACP streaming wiring | [x] | `aede/provider.py:636-645` |
| Critic (asymmetric code reviewer) | [x] | `aede/critic.py` |
| GEPA trace logger | [x] | `aede/trace/logger.py` |
| Web server (FastAPI) | [x] | `aede/server.py` |
| WebSocket gate backend | [x] | `aede/server.py:27-56` |
| Web UI (Next.js) | [x] | `ui/` |
| Import — Claude Code agents | [x] | `aede/import_/claude_code.py` |
| Import — OpenCode agents | [x] | `aede/import_/opencode.py` |
| Import — skills | [x] | `aede/import_/skills.py` |
| Import — MCP config | [x] | `aede/import_/mcp.py` |
| Model presets | [x] | `aede/models.py` |
| Project model | [x] | `aede/project.py` |
| Skills system (load + inject) | [x] | `aede/skills/schema.py`, `aede/skills/loader.py` |
| Agents system (load + validate) | [x] | `aede/agents/schema.py`, `aede/agents/loader.py` |
| Subagent orchestration | [x] | `aede/agents/orchestration.py` |
| spawn_subagent tool | [x] | `aede/tools/router.py:104-133` |
| write_learning tool | [x] | `aede/tools/router.py:326-357` |

## Phase 3 — Planned

| Feature | Status | Notes |
|---------|--------|-------|
| ACP transport rewrite (deferred issues) | [ ] | Chat routing wired, but edge cases remain |
| Infra hosting (dedicated server) | [ ] | Not started |
| Web UI — multi-user features | [ ] | Not started |
| Web UI — real-time collaboration | [ ] | Not started |
| Graph memory (knowledge graphs) | [ ] | Deferred to Phase 3+ |
| GRPO-based skill evolution | [ ] | Deferred — GEPA chosen instead |
