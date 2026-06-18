"""
Interactive approval gate + permission modes + safety classifier for aede.

Before executing tools that require user consent (powershell, write_file,
create_file), the agent pauses and shows a permission prompt.  The user can
allow once, allow for the session/project/globally, deny, redirect the agent
with a text message, or approve/deny an entire batch.  Persistent approvals are
written back to ``aede.yml`` or ``~/.aede/config.yml``.

Permission modes control the default behavior:
- PLAN: read-only; write/shell denied before gate.
- NORMAL: read auto; write/shell/tools gated (ask).
- ALLOW_WRITE_READ: read + file writes auto-approved; shell still gated.
- EXECUTION: auto-approve gated tools, but route risky actions through the
  rule-based safety classifier.  Protected paths and dangerous patterns still
  require explicit approval.  Equivalent to Claude Code's auto mode with a
  lightweight local classifier.
- AUTO: true hands-free mode.  All gated tools run without prompts and agent
  questions are skipped.  Use with caution.

Agent-initiated questions (ask_user, ask_user_choices, ask_user_confirm,
question) use a separate AskUserBackend protocol so the agent can gather user
input mid-task.
"""
from __future__ import annotations
import asyncio
import re
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Tool category constants
# ---------------------------------------------------------------------------

READ_TOOLS = frozenset({
    "read_file", "list_dir", "search_files",
    "fetch_url", "web_search", "session_search",
    "select_context",
})
WRITE_TOOLS = frozenset({
    "write_file", "create_file", "write_learning",
})
SHELL_TOOLS = frozenset({"powershell", "cmd"})


# ---------------------------------------------------------------------------
# Protected paths
# ---------------------------------------------------------------------------

PROTECTED_PATHS = [
    # version control
    ".git", ".gitconfig", ".gitmodules",
    ".config/git",
    # IDE / tool configs
    ".vscode", ".idea", ".husky", ".cargo", ".devcontainer", ".yarn", ".mvn",
    # aede / claude own config
    ".claude", ".aede", "aede.yml", ".aede.yml", ".mcp.json",
    # shell configs
    ".bashrc", ".bash_profile", ".bash_login", ".bash_aliases", ".bash_logout",
    ".zshrc", ".zprofile", ".zshenv", ".zlogin", ".zlogout", ".profile", ".envrc",
    # package manager configs
    ".npmrc", ".yarnrc", ".yarnrc.yml", ".pnpmfile.cjs",
    ".bazelrc", ".bazelversion", ".bazeliskrc",
    # hooks / quality
    ".pre-commit-config.yaml", "lefthook.yml", "lefthook.yaml",
    # build wrappers
    "gradle-wrapper.properties", "maven-wrapper.properties",
    # misc
    ".devcontainer.json", ".ripgreprc", "pyrightconfig.json",
]


def _compile_protected_patterns() -> list[re.Pattern]:
    patterns: list[re.Pattern] = []
    for p in PROTECTED_PATHS:
        escaped = re.escape(p)
        patterns.append(re.compile(rf"(^|[/\\]){escaped}([/\\]|$)", re.IGNORECASE))
    return patterns


_PROTECTED_PATTERNS = _compile_protected_patterns()


def is_protected_path(path: str | Path) -> bool:
    """Return True if *path* matches a protected path segment.

    Protected paths require explicit approval for writes even in execution/auto
    modes, preventing accidental corruption of repository state and aede's own
    configuration.
    """
    s = str(path).replace("\\", "/")
    for pat in _PROTECTED_PATTERNS:
        if pat.search(s):
            return True
    return False


# ---------------------------------------------------------------------------
# Permission modes
# ---------------------------------------------------------------------------

class PermissionMode(Enum):
    """Agent permission mode controlling default tool access levels."""

    PLAN = "plan"
    NORMAL = "normal"
    ALLOW_WRITE_READ = "allow_write_read"
    EXECUTION = "execution"
    AUTO = "auto"

    @classmethod
    def from_str(cls, s: str) -> PermissionMode:
        for m in cls:
            if m.value == s:
                return m
        return cls.NORMAL

    def default_tool_action(self, tool_name: str) -> str | None:
        """Return the default action for *tool_name* under this mode, or None
        meaning the action should be gated (ask user).

        Return values: ``"allow"``, ``"deny"``, or ``None`` (use gated default).
        """
        is_read = tool_name in READ_TOOLS
        is_write = tool_name in WRITE_TOOLS
        is_shell = tool_name in SHELL_TOOLS

        if self is PermissionMode.PLAN:
            return "allow" if is_read else "deny"

        if self is PermissionMode.ALLOW_WRITE_READ:
            if is_read or is_write:
                return "allow"
            # shell still gated
            return None

        if self in (PermissionMode.EXECUTION, PermissionMode.AUTO):
            # EXECUTION relies on the safety classifier; AUTO is hands-free.
            return "allow"

        # NORMAL: read auto, everything else gated.
        if is_read:
            return "allow"
        return None


# ---------------------------------------------------------------------------
# Safety classifier (rule-based stand-in for Claude Code's auto classifier)
# ---------------------------------------------------------------------------

class SafetyDecision(Enum):
    """Outcome of the safety classifier."""

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


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


class SafetyClassifier:
    """Rule-based safety classifier for execution/auto modes.

    Mirrors Claude Code's auto-mode classifier in a lightweight, local form.
    It blocks or escalates dangerous shell patterns and writes to protected
    paths.  A true LLM-based classifier can be swapped in later without
    changing the ``PermissionStore`` interface.
    """

    # Patterns that are always denied, even in execution mode.
    _DENY_PATTERNS = [
        r"rm\s+-rf\s+/(?!\S)",          # rm -rf / but not rm -rf /some/subdir
        r"del\s+/f\s+/s\s+/q\s+[A-Za-z]:\\$",
        r"format\s+[A-Za-z]:",
        r"rd\s+/s\s+/q\s+[A-Za-z]:\\$",
        r"mkfs\.",
        r"dd\s+if=.*of=/dev/",
        r"shutdown",
        r":\(\)\s*\{\s*:\|:&\s*\}",     # fork bomb
        r"curl\s+.*\|\s*(ba)?sh",
        r"wget\s+.*\|\s*(ba)?sh",
        r"git\s+push\s+.*--force",
        r"git\s+push\s+-f\b",
        r"git\s+push\s+origin\s+(HEAD:)?main\b",
        r"git\s+push\s+origin\s+(HEAD:)?master\b",
    ]

    # Patterns that are considered read-only / safe and may run without prompt.
    _ALLOW_PATTERNS = [
        r"^git\s+status",
        r"^git\s+log",
        r"^git\s+diff",
        r"^git\s+show",
        r"^git\s+branch",
        r"^ls(\s|$)",
        r"^cat(\s|$)",
        r"^echo(\s|$)",
        r"^pwd(\s|$)",
        r"^head(\s|$)",
        r"^tail(\s|$)",
        r"^grep(\s|$)",
        r"^find(\s|$)",
        r"^wc(\s|$)",
        r"^which(\s|$)",
    ]

    def __init__(
        self,
        project_dir: Path | None = None,
        allowed_paths: list[str] | None = None,
    ) -> None:
        self.project_dir = project_dir or Path.cwd()
        self.allowed_paths = allowed_paths or []
        self._deny = [re.compile(p, re.IGNORECASE) for p in self._DENY_PATTERNS]
        self._allow = [re.compile(p, re.IGNORECASE) for p in self._ALLOW_PATTERNS]

    def classify(self, tool_name: str, args: dict[str, Any]) -> tuple[SafetyDecision, str]:
        """Classify a tool call. Returns (decision, reason)."""
        if tool_name in SHELL_TOOLS:
            return self._classify_shell(args.get("cmd", ""))
        if tool_name in WRITE_TOOLS:
            return self._classify_write(args.get("path", ""))
        # Reads and other tools are allowed by the classifier.
        return SafetyDecision.ALLOW, "read/safe tool"

    def _classify_shell(self, cmd: str) -> tuple[SafetyDecision, str]:
        if not cmd:
            return SafetyDecision.ALLOW, "empty command"
        for pat in self._deny:
            if pat.search(cmd):
                return SafetyDecision.DENY, f"matches dangerous pattern: {pat.pattern}"
        for pat in self._allow:
            if pat.search(cmd):
                return SafetyDecision.ALLOW, "read-only/safe shell command"
        return SafetyDecision.ASK, "shell command requires approval"

    def _classify_write(self, path_str: str) -> tuple[SafetyDecision, str]:
        if not path_str:
            return SafetyDecision.ASK, "write with no path"
        if is_protected_path(path_str):
            return SafetyDecision.ASK, f"protected path: {path_str}"
        try:
            target = Path(path_str).resolve()
            if self._is_under_project_or_allowed(target):
                return SafetyDecision.ALLOW, "write within project/allowed path"
        except (OSError, ValueError):
            pass
        return SafetyDecision.ASK, "write outside project/allowed paths"

    def _is_under_project_or_allowed(self, target: Path) -> bool:
        try:
            proj = self.project_dir.resolve()
            target.relative_to(proj)
            return True
        except (ValueError, OSError):
            pass
        for allowed in self.allowed_paths:
            try:
                a = Path(allowed).resolve()
                target.relative_to(a)
                return True
            except (ValueError, OSError):
                pass
        return False


# ---------------------------------------------------------------------------
# Permission store
# ---------------------------------------------------------------------------

class PermissionStore:
    """In-memory store for tool-approval grants across session, project, and global scopes.

    Session grants disappear when the process exits.  Project and global grants
    are persisted to YAML config files by ``allow_project`` and ``allow_global``.
    Supports an active PermissionMode that pre-approves or pre-denies tools
    before any gate prompt is shown.  In EXECUTION mode a rule-based safety
    classifier filters risky auto-approved actions.
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        classifier: SafetyClassifier | None = None,
    ) -> None:
        self._session: set[str] = set()
        self._project: set[str] = set()
        self._global: set[str] = set()
        self._mode: PermissionMode = PermissionMode.NORMAL
        self._project_dir = project_dir or Path.cwd()
        self._classifier = classifier or SafetyClassifier(project_dir=self._project_dir)

    @property
    def mode(self) -> PermissionMode:
        return self._mode

    @mode.setter
    def mode(self, value: PermissionMode) -> None:
        self._mode = value

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

    def tool_action(self, tool_name: str, args: dict[str, Any] | None = None) -> str | None:
        """Determine the action for *tool_name* combining mode, grants, and safety.

        Args:
            tool_name: Name of the tool being requested.
            args: Tool arguments; used by the safety classifier in EXECUTION mode.

        Returns:
            ``"allow"`` — skip gate, run the tool.
            ``"deny"`` — reject without gate.
            ``None`` — proceed to the approval gate (ask user).
        """
        from aede.tools.router import GATE_TOOLS

        if self.is_allowed(tool_name):
            return "allow"

        mode_action = self._mode.default_tool_action(tool_name)

        if mode_action == "deny":
            return "deny"

        if mode_action == "allow":
            # EXECUTION mode runs auto-allowed actions through the safety classifier.
            if self._mode is PermissionMode.EXECUTION:
                decision, _reason = self._classifier.classify(tool_name, args or {})
                if decision is SafetyDecision.ALLOW:
                    return "allow"
                if decision is SafetyDecision.DENY:
                    return "deny"
                # ASK falls through to the gate below.
            elif self._mode is PermissionMode.AUTO:
                return "allow"
            else:
                return "allow"

        # Gated tools require explicit approval.
        if tool_name in GATE_TOOLS:
            return None
        if tool_name.startswith("mcp__"):
            return None
        return "allow"

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


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

@runtime_checkable
class GateBackend(Protocol):
    """Protocol for tool-approval backends (CLI terminal or Web UI)."""

    async def request(
        self,
        gate_id: str,
        tool_name: str,
        args: dict[str, Any],
        batch_count: int,
        mode: PermissionMode | None = None,
        reason: str | None = None,
    ) -> tuple[GateDecision, str]:
        """Request approval for a tool call. Returns (decision, redirect_msg)."""
        ...


@runtime_checkable
class AskUserBackend(Protocol):
    """Protocol for agent-to-user question backends (CLI terminal or Web UI)."""

    async def ask(
        self,
        question_id: str,
        question: str,
        choices: list[str] | None = None,
    ) -> str:
        """Ask the user a question. Returns the user's response text."""
        ...


class TerminalGateBackend:
    """Wraps the terminal prompt_gate for CLI usage."""

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
        mode: PermissionMode | None = None,
        reason: str | None = None,
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
                mode=mode,
                reason=reason,
            ),
        )


class TerminalAskUserBackend:
    """CLI backend for agent-initiated questions."""

    def __init__(self, console: Any = None) -> None:
        self._console = console

    async def ask(
        self,
        question_id: str,
        question: str,
        choices: list[str] | None = None,
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: _prompt_ask_user(
                question=question,
                choices=choices,
                console=self._console,
            ),
        )


# ---------------------------------------------------------------------------
# User question prompt
# ---------------------------------------------------------------------------

def _prompt_ask_user(
    question: str,
    choices: list[str] | None = None,
    console: Any = None,
) -> str:
    """Synchronous CLI function for asking the user a question."""
    from rich.prompt import Prompt

    if console:
        console.print(f"\n[bold cyan]❓ Agent asks:[/bold cyan] {question}")
    else:
        print(f"\n? Agent asks: {question}")

    if choices:
        for i, c in enumerate(choices, 1):
            if console:
                console.print(f"  [{i}] {c}")
            else:
                print(f"  [{i}] {c}")
        if console:
            raw = Prompt.ask("Your choice") or ""
        else:
            raw = input("Your choice: ") or ""
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        return raw

    if console:
        return Prompt.ask("Your response") or ""
    return input("Your response: ") or ""


# ---------------------------------------------------------------------------
# Gate rendering and prompt
# ---------------------------------------------------------------------------

def render_gate(
    tool_name: str,
    args: dict[str, Any],
    batch_count: int = 1,
    mode: PermissionMode | None = None,
    reason: str | None = None,
) -> str:
    """Render a human-readable gate prompt string for the given tool and arguments."""
    mode_label = f"[{mode.value}] " if mode else ""
    header = f"{mode_label}⚡ {tool_name}"
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) >= 2:
            header += f"  [server: {parts[1]}]"
    lines = [header]
    if reason:
        lines.append(f"  reason: {reason}")
    if batch_count > 1:
        lines.append(f"  (part of a batch of {batch_count} tools)")
    for k, v in args.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(
        "  [A]llow once  [S]ession  [P]roject  [G]lobal  [D]eny  [R]edirect  [B]atch"
    )
    return "\n".join(lines)


def prompt_gate(
    tool_name: str,
    args: dict[str, Any],
    store: PermissionStore,
    project_dir: Path,
    global_config_path: Path,
    console: Any,
    batch_count: int = 1,
    reason: str | None = None,
) -> tuple[GateDecision, str]:
    """
    Renders the approval gate and reads a single keypress.
    Returns (decision, redirect_message).
    redirect_message is non-empty only when decision is REDIRECT.
    """
    console.print(render_gate(tool_name, args, batch_count=batch_count, mode=store.mode, reason=reason))

    key = _read_key().lower()

    if key == "a":
        return GateDecision.ALLOW_ONCE, ""
    elif key in ("s", "p", "g"):
        if key == "s":
            store.allow_session(tool_name)
            return GateDecision.ALLOW_SESSION, ""
        elif key == "p":
            store.allow_project(tool_name, project_dir)
            return GateDecision.ALLOW_PROJECT, ""
        elif key == "g":
            store.allow_global(tool_name, global_config_path)
            return GateDecision.ALLOW_GLOBAL, ""
    elif key == "d":
        return GateDecision.DENY, ""
    elif key == "r":
        msg = console.input("  Tell the agent what to do: ")
        return GateDecision.REDIRECT, msg
    elif key == "b":
        console.print("  [A]pprove all  [D]eny all")
        batch_key = _read_key().lower()
        if batch_key == "a":
            return GateDecision.BATCH_APPROVE, ""
        return GateDecision.BATCH_DENY, ""
    return GateDecision.DENY, ""


def _read_key() -> str:
    """Read a single keypress without echoing or requiring Enter."""
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


# ---------------------------------------------------------------------------
# Structured gate options for Web UI / programmatic consumers
# ---------------------------------------------------------------------------

GATE_OPTIONS = [
    {"id": "allow_once", "label": "Allow once", "key": "a"},
    {"id": "allow_session", "label": "Allow for session", "key": "s"},
    {"id": "allow_project", "label": "Allow for project", "key": "p"},
    {"id": "allow_global", "label": "Always allow", "key": "g"},
    {"id": "deny", "label": "Deny", "key": "d"},
    {"id": "redirect", "label": "Redirect", "key": "r"},
    {"id": "batch_approve", "label": "Approve batch", "key": "b"},
]


def gate_options_payload(
    tool_name: str,
    args: dict[str, Any],
    mode: PermissionMode | None = None,
    reason: str | None = None,
    batch_count: int = 1,
) -> dict[str, Any]:
    """Build a structured gate request payload for the Web UI."""
    return {
        "tool_name": tool_name,
        "args": args,
        "mode": mode.value if mode else None,
        "reason": reason,
        "batch_count": batch_count,
        "options": GATE_OPTIONS,
    }
