---
type: doc
tags: [docs, user-guide]
date_updated: 2026-06-10
---

# Configuration

## Three-Layer Merge

Configuration is resolved from three sources, each overriding the previous:

1. **Defaults** — built into aede
2. **Global** — `~/.aede/config.yml`
3. **Project** — `./aede.yml` in the current working directory

## Config File Locations

| File | Scope |
|------|-------|
| `~/.aede/config.yml` | Global user config (applies everywhere) |
| `./aede.yml` | Project-local config (overrides global) |

## Environment Variables

Environment variables take precedence over all config file values. See [Installation](../getting-started/installation.md#environment-variables) for the full list.

## Config Editing

View and edit configuration from the REPL:

```
/config                   # show effective config with source tracking
/config global model claude-sonnet-4-20250514  # set a value
/config project auto_approve +powershell        # add to list
/config project auto_approve -powershell        # remove from list
```

Use `/config global` or `/config project` without arguments to open the config file in `$EDITOR`.

## Source Tracking

Every config key tracks its origin. Run `/config` with no arguments to see which settings come from defaults, global config, or project config.

See the [Config Keys reference](../reference/config-keys.md) for all available settings.
