---
type: internal-doc
tags: [docs-internal, deferred, audit, backlog]
date_updated: 2026-06-26
---

# Deferred work — the single durable backlog

**Why this doc exists:** the holistic audit (2026-06-22→26, merged in PR #82) deliberately deferred
real findings to the right phase rather than fix everything at once. The detail used to live only in
gitignored `_scratch/holistic-audit/` (vanishes on clean). This is the **durable, checked-in** list —
the one place to check when you want to pick up deferred work. Each item has a **trigger** (when to
tackle it) and a **GH issue** ref where one exists.

**How to use:** when you have time, scan the section whose trigger has arrived (e.g. starting Phase 3 →
do the Phase-3 section). Filter GH by label: `deferred-phase3`, `deferred-phase4`, `cloud-milestone`.

---

## Phase 3 — Agent Collaboration (label: `deferred-phase3`)
Pull these in WITH the Phase-3 feature they attach to (they get reworked there; fixing now is premature).

| Item | GH | What | Carry-forward |
|------|----|----|---------------|
| Daemon scheduler | **#64** | Daemon stores timers/cron/events but has NO scheduler loop — nothing fires. Build the loop. | Proposed design + `croniter` dep in `_scratch/.../RESEARCH-opencode.md` §5. Daemon SQLite-store correctness bugs land with it. |
| Voice COR cluster | **#69** | Voice files (controller/ASR/clip-recorder) correctness + lib/context findings (14). | Fold into the Phase-3 voice round (wake-word/ASR/TTS/UX). The AudioContext mic-leak #67 was already fixed pre-Phase-3. |
| DB cascade-delete | #22 (D2) | Replace manual child-row deletion with `ON DELETE CASCADE` DDL. | Needs a rebuild-table-and-copy migration + `parent_id` policy (SET NULL vs CASCADE). See roadmap overview.md Phase 3. |
| Memory poisoning detector | (in #46/#55) | Full injection-poisoning detector. | Cheap structural containment already shipped (EX-T-05). The detector lands with the Phase-3 Memory Upgrade / poisoning-guards block. |

## Phase 4 — Mobile / SaaS hosted UI (label: `deferred-phase4`)
aede is desktop-only now; mobile/responsive is Phase 4 (pairs with the SaaS hosted web UI).

| Item | GH | What | Note |
|------|----|----|------|
| Touch targets ≥44px | **#74** (button), **#76** (dialog), **#71** (18-file cluster) | WCAG 2.5.5/2.5.8 touch-target sizing. | TOUCH/coarse-pointer criterion — N/A on desktop mouse. **Decide hit-area-vs-grow at Phase-4** (expand invisible tap zone vs grow visible buttons). Non-touch a11y on these primitives already fixed. |
| Touch portion of WS-K cluster | #78 (partial) | The touch-target items in the 21-primitive cluster. | Non-touch items (animation/sonner/scroll-area/command a11y) already handled in the desktop UI wave. |

## Pre-divergence hardening — SaaS (label: `cloud-milestone`)
Correct for single-user-desktop today; required before any multi-tenant / non-loopback deploy.

| Item | GH | What |
|------|----|----|
| Cloud-readiness gate | **#20** | Server: no auth, no rate-limit, arbitrary FS browse. The multi-tenant release gate. |
| Per-tenant STRIDE (Phase-2 carryover) | #8, #9, #10, #11 | Daemon / Sandbox / ACP / Credentials threat-model items flagged cloud-milestone. |
| Error-message info-leak | (in #35) | Full path/URL/cmd in error messages — OK single-user (errors-return-to-model), leak vector multi-tenant. |
| Local-STRIDE spoofing/repudiation | (various) | No second principal to spoof today; real once multi-user. |

**Trigger for this whole section:** starting the SaaS divergence / any non-loopback (`--host 0.0.0.0`) deploy.

---

## Wave-2 audit remainder — low/med, no individual GH issues (commented on their parent issues)
These were triaged REAL but **not pulled into the Wave-2 fix cards** (low/med, not worth expanding the
card). Detail in each parent issue's comment. Tackle opportunistically or in a "audit cleanup" pass.

| Finding | File | Parent GH | What |
|---------|------|-----------|------|
| B26 | `import_/mcp.py` | #53 | No logging on MCP import (CWE-778). |
| B27 | `import_/mcp.py` | #53 | `remote_url` from serverUrl/url passed through unvalidated (CWE-20). |
| C15-C18 | `import_/mcp.py` | #53 | Edge cases: non-dict entries silently skipped, non-string env values, empty serverUrl. |
| DKR-003 | `sandboxing/docker.py` | #63 | No container reuse when CMD exits. |
| DKR-004 | `sandboxing/docker.py` | #63 | Container reload failure silently dropped (small log fix). |
| CLT-005 | `acp/client.py` | #62 | Subprocess not reaped on double-close failure (Med). |
| CLT-003 | `acp/client.py` | #62 | Stderr forwarder exceptions silently swallowed (Low). |
| MGR-001..004, CRED-001/002, PERM-001, REG-001..004 | `acp/*` | #62 | ~16 remaining ACP correctness findings (mostly silent-failure / KeyError on malformed input). |
| WS-F soft-core | config/commands/critic/tokens/session/instructions | #70 | 14 medium findings (logging, validation) across the soft-core files. |

## Follow-ups filed during verify (2026-06-26)
| GH | What | Trigger |
|----|----|---------|
| **#83** | Landing page `/` Lighthouse Perf 72 (TBT 616ms blocking work, unrelated to the #79 ChatView fix). | UI perf pass. |
| **#84** | `/docs` renders raw YAML frontmatter as visible text (docs markdown loader not stripping frontmatter). | Docs polish. |

---

## WON'T-FIX (design-accepted) — for completeness, do NOT re-flag
These are real behaviors but intended; fixing degrades the product. Re-audits should skip them.
- **router execute_sync "no caller auth"** (#35 #1/#2/#8/#11) — the gate is the model (upstream); per-tool
  auth is the wrong layer (= the #20 SaaS-gate, not a per-tool fix).
- **errors-return-to-model** (#35 #5/#6) — explicit CLAUDE.md convention "tool errors return to the model — never hide".
- **LLM cmd → shell** (powershell #12/#16) — that IS the powershell tool; the gate + sandbox are the controls.
- **credentials env-precedence** — single-user intended; revisit at multi-tenant (= SaaS-gate).

## FALSE POSITIVES (ratified WRONG — do NOT fix)
- **B3 / B11 / B19 / C12** "IndexError on missing closing `---`" in import parsers — guarded by
  `len(parts) >= 3`. The same wrong finding was filed 3×.
- **verify-COR-LLMcrash** — `split()[0]` guarded by `if reply_text.strip()`.
- **CLT-001 / CLT-002** (ACP) — ratified OVERSTATED (16MB buffer / defensively-written `_dispatch`).
- **OTel TB3 "raw tool args to OTLP"** — overstated; spans carry only metadata, not raw args.

---

*Full audit working docs (the reasoning behind each call) are in `_scratch/holistic-audit/` — gitignored,
so if that's cleaned, this doc is the durable record. Key scratch refs: `DEFERRED-FIXES.md`,
`04-fixes/WAVE2-TRIAGE.md`, `RATIFICATION.md`, `DOUBT-design-vs-bug.md`.*
