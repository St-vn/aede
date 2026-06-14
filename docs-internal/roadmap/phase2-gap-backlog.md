---
type: internal-doc
tags: [docs-internal, roadmap, phase2, backlog]
date_updated: 2026-06-14
---

# Phase 2 Gap Backlog

**Why this doc exists:** the user (2026-06-14) decided merge-phase2 should contain everything Phase 2 of the original roadmap (`aede-roadmap.md` lines 126-259) needs, AND pulled forward all deferred tools (since the SaaS will need them). This is the prioritized backlog of remaining work on `merge-phase2`.

**Scope:** items below are NOT in the current code on `merge-phase2`. Each item lists the source spec section, the rough size, the dependency, and the verification gate.

**Research-first policy still applies** (per `aede-roadmap.md` line 10). For each cluster, the research note in `.claude/docs/research/<topic>.md` must exist before design is finalized.

---

## P0 — must for SaaS MVP

### P0.1 LLM routing layer + OpenCode providers + curated MCP server configs

**Source spec:** `aede-roadmap.md` lines 154-163 (Tool Additions) + lines 174-181 (per-agent model routing, bundle)

**What ships:**
- **OpenCode zen provider** — free-tier; OpenAI-compatible API
- **OpenCode Go provider** — paid tier; OpenAI-compatible API
- **`aede/routing/router.py`** — route by constraint: `latency` → Groq, `volume` → Cerebras, `context` → Gemini, `offline` → Ollama, default → Anthropic. Reads `cfg.routing_strategy` (auto | manual). Manual: per-agent model override in `AGENT.md`. Auto: route by per-task heuristic (size of input, tool count, latency budget).
- **Curated MCP server configs** — add to `docs/mcp-server-configs/` (or `examples/mcp-servers.yml`): SearXNG, Playwright MCP, Docling MCP, GitHub MCP. Each is just a `mcp_servers:` YAML block the user pastes into `~/.aede/config.yml`. Per defer note, no bespoke code — just configs.
- **Optional: git/gh typed tools** — `aede/tools/git.py` and `aede/tools/github.py` with structured args/return. Polish, not capability gap (powershell can do it). Defer to v0.3 if time-constrained.

**Research gates (research-first):**
- OpenCode zen + Go API endpoints, auth scheme, rate limits, model names. (Write `.claude/docs/research/opencode-providers.md` before coding.)
- LLM routing patterns in LiteLLM, OpenRouter, LangChain. (Already have the research dirs; check `.claude/docs/research/`.)

**Size:** ~300-500 LOC + tests. Medium.

**Dependencies:** none (builds on existing `provider.py`, `models.py`, `mcp/client.py`).

**Verification:** new unit tests for routing decisions + each new provider; live test against OpenCode API.

---

### P0.2 Sandboxing

**Source spec:** `aede-roadmap.md` lines 130-136

**What ships:**
- **`aede/sandboxing/docker.py`** — Docker-per-user sandbox. Each user (or each session) gets a fresh container with the workspace mounted read-only by default. Tool execution (`powershell`, `write_file`, `create_file`) routes through the sandbox when `cfg.sandbox_enabled=True`.
- **File set discipline** — `aede/sandboxing/fileset.py` — agent declares the file set it intends to touch at task start (via a `declare_fileset` tool or auto-inferred from the prompt). Writes outside the declared set require explicit gate approval. Default-deny outside the set.
- **Prompt injection filter** — `aede/sandboxing/prompt_filter.py` — strip suspicious content from tool results (fetch_url, web_search, session_search) before they reach the LLM. Pattern match on "ignore previous instructions", "system:", base64 blobs, etc. Heuristic, not perfect — log filtered content for review.

**Research gates (research-first):**
- E2B, Microsandbox, Docker SDK isolation patterns. (Write `.claude/docs/research/sandboxing.md`.)
- Riley Goodside + Simon Willison prompt injection attack patterns. (Same file.)
- Manus / OpenCode "file set discipline" approach. (Same file.)

**Size:** ~500-800 LOC + tests. Large.

**Dependencies:** Docker SDK (new dep); prompt injection filter is pure Python.

**Verification:** sandbox integration tests (real containers); prompt injection unit tests with a corpus of attack patterns.

**Why P0 for SaaS:** without sandboxing, the SaaS cannot host other users' code safely. Non-negotiable for SaaS.

---

### P0.3 Skills and Plugins block

**Source spec:** `aede-roadmap.md` lines 194-204

**What ships:**
- **Plugin toggle system** — `aede/plugins/registry.py` — per-project enable/disable. Config schema: `plugins:` block in `aede.yml` with `enabled: [skill-name-1, skill-name-2]` or `disabled: [...]`. Skills not in the list are not loaded.
- **sdlc-engineer skill** — `skills/sdlc-engineer/SKILL.md` + sub-skill files. The 28-task suite from the existing v2 plan (referenced in `.claude/docs/`). Scaffold the SKILL.md, the orchestration body, and the methodology doc. Stub the tools the skill invokes (most delegate to existing aede tools).
- **configure skill** — `skills/configure/SKILL.md` — ≤8-question interview. Project intent tier → security tier → launch tier → sub-skill gates. Output: `aede.yml` populated with `plugins:`, `mcp_servers:`, `model:`, etc. This is the "first-run" experience.
- **research skill** — `skills/research/SKILL.md` — 3-track: market, technical, compliance. Delegates to MCP tools (web search, fetch_url) + invokes aede's memory for prior research. Outputs findings to `.aede/research/<topic>.md` with structured sections.
- **kaizen skill (upgraded)** — `skills/kaizen/SKILL.md` — critique-then-fix format per `aede-roadmap.md` line 144. Symptom → Investigation → Root-Cause → Fix → Lesson. Reads the trace logger output for the last session, identifies patterns, prompts the user to crystallize learnings into the `LearningsStore`.

**Research gates:**
- Existing skills in `.claude/docs/research/migration-import.md` line 112 (kaizen format reference).
- The 28-task sdlc-engineer plan is in `.claude/docs/`. Read it before scaffolding.

**Size:** ~800-1200 LOC across 5 skills + plugin registry + tests. Large.

**Dependencies:** plugin toggle is independent; skills depend on the existing `aede/skills/loader.py`.

**Verification:** TDD per skill; integration test that loads all 5 skills and verifies trigger phrases dispatch correctly.

**Why P0 for SaaS:** the customization layer IS the SaaS product differentiator. Without a skill library, the SaaS is "aede in the cloud" with no per-tenant value-add.

---

### P0.4 Context selection tool (moved from P2)

**Source spec:** `aede-roadmap.md` line 229

**What ships:**
- **`aede/tools/context.py`** — `exclude_message(message_id)`, `include_message(message_id)`, `compact_to_last(n)` tools. The agent calls these to manage its own context window.
- **Filter in `aede/agent.py`** — `run_turn` honors the exclusion markers; excluded messages stay in the DB (audit trail) but are not sent to the LLM.
- **UI hook** — in the web UI, excluded messages get a strikethrough or "excluded" badge.

**Size:** ~150-200 LOC + tests. Small.

**Dependencies:** none (uses existing `db.py` schema).

**Verification:** TDD on the tool + integration test verifying excluded messages are not in the LLM call.

**Why P0:** the user explicitly asked for it; it's a high-leverage UX improvement for long sessions.

---

## P1 — defer to v0.3 (after the SaaS MVP ships)

### P1.1 Interface Additions gaps (UI polish)

- Session rename (trivial DB update — `PATCH /api/sessions/{id}` + UI button)
- Batch-approval scrollable menu with per-item preview
- In-TUI full config file editing via Textual

**Why defer:** polish, not capability gap. Ship the SaaS with the current UI.

---

## Sequencing (recommended sprint order)

| Sprint | Items | Approx size |
|---|---|---|
| Sprint 1 (this session?) | P0.1: OpenCode providers + LLM routing + curated MCP configs | 1-2 days |
| Sprint 2 | P0.4: Context selection tool | 0.5 day |
| Sprint 3 | P0.2: Sandboxing | 2-3 days |
| Sprint 4 | P0.3: Skills and Plugins block | 3-4 days |
| Sprint 5 | P1.1: UI polish | 1-2 days |

**Sprint 1 is the right starting point** — it unblocks the SaaS (multiple providers, routing = capacity to handle multiple tenants with different cost/latency needs) and is the smallest of the four P0s.

---

## What this backlog is NOT

- Not a rewrite of the original roadmap. It's a focused extraction of what's missing.
- Not a list of nice-to-haves. Every item is justified for the SaaS MVP.
- Not the Phase 3+ backlog. Cross-harness interop, background runtime, etc. are out of scope here.
