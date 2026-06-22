---
type: doc
tags: [docs, features]
date_updated: 2026-06-20
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

## Web UI — Daemon tab

The web UI exposes a **Daemon** tab in Settings that manages the running daemon
without dropping to the CLI. It is backed by the `/api/daemon/*` REST endpoints
and refreshes live while the daemon is up.

| Section | What you can do |
|---------|-----------------|
| **Status** | See whether the daemon is running; start or stop it with a button (`GET /api/daemon/status`, `POST /api/daemon/start`, `POST /api/daemon/stop`). |
| **Timers** | List active one-shot timers and add a new one (delay + action + optional label) or delete one (`GET`/`POST` `/api/daemon/timers`, `DELETE /api/daemon/timers/{id}`). |
| **Cron** | List repeating cron jobs and add a new one (schedule expression + action + optional label) or delete one (`GET`/`POST` `/api/daemon/cron`, `DELETE /api/daemon/cron/{id}`). The schedule field is validated client-side against standard 5-field cron syntax before submit. |

Timer and cron lists only load while the daemon is running; when it is stopped
the tab shows the start control instead. File-watch and webhook **events** are
configured through the CLI/config, not this tab.
