from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Any


class GateDecision(Enum):
    ALLOW_ONCE = "allow_once"
    ALLOW_SESSION = "allow_session"
    ALLOW_PROJECT = "allow_project"
    ALLOW_GLOBAL = "allow_global"
    DENY = "deny"
    REDIRECT = "redirect"
    BATCH_APPROVE = "batch_approve"
    BATCH_DENY = "batch_deny"


class PermissionStore:
    def __init__(self) -> None:
        self._session: set[str] = set()
        self._project: set[str] = set()
        self._global: set[str] = set()

    def load_from_config(self, auto_approve: list[str]) -> None:
        self._project.update(auto_approve)

    def is_allowed(self, tool_name: str) -> bool:
        return (
            tool_name in self._session
            or tool_name in self._project
            or tool_name in self._global
        )

    def allow_session(self, tool_name: str) -> None:
        self._session.add(tool_name)

    def allow_project(self, tool_name: str, project_dir: Path) -> None:
        self._project.add(tool_name)
        self._persist_project(project_dir)

    def allow_global(self, tool_name: str, global_config_path: Path) -> None:
        self._global.add(tool_name)
        self._persist_global(tool_name, global_config_path)

    def _persist_project(self, project_dir: Path) -> None:
        import yaml
        path = project_dir / "jarvis.yml"
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


def render_gate(tool_name: str, args: dict[str, Any]) -> str:
    lines = [f"⚡ {tool_name}"]
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
) -> tuple[GateDecision, str]:
    """
    Renders the approval gate and reads a single keypress.
    Returns (decision, redirect_message).
    redirect_message is non-empty only when decision is REDIRECT.
    """
    console.print(render_gate(tool_name, args))

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
