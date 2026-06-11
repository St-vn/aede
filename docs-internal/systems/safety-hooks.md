---
type: internal-doc
tags: [docs-internal, systems]
date_updated: 2026-06-10
---

# Safety Hooks

**File:** `aede/hooks.py` (52 lines)

## pre_tool_use() (`aede/hooks.py:37-52`)

Pre-execution safety gate that hard-denies dangerous shell patterns BEFORE the approval gate renders. Only checks `SHELL_TOOLS = {"powershell", "cmd"}`. All other tools pass through silently.

## Dangerous patterns (`aede/hooks.py:13-22`)

| Pattern | Targets |
|---------|---------|
| `rm\s+-rf\s+/(?!\S)` | `rm -rf /` root deletion |
| `del\s+/f\s+/s\s+/q\s+[A-Za-z]:\\$` | Windows del on root |
| `format\s+[A-Za-z]:` | Disk formatting |
| `rd\s+/s\s+/q\s+[A-Za-z]:\\$` | Windows rmdir on root |
| `mkfs\.` | Filesystem creation |
| `dd\s+if=.*of=/dev/` | Raw device overwrite |
| `shutdown` | System shutdown/reboot |
| `:\(\)\s*\{\s*:\|:&\s*\}` | Fork bomb |

Patterns compiled with `re.IGNORECASE` (`aede/hooks.py:24`). Raises `HardDeniedError` with matched pattern substring (`aede/hooks.py:29-34`).

## Integration with AgentLoop

Called in `aede/agent.py:426-438` before the approval gate. The error is injected back as a tool result — `HardDeniedError` produces `"Hard denied: command matches dangerous pattern: ..."` with `is_error=True`. Skips validation and gate entirely.
