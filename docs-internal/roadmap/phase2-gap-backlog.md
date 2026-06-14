---
type: internal-doc
tags: [docs-internal, roadmap, phase2, backlog, phase3]
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

### P0.5 Background Runtime — Daemon + Timers + Cron + Event triggers

**Source spec:** `aede-roadmap.md` lines 338-348 (Phase 3)

**What ships:**
- **`aede/daemon/`** — long-running host process (`aede daemon`). The foreground CLI attaches to a running daemon instead of being the only runtime. IPC over a Unix socket (POSIX) or named pipe (Windows).
- **`aede/daemon/timers.py`** — one-shot delays ("in 20 minutes", "at 3pm"). Persisted across daemon restarts.
- **`aede/daemon/cron.py`** — repeating schedules ("every Monday at 9am"). Persisted; survives restart.
- **`aede/daemon/events.py`** — fire session on file-watch (path changes) or inbound webhook. The daemon hosts the watchers/listeners.
- **Client attach API** — `aede --attach` connects to a running daemon; the REPL goes through the daemon.

**Size:** ~600-1000 LOC + tests. Large.

**Dependencies:** APScheduler (or roll our own); `watchfiles` for file-watch; HTTP server for webhooks.

**Verification:** integration tests with the daemon running; restart-survives for persisted timers/cron.

**Why P0 for SaaS:** without a daemon, the SaaS is single-shot (one CLI run per user per request). The SaaS is a daemon that services many concurrent users. **Non-negotiable for multi-tenant.**

---

### P0.6 Observability — OTel adapter for TraceLogger

**Source spec:** `aede-roadmap.md` lines 398-401 (Phase 3)

**What ships:**
- **`aede/observability/otel.py`** — wraps the existing `aede/trace/logger.py` TraceLogger with OpenTelemetry spans. One span per turn, child spans per tool call, attributes for token counts.
- **OTel exporter config** — `cfg.otel_endpoint` (default: `localhost:4317` for a local Jaeger/Tempo). When unset, no-op (personal aede doesn't phone home).
- **Per-process correlation** — trace_id is logged alongside session_id so the SaaS can join traces across user requests.

**Size:** ~200-300 LOC + tests. Medium.

**Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp` (new deps).

**Verification:** integration test with a local OTel collector; assert spans are emitted with correct attributes.

**Why P0 for SaaS:** the SaaS needs cross-tenant trace aggregation for debugging + SLA. The personal install doesn't need this (the local trace is enough), so it's opt-in via `cfg.otel_endpoint`.

---

### P0.7 FDE — opt-in capture + redaction

**Source spec:** `aede-roadmap.md` lines 405-413 (Phase 3)

**What ships:**
- **`aede/observability/fde_capture.py`** — opt-in (default OFF) capture of: tool call name + args (redacted), tool result (truncated + redacted), outcome, latency. Persisted to `<data_dir>/fde/<session_id>.jsonl` locally.
- **`aede/observability/redact.py`** — heuristic PII/secret redaction (API keys, email, paths under `~/`, etc.) before any capture. Tunable allowlist/denylist.
- **Consent gate** — `cfg.fde_enabled` flag, explicit consent (not silently set). When OFF, capture is a no-op.
- **Upload path stub** — when `cfg.fde_endpoint` is set, the captured JSONL is POSTed (with re-redaction check) to the endpoint. The SaaS provides the endpoint; aede just ships the client.

**Size:** ~200-400 LOC + tests. Medium.

**Dependencies:** none new (stdlib re + json + httpx already there).

**Verification:** TDD on the redaction patterns; integration test that the upload is a no-op when no endpoint; privacy test that secrets are redacted.

**Why P0 for SaaS:** the SaaS feedback loop depends on real usage data. Without capture, the SaaS is flying blind. **Opt-in + redact-by-default + clear consent** — non-negotiable for ethical reasons.

---

### P0.8 SOUL.md — agent identity + phonemes

**Source spec:** new (proposed 2026-06-14; complements the deferred "Wake word" item in `aede-roadmap.md` line 348)

**What ships:**
- **`aede/soul/schema.py`** — `SoulDef` dataclass with fields: `name`, `phonetic` (IPA, e.g. `/ˈdʒɑːvɪs/`), `wake_word` (defaults to `hey {name.lower()}`), `wake_word_phonetic`, `persona` (short markdown body), `voice` (TTS config — engine, voice_id, rate, pitch — for future use), `aliases` (list of alternative call names).
- **`aede/soul/loader.py`** — reads `SOUL.md` from `~/.aede/SOUL.md` (global) and `./SOUL.md` (project). 3-layer merge: project overrides global, just like `aede.yml`. YAML frontmatter + markdown body. Falls back to a default `SoulDef(name="aede", phonetic="/eɪd/")` if no file present.
- **`aede/soul/injection.py`** — injects the persona + phonetic into the system prompt as a `## Agent Identity` section (mirrors the skills injection pattern). The wake word is exposed to the voice input subsystem via `cfg.soul.wake_word`.
- **CLI surface** — `/soul` slash command to view/edit the active SOUL.md.
- **Settings tab** — `SoulTab` in the web UI settings modal (parallels the existing `SkillsTab`).

**Example `SOUL.md`:**
```yaml
---
name: Jarvis
phonetic: /ˈdʒɑːvɪs/
wake_word: "hey jarvis"
wake_word_phonetic: /heɪ ˈdʒɑːvɪs/
persona_voice: en-GB-Ryan
persona_rate: 1.0
aliases: [jarvis, j]
---
British butler. Dry wit. Gets to the point. Never apologetic.
```

**Size:** ~100-200 LOC + tests. Small.

**Dependencies:** none new (mirrors the existing `SKILL.md` loader pattern in `aede/skills/loader.py`).

**Verification:** TDD on the loader (YAML parsing, 3-layer merge, fallback to default); integration test that the persona is injected into the system prompt.

**Why pre-divergence (per 2026-06-14 user decision):** users want the agent to have an identity. "Wake word might seem like a luxury feature" but users like having it. The SaaS benefits from per-tenant SOUL.md (each user customizes their agent's name + persona) without forking the loader.

---

### P0.9 Voice input — push-to-talk + browser continuous wake word

**Source spec:** `aede-roadmap.md` line 348 (Phase 3, currently deferred — pulled forward 2026-06-14)

**What ships:**
- **Web UI mic button** in `InputBar` — toggleable per user preference (`cfg.voice_input_enabled`, default off). Press-to-talk; speech → text via Web Speech API. Populates the input bar; user reviews, hits send.
- **Browser continuous wake word** — when `cfg.voice_wake_word_enabled=true` and the wake word from SOUL.md is set, the web UI listens continuously for the wake word via Web Speech API with `continuous: true`. On match, activates the input bar with a "yes?" prompt.
- **Phoneme-aware TTS prep** — stores `wake_word_phonetic` from SOUL.md for use by future TTS / acoustic models. (The actual TTS response path is deferred per Phase 3 Other Tools line 362.)
- **Permissions UX** — browser-native mic permission prompt; clear UI indication when listening, when waiting for wake word, when error.
- **Backend acknowledgment** — when the wake word triggers an input, aede logs the trigger event to the trace + (opt-in) FDE capture.

**Browser support matrix:**
| Browser | Push-to-talk | Continuous wake word |
|---|---|---|
| Chrome / Edge (desktop + mobile) | Yes | Yes (with limitations on mobile background) |
| Safari (desktop + iOS) | Yes | Partial (Safari pauses recognition after a few minutes) |
| Firefox | Yes (via webkitSpeechRecognition polyfill if available) | No (no Web Speech API support) |

**Size:** ~700-1200 LOC + tests. Medium-large.

**Dependencies:** none new for the client side (Web Speech API is browser-native). Backend: hooks into the existing `TraceLogger` for trigger events.

**Verification:** TDD on the wake word matching logic (string + phonetic); integration test that the web UI toggles correctly (mock `window.SpeechRecognition`); manual cross-browser smoke test.

**Why pre-divergence (per 2026-06-14 user decision):** the user wants the wake word for their own daily use; it's a UX differentiator that the SaaS can re-skin for per-tenant branding (each tenant's agent has a different wake word via their SOUL.md). Building it pre-divergence means the SaaS fork ships with voice support on day one.

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
| Sprint 1 (DONE) | P0.1: OpenCode providers + LLM routing + curated MCP configs (commits `8000c40` + `6c40742`) | 1-2 days |
| Sprint 2 | P0.4: Context selection tool | 0.5 day |
| Sprint 3 | P0.2: Sandboxing | 2-3 days |
| Sprint 4 | P0.5: Background Runtime (daemon) | 2-3 days |
| Sprint 5 | P0.3: Skills and Plugins block (or import from Claude Code) | 3-4 days |
| Sprint 6 | P0.6: Observability (OTel) | 1 day |
| Sprint 7 | P0.7: FDE opt-in capture | 1-2 days |
| Sprint 8 | P1.1: UI polish | 1-2 days |

**Sprint 1 done (2026-06-14).** The next step is Sprint 2 (P0.4 Context selection — smallest remaining P0) or Sprint 3 (P0.2 Sandboxing — most critical for SaaS multi-tenant). Pick based on whether you want momentum (P0.4) or the highest-leverage piece (P0.2).

---

## What this backlog is NOT

- Not a rewrite of the original roadmap. It's a focused extraction of what's missing.
- Not a list of nice-to-haves. Every item is justified for the SaaS MVP.
- Not the Phase 3+ backlog. Cross-harness interop, background runtime, etc. are out of scope here.
