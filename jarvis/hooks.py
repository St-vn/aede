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
    def __init__(self, matched: str) -> None:
        self.matched = matched
        super().__init__(f"Hard denied: command matches dangerous pattern: {matched!r}")


def pre_tool_use(tool_name: str, args: dict[str, Any]) -> None:
    if tool_name not in SHELL_TOOLS:
        return
    cmd = args.get("cmd", "")
    for pattern in _COMPILED:
        m = pattern.search(cmd)
        if m:
            raise HardDeniedError(matched=m.group(0))
