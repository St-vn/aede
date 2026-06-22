---
type: doc
tags: [docs, features]
date_updated: 2026-06-20
---

# Sandboxed Execution

The sandbox subsystem provides defense-in-depth for untrusted agent output through three layers:

## FileSet (default-deny path allowlisting)

`FileSet` controls which files and directories the agent can read or write. By default all paths are denied; the allowlist defines permitted access. Configured via the `sandbox` config key.

## Docker Sandbox

When enabled, agent shell commands execute inside a Docker container instead of directly on the host. Configure via the `sandbox` key (nested object) or the flat top-level keys:

**Nested object (`sandbox:`):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable Docker sandboxing |
| `image` | string | `python:3.12-slim` | Container image to use |
| `workspace_mount` | string | `/workspace` | Mount point inside the container for the project directory |
| `memory_limit` | string | `512m` | Memory limit (e.g. `2g`) |
| `cpu_limit` | float | `1.0` | CPU quota (e.g. `1.5`) |
| `env` | object | `{}` | Extra environment variables injected into the container |

**Flat top-level keys (alternative / override):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sandbox_enabled` | bool | `false` | Enable Docker sandboxing |
| `sandbox_image` | string | `aede-sandbox:latest` | Container image to use |
| `sandbox_memory` | string | `512m` | Memory limit |
| `sandbox_cpus` | float | `1.0` | CPU quota |
| `sandbox_network` | string | `off` | Network mode: `off` (none) or `bridge` |
| `sandbox_pids_limit` | integer | `256` | Maximum number of processes in the container |
| `sandbox_pull_on_start` | bool | `true` | Pull the image before starting |
| `sandbox_filter_session_search` | bool | `false` | Strip sensitive session data from `session_search` results inside sandbox |

The container runs as user `1000:1000` with a read-only filesystem, `no-new-privileges`, and default seccomp. Only `/tmp` (64 MB tmpfs) and the data directory are writable inside the container.

## Prompt Injection Filter

Heuristic-based detection of prompt injection attempts in agent output. Uses regex patterns to identify injection techniques, base64-encoded payloads, and other attack vectors. When triggered, the output is flagged and the gate prompts for confirmation.
