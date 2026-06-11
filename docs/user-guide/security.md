---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-10
---

# Security

## Approval Gate

Before executing dangerous operations, aede pauses and shows an approval prompt. Gated tools are:

- `powershell` — arbitrary shell execution
- `write_file` — overwriting existing files
- `create_file` — creating new files
- `write_learning` — persisting memory

The gate offers these decisions:

| Decision | Meaning |
|----------|---------|
| Allow once | Run this one call |
| Allow session | Skip gate for this tool for the rest of the session |
| Allow project | Persist to `aede.yml` (project scope) |
| Allow global | Persist to `~/.aede/config.yml` |
| Deny | Reject the call |
| Redirect | Send a message back to the agent instead |

## Safety Hooks

Before the approval gate even renders, a pre-execution check hard-denies dangerous shell patterns:

- `rm -rf /` and variants
- `format C:` and variants
- `mkfs.*` commands
- `dd` destructive operations
- `shutdown` / `reboot`
- Fork bombs

These patterns are checked with case-insensitive matching and cannot be overridden.

## Credentials Vault

API keys and secrets are stored in `~/.aede/credentials.json` with best-effort file permissions (`0o600`). On startup, the vault is loaded into environment variables (real env vars take precedence). Use `/setkey <NAME> <value>` to add credentials from the REPL.

## Permission Model

Permissions are scoped at three levels:

1. **Session** — in-memory only, lost on exit
2. **Project** — persisted to `./aede.yml`
3. **Global** — persisted to `~/.aede/config.yml`

Session overrides project, which overrides global. The `auto_approve` config key lists pre-approved tool names.
