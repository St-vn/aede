"""
Interactive approval gate for aede tool calls.

Before executing tools that require user consent (powershell, write_file,
create_file), the agent pauses and shows a permission prompt.  The user can
allow once, allow for the session/project/globally, deny, redirect the agent
with a text message, or approve/deny an entire batch.  Persistent approvals
are written back to ``aede.yml`` or ``~/.aede/config.yml``.
"""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Any


class GateDecision(Enum):
    """Outcome returned by ``prompt_gate`` after the user responds."""

    ALLOW_ONCE = "allow_once"
    ALLOW_SESSION = "allow_session"
    ALLOW_PROJECT = "allow_project"
    ALLOW_GLOBAL = "allow_global"
    DENY = "deny"
    REDIRECT = "redirect"
    BATCH_APPROVE = "batch_approve"
    BATCH_DENY = "batch_deny"


class PermissionStore:
    """In-memory store for tool-approval grants across session, project, and global scopes.

    Session grants disappear when the process exits.  Project and global grants
    are persisted to YAML config files by ``allow_project`` and ``allow_global``.
    """

    def __init__(self) -> None:
        self._session: set[str] = set()
        self._project: set[str] = set()
        self._global: set[str] = set()

    def load_from_config(self, auto_approve: list[str]) -> None:
        """Seed the project grant set from the ``auto_approve`` list in config."""
        self._project.update(auto_approve)

    def is_allowed(self, tool_name: str) -> bool:
        """Return True if the tool is granted in any scope (session, project, or global)."""
        return (
            tool_name in self._session
            or tool_name in self._project
            or tool_name in self._global
        )

    def allow_session(self, tool_name: str) -> None:
        """Grant the tool for the current process lifetime only."""
        self._session.add(tool_name)

    def allow_project(self, tool_name: str, project_dir: Path) -> None:
        """Grant the tool and persist it to ``<project_dir>/aede.yml``."""
        self._project.add(tool_name)
        self._persist_project(project_dir)

    def allow_global(self, tool_name: str, global_config_path: Path) -> None:
        """Grant the tool and persist it to the global config file."""
        self._global.add(tool_name)
        self._persist_global(tool_name, global_config_path)

    def _persist_project(self, project_dir: Path) -> None:
        import yaml
        path = project_dir / "aede.yml"
        data: dict = {}
        if path.exists():
            data = yaml.safe_load(path.read_text()) or {}
        data.setdefault("auto_approve", [])
        for tool in self._project:
            if tool not in data["auto_approve"]:
                data["auto_approve"].append(tool)
        path.write_text(yaml.dump(data))

    def _persist_global(self, tool_name: str, config_path: Path) -> None:
        import yaml
        data: dict = {}
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text()) or {}
        data.setdefault("auto_approve", [])
        if tool_name not in data["auto_approve"]:
            data["auto_approve"].append(tool_name)
        config_path.write_text(yaml.dump(data))


import asyncio
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GateBackend(Protocol):
    """Protocol for tool-approval backends (CLI terminal or Web UI)."""

    async def request(
        self,
        gate_id: str,
        tool_name: str,
        args: dict[str, Any],
        batch_count: int,
    ) -> tuple[GateDecision, str]:
        """Request approval for a tool call. Returns (decision, redirect_msg)."""
        ...


class TerminalGateBackend:
    """Wraps existing prompt_gate for CLI usage.

    Maintains byte-for-byte identical behavior with the original CLI gate.
    """

    def __init__(
        self,
        store: PermissionStore | None = None,
        project_dir: Path | None = None,
        global_config_path: Path | None = None,
        console: Any = None,
    ) -> None:
        self._store = store
        self._project_dir = project_dir
        self._global_config_path = global_config_path
        self._console = console

    async def request(
        self,
        gate_id: str,
        tool_name: str,
        args: dict[str, Any],
        batch_count: int,
    ) -> tuple[GateDecision, str]:
        """Delegates to the synchronous prompt_gate in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: prompt_gate(
                tool_name=tool_name,
                args=args,
                store=self._store,  # type: ignore
                project_dir=self._project_dir,  # type: ignore
                global_config_path=self._global_config_path,  # type: ignore
                console=self._console,
                batch_count=batch_count,
            ),
        )


def render_gate(tool_name: str, args: dict[str, Any], batch_count: int = 1) -> str:
    """Render a human-readable gate prompt string for the given tool and arguments."""
    header = f"⚡ {tool_name}"
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) >= 2:
            header += f"  [server: {parts[1]}]"
    lines = [header]
    if batch_count > 1:
        lines.append(f"  (part of a batch of {batch_count} tools)")
    for k, v in args.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("  [A] Allow once  [W] Always allow  [D] Deny  [R] Redirect  [B] Approve batch")
    return "\n".join(lines)


def prompt_gate(
    tool_name: str,
    args: dict[str, Any],
    store: PermissionStore,
    project_dir: Path,
    global_config_path: Path,
    console: Any,
    batch_count: int = 1,
) -> tuple[GateDecision, str]:
    """
    Renders the approval gate and reads a single keypress.
    Returns (decision, redirect_message).
    redirect_message is non-empty only when decision is REDIRECT.
    """
    console.print(render_gate(tool_name, args, batch_count=batch_count))

    key = _read_key().lower()

    if key == "a":
        return GateDecision.ALLOW_ONCE, ""
    elif key == "w":
        console.print("  Always allow scope: [S] Session  [P] Project  [G] Global")
        scope_key = _read_key().lower()
        if scope_key == "s":
            store.allow_session(tool_name)
            return GateDecision.ALLOW_SESSION, ""
        elif scope_key == "p":
            store.allow_project(tool_name, project_dir)
            return GateDecision.ALLOW_PROJECT, ""
        elif scope_key == "g":
            store.allow_global(tool_name, global_config_path)
            return GateDecision.ALLOW_GLOBAL, ""
        return GateDecision.ALLOW_ONCE, ""
    elif key == "d":
        return GateDecision.DENY, ""
    elif key == "r":
        msg = console.input("  Tell the agent what to do: ")
        return GateDecision.REDIRECT, msg
    elif key == "b":
        console.print("  [A] Approve all  [D] Deny all")
        batch_key = _read_key().lower()
        if batch_key == "a":
            return GateDecision.BATCH_APPROVE, ""
        return GateDecision.BATCH_DENY, ""
    return GateDecision.DENY, ""


def _read_key() -> str:
    """Read a single keypress without echoing or requiring Enter.

    Uses ``msvcrt.getch`` on Windows and raw-mode ``tty`` on POSIX.
    """
    import sys
    if sys.platform == "win32":
        import msvcrt
        return msvcrt.getch().decode("utf-8", errors="replace")
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
