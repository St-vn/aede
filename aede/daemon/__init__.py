from __future__ import annotations
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, PermissionError):
        return False


class Daemon:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._running = False
        self._server: asyncio.AbstractServer | None = None
        self._pid = 0
        self._timers: Any = None
        self._cron: Any = None
        self._events: Any = None

    @property
    def pid_path(self) -> Path:
        return self.data_dir / "daemon.pid"

    @property
    def port_path(self) -> Path:
        return self.data_dir / "daemon.port"

    @property
    def timers(self) -> Any:
        if self._timers is None:
            from aede.daemon.timers import TimerStore
            self._timers = TimerStore(data_dir=self.data_dir)
        return self._timers

    @property
    def cron(self) -> Any:
        if self._cron is None:
            from aede.daemon.cron import CronStore
            self._cron = CronStore(data_dir=self.data_dir)
        return self._cron

    @property
    def events(self) -> Any:
        if self._events is None:
            from aede.daemon.events import EventStore
            self._events = EventStore(data_dir=self.data_dir)
        return self._events

    def is_running(self) -> bool:
        if not self.pid_path.exists():
            return False
        try:
            pid = int(self.pid_path.read_text().strip())
        except (ValueError, OSError):
            return False
        return _process_exists(pid)

    async def start(self) -> None:
        if self._running:
            raise RuntimeError("Daemon is already running")
        self._pid = os.getpid()
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text(str(self._pid))
        self._running = True
        self._server = await asyncio.start_server(
            self._handle_client, host="127.0.0.1", port=0
        )
        port = self._server.sockets[0].getsockname()[1]
        self.port_path.write_text(str(port))

    async def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self.pid_path.exists():
            self.pid_path.unlink(missing_ok=True)
        if self.port_path.exists():
            self.port_path.unlink(missing_ok=True)
        if self._timers:
            self._timers.close()
        if self._cron:
            self._cron.close()
        if self._events:
            self._events.close()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            data = await reader.readline()
            if not data:
                return
            cmd = json.loads(data.decode("utf-8"))
            resp = await self._dispatch(cmd)
            writer.write((json.dumps(resp) + "\n").encode("utf-8"))
            await writer.drain()
        except Exception as exc:
            err = {"status": "error", "message": str(exc)}
            try:
                writer.write((json.dumps(err) + "\n").encode("utf-8"))
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _dispatch(self, cmd: dict[str, Any]) -> dict[str, Any]:
        command = cmd.get("cmd", "")
        if command == "ping":
            return {"status": "ok", "pong": True}
        elif command == "status":
            return {"status": "ok", "running": self._running, "pid": self._pid}
        elif command == "stop":
            asyncio.create_task(self.stop())
            return {"status": "ok"}
        elif command == "timer_add":
            t = self.timers.add_timer(
                delay_s=cmd["delay_s"], action=cmd["action"],
                label=cmd.get("label", ""),
            )
            return {"status": "ok", "timer": {
                "id": t.id, "delay_s": t.delay_s, "action": t.action,
                "label": t.label, "fire_at": t.fire_at, "fired": t.fired,
            }}
        elif command == "timer_list":
            return {"status": "ok", "timers": [
                {"id": t.id, "delay_s": t.delay_s, "action": t.action,
                 "label": t.label, "fire_at": t.fire_at, "fired": t.fired}
                for t in self.timers.list_timers()
            ]}
        elif command == "timer_delete":
            self.timers.delete_timer(cmd["id"])
            return {"status": "ok"}
        elif command == "cron_add":
            j = self.cron.add_job(
                schedule=cmd["schedule"], action=cmd["action"],
                label=cmd.get("label", ""),
            )
            return {"status": "ok", "job": {
                "id": j.id, "schedule": j.schedule, "action": j.action,
                "label": j.label, "enabled": j.enabled,
            }}
        elif command == "cron_list":
            return {"status": "ok", "jobs": [
                {"id": j.id, "schedule": j.schedule, "action": j.action,
                 "label": j.label, "enabled": j.enabled}
                for j in self.cron.list_jobs()
            ]}
        elif command == "cron_delete":
            self.cron.delete_job(cmd["id"])
            return {"status": "ok"}
        elif command == "event_add_watch":
            e = self.events.add_watch(
                path=cmd["path"], action=cmd["action"],
                label=cmd.get("label", ""),
            )
            return {"status": "ok", "event": e.to_dict()}
        elif command == "event_add_webhook":
            e = self.events.add_webhook(
                route=cmd["route"], action=cmd["action"],
                label=cmd.get("label", ""),
            )
            return {"status": "ok", "event": e.to_dict()}
        elif command == "event_list":
            return {"status": "ok", "events": [e.to_dict() for e in self.events.list_events()]}
        elif command == "event_delete":
            self.events.delete_event(cmd["id"])
            return {"status": "ok"}
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}


async def send_command(cmd: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    d = Daemon(data_dir=data_dir)
    if not d.is_running():
        raise ConnectionError("Daemon is not running")
    if not d.port_path.exists():
        raise ConnectionError("Daemon port file not found")
    port = int(d.port_path.read_text().strip())
    try:
        reader, writer = await asyncio.open_connection(host="127.0.0.1", port=port)
        writer.write((json.dumps(cmd) + "\n").encode("utf-8"))
        await writer.drain()
        data = await reader.readline()
        resp = json.loads(data.decode("utf-8"))
        writer.close()
        return resp
    except (OSError, ConnectionError) as e:
        raise ConnectionError(f"Cannot connect to daemon: {e}") from e
