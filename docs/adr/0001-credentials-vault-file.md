# ADR 0001 — Credentials stored in a vault file, not OS environment variables

**Status:** Accepted · 2026-06-05

## Context

`/setkey` (added alongside OpenRouter support) persisted API keys by writing the
Windows user environment (`HKCU\Environment`) via a PowerShell subprocess. Two
problems surfaced:

1. **Misleading "permanence."** The registry write *does* persist, but Windows
   never refreshes the environment of already-running processes — a process
   copies its env block at creation and never re-reads the registry. New tabs in
   an already-running terminal, and processes launched from one, do not see the
   key. The success message claimed "new shells will pick it up automatically,"
   which is false. Users read this as "the key didn't persist."
2. **Fragile/unsafe value handling.** The value was string-interpolated into a
   PowerShell command. Values containing `"`, `$`, or `&` break parsing
   (observed: returncode 1) or risk silent partial writes / command injection.

Off-spec, too: the Phase 1 PRD states API keys are env-var-only and an explicit
credential vault is later work (see roadmap "Credential Vault Upgrade").

How established harnesses handle this:

| Harness | Mechanism |
|---|---|
| Claude Code | config under `~/.claude` or OS keychain (keytar); never mutates shell env |
| OpenCode | `~/.config/opencode/` auth JSON written by `auth login`; read each launch |
| aider / Continue / Codex | `.env` or `~/.config/<tool>/config.*` the app loads itself |

The universal pattern: **the app owns a credentials file it reads at startup.**
It never mutates the OS environment. This avoids the running-process refresh
problem entirely (the app re-reads the file every launch), is cross-platform,
keeps secrets out of the process table / registry, and allows future scoping.

## Decision

Introduce `~/.aede/credentials.json` (restricted file permissions). aede
loads it into `os.environ` at startup, *before* any provider call, without
overwriting variables already present in the real environment (real env wins).
`/setkey <NAME> <value>` writes to this file (and sets `os.environ` for the
current session for immediate use). The PowerShell/registry write is removed.

This pulls the Phase-2 "Credential Vault interface" forward for the key-setting
path only; it supersedes the PRD's "env-var-only in Phase 1" statement for
credential *storage*. Reading from real environment variables remains supported
and takes precedence, so nothing that worked before breaks.

## Consequences

- **Positive:** Keys persist across reboots and new shells by design (aede
  reads the file every launch). No registry/quoting/injection bug. Cross-platform.
  Matches the OpenCode/Claude Code model. Real env vars still override, so CI and
  power users are unaffected.
- **Negative:** Secrets now live in a plaintext file on disk. Mitigated by
  restricted permissions; a future upgrade can move to OS keychain / managed
  secrets (already on the roadmap). The file must be gitignored.
- **Follow-up:** gitignore `credentials.json`; document the precedence (real env
  > vault file); Phase 4 onboarding replaces manual `/setkey` with guided setup.
