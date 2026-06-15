---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Sandboxed Execution

The sandbox subsystem provides defense-in-depth for untrusted agent output through three layers:

## FileSet (default-deny path allowlisting)

`FileSet` controls which files and directories the agent can read or write. By default all paths are denied; the allowlist defines permitted access. Configured via the `sandbox` config key.

## Docker Sandbox

When enabled, agent shell commands execute inside a Docker container instead of directly on the host. `SandboxConfig` supports:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable Docker sandboxing |
| `image` | string | `ubuntu:24.04` | Container image to use |
| `workspace_mount` | string | `""` | Host path to mount as workspace |
| `memory_limit` | string | `""` | Memory limit (e.g. `2g`) |
| `cpu_limit` | float | `0` | CPU limit (e.g. `1.5`) |
| `env` | object | `{}` | Extra environment variables for the container |

## Prompt Injection Filter

Heuristic-based detection of prompt injection attempts in agent output. Uses regex patterns to identify injection techniques, base64-encoded payloads, and other attack vectors. When triggered, the output is flagged and the gate prompts for confirmation.
