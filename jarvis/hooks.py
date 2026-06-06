"""
Pre-execution safety hooks for Jarvis tool calls.

Performs a hard-deny check on shell commands before they reach the approval
gate or the subprocess layer.  Commands matching any pattern in
``DANGEROUS_PATTERNS`` are refused immediately and never shown to the user for
approval, because the risk of accidental or injected execution is too high.
"""
from __future__ import annotations
import re
from typing import Any

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/(?!\S)",          # rm -rf / but not rm -rf /some/subdir
    r"del\s+/f\s+/s\s+/q\s+[A-Za-z]:\\$",
    r"format\s+[A-Za-z]:",
    r"rd\s+/s\s+/q\s+[A-Za-z]:\\$",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
    r"shutdown",
    r":\(\)\s*\{\s*:\|:&\s*\}",     # fork bomb
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

SHELL_TOOLS = {"powershell", "cmd"}


class HardDeniedError(Exception):
    """Raised by ``pre_tool_use`` when a shell command matches a dangerous pattern."""

    def __init__(self, matched: str) -> None:
        self.matched = matched
        super().__init__(f"Hard denied: command matches dangerous pattern: {matched!r}")


def pre_tool_use(tool_name: str, args: dict[str, Any]) -> None:
    """Scan shell-tool arguments against the dangerous-pattern blocklist.

    Only checks tools in ``SHELL_TOOLS``; all other tools pass through silently.

    Raises:
        HardDeniedError: if the ``cmd`` argument matches any pattern in
            ``DANGEROUS_PATTERNS``.  The error carries the matched substring.
    """
    if tool_name not in SHELL_TOOLS:
        return
    cmd = args.get("cmd", "")
    for pattern in _COMPILED:
        m = pattern.search(cmd)
        if m:
            raise HardDeniedError(matched=m.group(0))
