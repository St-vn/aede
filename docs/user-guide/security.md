---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-18
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

## Permission Modes

Use `/mode` to switch between permission modes. The mode is persisted per session and restored when you `/resume`.

| Mode | Behavior |
|------|----------|
| `plan` | Read-only. Write and shell tools are denied without prompting. |
| `normal` | Read tools run automatically; write/shell/tools prompt for approval. |
| `allow_write_read` | Read and file writes run automatically; shell still prompts. |
| `execution` | Auto-approves gated tools, but risky actions (dangerous shell patterns, writes to protected paths, writes outside the project) are still escalated to the gate. Equivalent to Claude Code's auto mode with a local rule-based classifier. |
| `auto` | Hands-free mode. All gated tools run and agent questions are answered with safe defaults. Use with caution. |

Protected paths (`.git`, `.claude`, `.aede`, shell configs, IDE/tool configs, etc.) always require explicit approval for writes in `execution` mode and are allowed only in `auto` mode.

## Voice & Privacy

When voice input is enabled, audio recordings are sent to external ASR providers (Groq, OpenAI, OpenRouter, or Google) for transcription. If no API keys are configured, transcription falls back to the browser's built-in Speech Recognition API (data stays local to the browser). Audio is not stored — only the transcription text is passed to the agent.
