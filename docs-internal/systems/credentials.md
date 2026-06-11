---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Credentials Vault

**File:** `aede/credentials.py` (152 lines)

**Path:** `~/.aede/credentials.json`

## Functions

| Function | Description | Line |
|----------|-------------|------|
| `load_credentials_into_env(home)` | Read vault → `os.environ`. Real env vars take precedence. | 24-62 |
| `set_credential(home, name, value, provider)` | Write to vault (create file if needed), best-effort `os.chmod(0o600)` | 65-95 |
| `list_credentials(home)` | List stored key names + providers | 98-131 |
| `delete_credential(home, name)` | Remove from vault (no-op if missing) | 134-152 |

## Format

Backward-compatible with both flat and structured formats:
```json
{"ANTHROPIC_API_KEY": "sk-ant-..."}
{"DEEPSEEK_API_KEY": {"value": "sk-...", "provider": "deepseek"}}
```

## Security

Best-effort file permission restriction via `os.chmod(path, 0o600)` (`aede/credentials.py:92-95`). Graceful fallback on Windows where chmod is limited. Real environment variables always take precedence over vault values (`aede/credentials.py:54-55`).

## Integration

Credentials loaded early in bootstrap (`aede/cli.py:293-297`) before config merge, session creation, or agent loop initialization. `/setkey <NAME> <value>` CLI command writes + sets in current environment.
