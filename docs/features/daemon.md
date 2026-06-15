---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Background Runtime Daemon

`aede daemon` runs a lightweight TCP server in the background that keeps the agent alive between REPL sessions. It supports scheduled cron jobs, file watch events, and one-shot timers.

## Commands

| Command | Description |
|---------|-------------|
| `aede daemon start` | Start the daemon (writes `daemon.pid` + `daemon.port` to data dir) |
| `aede daemon stop` | Stop the daemon gracefully via TCP (falls back to SIGTERM) |
| `aede daemon status` | Check if the daemon is running |
| `aede --attach` | Start a REPL that validates the daemon is alive before launching |

## Subsystems

### Cron (`daemon/cron.py`)

SQLite-backed cron-style scheduler. Each `CronJob` stores a schedule expression, action, and optional arguments. Evaluated on a polling interval.

### Events (`daemon/events.py`)

File watch and webhook event definitions persisted to SQLite. `WatchEvent` monitors file paths for changes; `WebhookEvent` fires HTTP callbacks on triggers.

### Timers (`daemon/timers.py`)

One-shot delay timers. A `Timer` fires once after a specified duration, then auto-removes. Persisted to SQLite so timers survive daemon restarts.
