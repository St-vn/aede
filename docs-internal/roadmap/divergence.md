---
type: internal-doc
tags: [docs-internal, roadmap, divergence]
date_updated: 2026-06-14
---

# Divergence Point Roadmap

**The fork point between aede (open-core) and the commercial SaaS that builds on it.**

Last updated: 2026-06-14
Owner: aede
Status: draft — aede is still single-user; the SaaS layer is the Phase 4 work in `aede-roadmap.md` line 417+

---

## TL;DR

- **aede** stays as the open-core agent harness — the upstream. Phase 1+2+3 work. Single-user local install, multi-user when self-hosted. The community product (OpenClaw / Hermes model).
- **SaaS** is a **separate repo, copied base**. Uses aede as a library. Adds the multi-tenant cloud layer: auth, billing, hosted web UI, observability, rate limiting, FDE telemetry.
- **Personal aede** is your local install of aede. The canary. New aede features land there first; the SaaS pulls from aede as a stable subset.

The Phase 2/3 work that landed on `merge-phase2` is the foundation both build on. This doc defines the seam.

---

## 1. What's in aede (the open-core)

Phase 1+2+3 deliverables, in scope for the public aede:

| Module | Purpose | Why it's in aede |
|---|---|---|
| `aede/agent.py` | Core `AgentLoop` | The product. Multi-turn + tool calling is the harness. |
| `aede/provider.py` | LLM provider abstraction (Anthropic + OpenAI-compatible) | Universal. Any user needs it. |
| `aede/tools/` | Tool router + built-in tools (read/write/list, powershell, web, search) | Universal. |
| `aede/skills/` + `aede/agents/` | Skills + AGENT.md subagent system | The customization vector — the *headline* feature. |
| `aede/mcp/` | MCP bridge | The plugin interface. |
| `aede/memory/` | Learnings store + retrieval + verifier | Universal across users. |
| `aede/acp/` | ACP connections (subprocess management, auth, registry) | The connectivity layer. |
| `aede/server.py` + `ui/` | FastAPI backend + Next.js web UI | Universal — every install gets the web UI. |
| `aede/import_/` | Converters from 6 other harnesses | Adoption lever. |
| `aede/db.py` | SQLite + WAL + FTS5 | Default local store. Per-user DB. |
| `aede/gate.py`, `aede/hooks.py` | Approval gate + safety hooks | Universal safety. |
| `aede/compaction.py`, `aede/critic.py`, `aede/trace/` | Context mgmt, asymmetric critic, GEPA trace | Universal. |

Phase 3 work (background runtime, cross-harness interop, visual agent builder, etc.) **also lands in aede** — these are harness improvements, not commercial product differentiation.

---

## 2. What's NOT in aede (the SaaS layer)

These are **Phase 4** items from `aede-roadmap.md` line 417+. They are NOT aede's responsibility — they live in the SaaS repo:

| Concern | Owner | Why it's SaaS-only |
|---|---|---|
| **Auth** (Supabase Auth, OAuth) | SaaS | aede's only auth is the local credential vault. SaaS needs real user accounts. |
| **Multi-tenancy** (per-user DB isolation, per-user rate limits) | SaaS | aede is single-DB-per-install. SaaS needs per-tenant boundary. |
| **Hosting** (Fly.io API + Vercel SPA + Cloudflare) | SaaS | aede is local-first. SaaS is cloud. |
| **Billing** (Stripe) | SaaS | aede is free. |
| **Hosted web UI** (the SaaS instance of `ui/`) | SaaS | aede's web UI is for the local install. SaaS UI may re-skin or extend it. |
| **GDPR/PIPEDA** (data export, data deletion) | SaaS | aede's user owns their data. SaaS has a data controller relationship. |
| **Observability** (Langfuse, OTel) | SaaS | aede's only telemetry is the local GEPA trace. SaaS aggregates cross-user. |
| **Field feedback loop / FDE telemetry** (opt-in usage capture) | SaaS | aede doesn't phone home. SaaS does, with consent. |
| **Rate limiting** (per-user, per-tenant) | SaaS | aede has none. |
| **Status page, public docs site, marketing site** | SaaS | aede's docs are at `docs/`. SaaS has its own surface. |

The Phase 4 "Consumer UX" block (NL workflow creation, onboarding flow, marketplace) is *also* SaaS-only — these are the commercial product differentiators that justify the SaaS existing.

---

## 3. The import surface (the seam)

The boundary between aede and the SaaS is the **Python import surface**. Everything listed in §1 should be importable as a library. The SaaS repo's `pyproject.toml` does:

```toml
dependencies = [
    "aedeai @ git+ssh://git@github.com/you/aede.git@vX.Y.Z",
    # ... SaaS-specific deps
]
```

And the SaaS code does:

```python
from aede.agent import AgentLoop
from aede.acp.manager import AcpManager
from aede.skills.loader import load_skills
# etc.
```

**The seam contract (locked):**
- aede exposes a **stable, documented import surface** for the modules the SaaS uses.
- aede's **CLI surface is not the seam** — the SaaS doesn't shell out to `aede`, it imports.
- aede's **per-user database format is the seam** — the SaaS can read aede's SQLite schema (sessions, messages, learnings) for migration/integration.
- aede's **skill/agent file formats are the seam** — `SKILL.md` and `AGENT.md` files written by aede work in the SaaS unchanged.

**What the SaaS may NOT do:**
- Modify aede source code in place (use the version pin, fork if you must, but don't monkey-patch).
- Reach into aede's internal modules (anything not in the import surface is subject to change).
- Bypass aede's approval gate (security boundaries are non-negotiable).

**Versioning:**
- aede follows SemVer. The SaaS pins to a major version (`aedeai>=2,<3`) and updates deliberately.
- Breaking changes to the import surface require a major version bump and a changelog entry.

---

## 4. Personal aede vs the SaaS — three relationship options

You picked "not sure" — that's fine, this section lays out the three options so you can decide later.

### Option A: Personal aede is the canary

- You run aede on your machine. New features land there first, you dogfood them.
- Stable features eventually get tagged on aede and the SaaS pulls from a stable version pin.
- **Best when:** you're iterating fast on aede and want feedback before SaaS users see changes.
- **Tradeoff:** the SaaS is always one step behind your personal install.

### Option B: Personal aede is downstream of the SaaS

- The SaaS is canonical. You run aede as a checkout/profile on your machine, configured to use the SaaS as the backend.
- Personal config (your private skills, agents, credentials) lives in `~/.aede/` and is a runtime overlay on the SaaS binary.
- **Best when:** you want the SaaS to be the source of truth and personal use is just "the same product, locally."
- **Tradeoff:** the SaaS has to expose a self-hosting path that personal can use.

### Option C: Siblings (no parent/child)

- Personal aede and the SaaS both pull from the aede library. Neither is canonical. They share a common base but evolve independently.
- **Best when:** the two surfaces need to diverge fast (e.g. you ship an experimental feature in personal that never makes it to aede or the SaaS).
- **Tradeoff:** most discipline required — you have to keep the shared subset clean and resist the temptation to fork inside aede.

**Recommendation for MVP:** start with **Option A (canary)**. It's the lowest-friction for getting to a SaaS MVP — personal aede already works, you dogfood there, and the SaaS just consumes the stable subset.

---

## 5. What lands in aede vs the SaaS — the 4 spec'd Phase 2 sections

| Spec | aede (open-core) | SaaS |
|---|---|---|
| MCP client | Yes (general plugin interface) | Reuses — configures MCP servers per tenant. |
| Agent System (SKILL.md / AGENT.md / subagents) | Yes (the customization vector) | Reuses + extends: per-tenant skill library, role-based agent visibility. |
| Memory System (learnings + retrieval + verifier) | Yes (single-user) | Reuses — per-tenant learnings DB (same schema, separate DBs). |
| Basic Correctness (grounding + critic) | Yes (harness quality) | Reuses. |

The SaaS adds **multi-tenant wrappers** around the same modules: per-tenant `AedeConfig`, per-tenant `DB`, per-tenant `LearningsStore`, per-tenant ACP registry.

---

## 6. Phase 3 triage — aede vs SaaS vs defer vs ignore

**Multi-agent orchestration is explicitly omitted** per the 2026-06-14 decision (the user wants aede to be a single-agent harness, not a multi-agent orchestrator). This removes the "Multi-agent debate" item entirely and keeps the orchestrator/single-agent stance from `aede-roadmap.md`.

For each Phase 3 block, four destinations:

### aede (open-core) — lands in aede regardless

| Block | Why in aede |
|---|---|
| Sandboxing Upgrade (microVM) | Gated by Docker→microVM threshold; aede owns the sandboxing primitive. The SaaS reuses via the same import surface. |
| Memory Upgrade — pgvector | Gated by codebase size threshold; aede owns the memory store. |
| Memory Upgrade — Learning TTL + pruning | Quality-of-life for any user; the SaaS reuses. |
| Memory Upgrade — Poisoning guards | Security; required for SaaS users with adversarial inputs. |
| Self-Improvement — Skill auto-creation | The Hermes pattern; aede owns the loop. |
| Self-Improvement — Skill curator | Pruning companion to auto-creation. |
| Self-Improvement — DSPy/GEPA | Locked: needs metric + held-out set first. aede owns the optimization loop when ready. |
| ACP Chat Integration | Done in P0.1 commit `8000c40` + `6c40742`. |
| Background Runtime — Daemon | The multi-tenant foundation. The SaaS is a daemon process. **Must-have pre-divergence.** |
| Background Runtime — Timers / cron / event triggers | The daemon needs these to actually do anything. **Must-have pre-divergence.** |
| SOUL.md (agent identity + phonemes + wake word) | The agent's name, persona, wake word, and phonemes live in a config file. Loader is aede-side. **Must-have pre-divergence** (per 2026-06-14 user decision: wake word is not a luxury, users want it, ship pre-divergence). |
| Voice input subsystem (web UI mic + Web Speech API + browser continuous wake word) | The voice input path is part of the aede web UI. The SaaS reuses — each tenant can enable voice. **Must-have pre-divergence.** |
| Workflow Automation | n8n-style; aede owns the loop. |
| Observability (OTel, Langfuse) | The `TraceLogger` is already in aede; OTel is a thin adapter. **Must-have pre-divergence** (the SaaS needs cross-tenant aggregation). |
| Field Feedback Loop (FDE) — opt-in capture | Aede-side: the capture + redaction primitive. **Must-have pre-divergence** for SaaS feedback loop. |

### SaaS-only — does NOT land in aede

| Block | Why SaaS-only |
|---|---|
| Multi-Channel Gateway (Slack, etc.) | Per-tenant channel config + per-channel auth — aede doesn't know what channels exist. SaaS owns. |
| Field Feedback Loop (FDE) — feedback → spec/evals | The aggregation + privacy gate + consent UI is SaaS-side. The aede-side capture (above) is the seam. |
| Customer-facing observability dashboards | The SaaS has the users; aede doesn't. |
| Stripe / billing / pricing tiers | SaaS. |

### Defer (post-divergence, build in either side as needed)

| Block | Why defer |
|---|---|
| Visual Agent Builder | UX, not capability gap. v0.3+. |
| Keybind customization | UX, not core. v0.3+. |
| Keybind import | Depends on keybind customization. v0.3+. |
| Cross-harness interop | Distinct from ACP (which is already in). Build when a user actually needs to drive Claude Code from aede live. v0.3+. |
| Local TTS for voice responses | The input side (Web Speech API → text) is in aede. The output side (text → speech) needs a TTS engine. Defer to v0.4+ — pair with a chosen TTS engine (piper, OpenAI TTS, etc.). |
| Native cross-platform wake word (Porcupine/openWakeWord) | Browser-based wake word covers "any device with a browser". Native bindings per-OS are a large lift; defer to v0.4+ unless user feedback demands. |
| iOS Shortcut / Android Tasker integrations | Zero aede code needed (just a stable HTTP endpoint, which the daemon provides). Built as separate iOS/Android apps post-divergence. |
| Other Tools (Full Browser Use, image gen) | Playwright MCP covers browser; image gen is niche. v0.4+. |
| Workflow Automation | The pattern is clear; the actual n8n integration is large. Build when there's a real use case. v0.3+. |
| Self-Improvement — Executable skill bodies | **Locked: "v1 self-improvement writes typed *learnings* only, never code"** (defer note line 26). v0.4+ at earliest. |

### Ignore entirely (do not build)

| Block | Why ignore |
|---|---|
| Multi-agent debate | **Locked: research-confirmed loses to self-consistency at equal budget (2.1-3.4×).** Asymmetric critic covers the need. |
| Executable skill bodies (auto-generated code) | Locked (above). Hard "no" until microVM sandbox + reproducibility gate exist. |

### Net effect on the gap backlog

Adding Phase 3 to the pre-divergence must-haves means P0 expands. New P0 items to add to the gap backlog:

- **P0.5 Background Runtime — Daemon + Timers + Cron + Event triggers** (~600-1000 LOC). The SaaS cannot be multi-tenant without a daemon.
- **P0.6 Observability — OTel adapter for TraceLogger** (~200-300 LOC). The SaaS needs cross-tenant trace aggregation.
- **P0.7 FDE — opt-in capture + redaction** (~200-400 LOC). Required for the SaaS feedback loop.
- **P0.8 SOUL.md — agent identity config with phonemes** (~100-200 LOC). The agent's name, persona, wake word, and phonetic pronunciation live in a single config file. Mirrors the `SKILL.md` loader pattern.
- **P0.9 Voice input — push-to-talk + browser continuous wake word** (~700-1200 LOC). Web Speech API integration in the web UI. Reads the wake word from SOUL.md. Works on any device with a supported browser.

The Memory Upgrade (pgvector, TTL, poisoning) and Self-Improvement (auto-creation, curator) are not pre-divergence must-haves — they can land in aede after the SaaS fork, and the SaaS updates its pin when they ship.

---

## 7. Concrete next moves for the SaaS

In rough dependency order (lowest first):

1. **Tag a stable aede version.** Once `merge-phase2` lands to main and you've validated it for a week, cut `v0.2.0`. This is the first version the SaaS imports.
2. **Create the SaaS repo.** Private initially. `pyproject.toml` pins `aedeai>=0.2,<0.3`. Single FastAPI process that imports `aede.server.app` and adds a Supabase auth middleware.
3. **Add per-tenant DB isolation.** The cleanest way: aede's `DB` already takes a `path` argument. The SaaS passes `/var/lib/saas/tenants/<user_id>/aede.db`. Zero aede changes needed.
4. **Add Supabase auth.** The SaaS middleware verifies the JWT on every request, extracts `user_id`, and constructs the per-tenant `AedeConfig` + `DB`.
5. **Wire Stripe.** Per-tenant subscription state in Supabase. Free tier caps via the rate-limiter (next step).
6. **Rate limit.** Per-tenant token + request budget. Implemented as a SaaS middleware that calls into aede's existing `tokens.py` for cost estimation.
7. **Hosted web UI.** The existing `ui/` works as-is against the SaaS API. The SaaS may want to re-skin for branding, but no aede changes are required.
8. **GDPR endpoints.** `GET /api/me/export` and `DELETE /api/me` — both are SaaS-side, they walk aede's SQLite tables for the tenant and dump/delete.
9. **Observability.** Wrap aede's `TraceLogger` calls with OTel spans. The GEPA traces already in aede are the substrate.
10. **Opt-in FDE telemetry.** An additional consent gate + a SaaS-side endpoint that ingests opt-in events.

Steps 1-3 are the **MVP**. Steps 4-7 are the **shippable beta**. Steps 8-10 are the **public launch** checklist.

---

## 7. Open questions for the SaaS design

These are deliberately not pinned down yet — they depend on the product surface choice (multi-tenant cloud harness vs. new product building on aede as a library):

- **Q1: Does the SaaS have its own front-end, or is it a re-skin of aede's web UI?**
  - Re-skin: fastest to MVP. Differentiate later.
  - Custom front-end: more work, more differentiation potential.
- **Q2: Does the SaaS expose a public API?**
  - If yes: design the API surface as a stable contract (it'll become its own product surface).
  - If no: keep everything web-UI-only.
- **Q3: Does the SaaS support teams/orgs, or is it per-user only?**
  - Per-user only: simplest. Single Supabase `user_id` key.
  - Teams: add an `org_id` layer. Multiplies every per-tenant consideration.
- **Q4: What's the pricing model?**
  - Flat per-seat: simple, fits "personal AI agent" pitch.
  - Usage-based (token consumption): more honest, more complex billing.
  - Tiered (free / pro / team): standard SaaS, but adds marketing surface.

The MVP doesn't need answers to all four — Q1 and Q4 are the urgent ones.

---

## 8. What this doc is NOT

- Not a product spec for the SaaS. The SaaS design lives in the SaaS repo, not here.
- Not the canonical Phase 3 backlog for aede. That lives in `phase2-gap-backlog.md` and `aede-roadmap.md`. §6 here is the *triage* (aede vs SaaS vs defer vs ignore), not the full spec.
- Not a list of features the SaaS should copy from aede. The SaaS picks what it needs.

The sole purpose: **define the seam** so aede can keep evolving freely while the SaaS depends on a stable subset.
