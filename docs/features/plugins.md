---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Plugin System

The plugin system lets you enable or disable built-in skills by name. It works as an allowlist: the enabled list takes precedence over the disabled list.

## Configuration

```yaml
plugins:
  enabled: [sdlc-engineer, kaizen]
  # disabled: [research, configure]
```

## Built-in Skills

These skills ship with aede and are available under `skills/`:

| Skill | Description |
|-------|-------------|
| **sdlc-engineer** | Full SDLC lifecycle orchestration — elicit → spec → design → tasks → implement → ship |
| **configure** | First-run project configuration via ≤8-question interview; writes `aede.yml` |
| **research** | 3-track investigation (market, technical, compliance); writes structured findings |
| **kaizen** | Post-mortem logging after every bug fix or code review in critique-then-fix format |

## Toggle Logic

- Both lists empty → all skills loaded (default behavior)
- `enabled` non-empty → only those skills are loaded (allowlist)
- `disabled` non-empty → those skills excluded from the full set (denylist)
- `enabled` takes precedence if a name appears in both
