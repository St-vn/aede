# aede Spec Index

**Maintained by:** holistic-audit WP-4 (2026-06-22)
**GH issue:** [spec][holistic] No spec index + missing Gherkin ACs for new subsystems — see issue filed during this audit.
**Canonical location:** `docs/specs/` — all spec files live here going forward.

---

## Subsystem Spec Coverage Matrix

| Subsystem | Primary spec doc(s) | Design doc | Research doc | Has Gherkin ACs? | AC file in docs/specs/ | Gaps |
|-----------|--------------------|-----------:|-------------:|:----------------:|:----------------------:|------|
| **ACP (transport)** | `.claude/docs/acp-transport-rewrite-spec.md` | `.claude/docs/acp-transport-rewrite-design.md` | `.claude/docs/research/acp-connections.md` | YES (Gherkin in spec §4) | `docs/specs/ac-acp-transport.feature` | ACs cover Must-haves only; graceful-crash (US-9/US-10) have no Gherkin |
| **Sandbox (P0.2)** | `.claude/docs/spec/p0.2-sandboxing.md` | `.claude/docs/design/p0.2-sandboxing.md` | `.claude/docs/research/p0.2-sandboxing.md` | YES (AC-1..10 in spec §3) | `docs/specs/ac-sandbox.feature` | AC-9 (missing Docker one-time warn) and AC-10 (container reuse) need security-audit Gherkin |
| **Daemon (P0.5)** | `.claude/docs/spec/p0.5-background-runtime.md` | `.claude/docs/design/p0.5-background-runtime.md` | `.claude/docs/research/p0.5-background-runtime.md` | PARTIAL (AC-1..10 in §3 — structured but not strict Gherkin blocks) | backlog | AC-1/2/3 are Given/When/Then prose; need formal `.feature` files; no cron/missed-fire Gherkin |
| **Memory/Extractor** | `.claude/docs/phase2/phase2-spec-memory-system.md` + `.claude/docs/phase2/phase2-spec-trace-extractor.md` | — | `.claude/docs/research/self-improvement.md` | YES (full Gherkin in memory spec §4; extractor spec §2) | `docs/specs/ac-memory.feature` (MEM) + `docs/specs/ac-extractor.feature` | Gherkin complete for memory; extractor has scenarios but not `.feature` block headings |
| **MCP client** | `.claude/docs/phase2/phase2-spec-mcp-client.md` | — | — | YES (Gherkin in spec §2 US-01..US-09) | `docs/specs/ac-mcp-client.feature` | All 9 US have Gherkin; NFR-01..NFR-09 lack acceptance tests |
| **Agent System (skills/agents/subagents)** | `.claude/docs/phase2/phase2-spec-agent-system.md` | — | — | YES (full Gherkin in spec §3, Phases A–D) | `docs/specs/ac-agent-system.feature` | Open questions Q4/Q6/Q10 lack ACs; import fidelity edge cases (Hermes, Cline) not covered |
| **Import (conversation/agent import)** | `.claude/docs/phase2/phase2-spec-import-expansion.md` | — | `.claude/docs/research/migration-import.md` | PARTIAL (story-level; no scenario blocks) | backlog | No Gherkin at all; only user stories; import-expansion spec is thinner than agent-system |
| **Web Server (FastAPI + WS)** | `docs-internal/architecture/server.md` + `docs-internal/web-ui/api-contract.md` | `docs-internal/web-ui/architecture.md` | — | NO | `docs/specs/ac-server-security.feature` (**written here**) | No canonical Gherkin anywhere; security findings #19/#21/#22/#24 had no spec-backing before this audit |
| **Web UI (Layer 1/2)** | `.claude/docs/phase2/phase2-ui-web-spec.md` + `phase2-ui-web-spec-layer2.md` | — | — | PARTIAL (acceptance criteria in prose, not Gherkin blocks) | backlog | Layer 1 and 2 specs have ACs in prose; no .feature files |
| **Credentials vault** | `docs-internal/systems/credentials.md` + `docs/adr/0001-credentials-vault-file.md` | — | — | NO | backlog | Described in systems/ doc and ADR; no Gherkin |
| **Sessions / DB** | `docs-internal/architecture/database.md` + `docs-internal/systems/sessions.md` | — | — | NO | backlog | Schema + behaviors described; no Gherkin; D1/D2 thread-safety findings (#22) uncovered |
| **Gate / Safety Classifier** | `docs-internal/systems/gate.md` | — | — | NO | `docs/specs/ac-server-security.feature` (G2 scenario) | G1/G2 compound-cmd bypass (#21) had no spec; G2 fix codified here |
| **Soul / Persona** | `.claude/docs/spec/p0.8-soul-enhancements.md` | `.claude/docs/design/p0.8-soul-enhancements.md` | `.claude/docs/research/p0.8-soul-enhancements.md` | PARTIAL | backlog | Some ACs; not strict Gherkin format |
| **Voice / ASR** | `.claude/docs/spec/p0.9-voice-input.md` | `.claude/docs/design/p0.9-voice-input.md` | `.claude/docs/research/p0.9-voice-input.md` | PARTIAL | backlog | Story-level ACs; no Gherkin |
| **Context Selection (P0.4)** | `.claude/docs/spec/p0.4-context-selection.md` | `.claude/docs/design/p0.4-context-selection.md` | `.claude/docs/research/p0.4-context-selection.md` | PARTIAL | backlog | ACs exist in spec; not strict Gherkin |
| **Observability / OTel (P0.6)** | `.claude/docs/spec/p0.6-otel-observability.md` | `.claude/docs/design/p0.6-otel-observability.md` | — | NO | backlog | No Gherkin; design doc only |
| **Skills / Plugins (P0.3)** | `.claude/docs/spec/p0.3-skills-plugins.md` | `.claude/docs/design/p0.3-skills-plugins.md` | `.claude/docs/research/p0.3-skills-plugins.md` | PARTIAL | backlog | Overlaps with agent-system spec; not deduplicated |

---

## AC Files Written in This Audit (Priority: security-critical + new subsystems)

| File | Subsystem | Coverage | Tied to issues |
|------|-----------|----------|----------------|
| `docs/specs/ac-server-security.feature` | Web Server security + Gate | S2 fix (path guard), G2 fix (compound-cmd), D1 (DB thread lock), W1 (cfg.model race) | #19, #21, #22, #24 |
| `docs/specs/ac-acp-transport.feature` | ACP transport rewrite | US-1..US-8 Gherkin, consolidated from spec | — |
| `docs/specs/ac-sandbox.feature` | Sandbox (P0.2) | AC-1..AC-10 Gherkin, consolidated from spec | #9 |
| `docs/specs/ac-memory.feature` | Memory system (MEM-01..MEM-13) | Full Gherkin, consolidated from memory spec §4 | — |
| `docs/specs/ac-extractor.feature` | Trace extractor | US-01..US-07 scenarios, consolidated from extractor spec §2 | — |
| `docs/specs/ac-mcp-client.feature` | MCP client | US-01..US-09 Gherkin, consolidated from MCP spec §2 | — |
| `docs/specs/ac-agent-system.feature` | Agent system (Skills/Agents/Subagents) | Phases A–D Gherkin, consolidated from agent spec §3 | — |

---

## Backlog (spec exists but no Gherkin .feature file)

Priority order for next audit wave:

1. **Daemon (P0.5)** — structured ACs in spec §3 need Gherkin formatting; OS-service install (AC-2) and missed-fire recovery (AC-6) are complex behaviors
2. **Web UI Layer 1/2** — prose ACs exist in phase2-ui-web-spec; need .feature conversion
3. **Import (conversation import)** — phase2-spec-import-expansion has only user stories; needs full Gherkin
4. **Credentials vault** — only ADR + systems doc; no ACs of any kind
5. **Context Selection (P0.4)** — partial ACs; convert to Gherkin
6. **OTel Observability (P0.6)** — design doc only; no ACs
7. **Skills/Plugins (P0.3)** — overlaps agent-system; needs dedup then Gherkin
8. **Sessions / DB** — schema + behaviors doc; no ACs

---

## Cross-Cutting Gaps

- **No RTM (Requirements Traceability Matrix)** linking GH issues → spec ACs → test files. Recommend `docs/specs/RTM.md` as a future artifact.
- **Server spec is a description, not a requirements document** — `docs-internal/architecture/server.md` documents what exists; it does not specify what must be true. Security properties (auth, rate-limiting, path validation) had no spec at all before this audit.
- **Gate/safety classifier** is documented in `docs-internal/systems/gate.md` as behavior description, not as testable ACs. G2 compound-command bypass had no Gherkin before this audit.
- **Daemon/scheduler trigger correctness** (missed-fire, cron next-tick) has no formal spec validation. The P0.5 spec §3 ACs are prose not Gherkin.
