"""
Pre-execution safety hooks for aede tool calls.

Performs a hard-deny check on shell commands before they reach the approval
gate or the subprocess layer.  Commands matching any pattern in
``DANGEROUS_SHELL_PATTERNS`` are refused immediately and never shown to the user
for approval, because the risk of accidental or injected execution is too high.

``DANGEROUS_SHELL_PATTERNS`` is the single source of truth for the dangerous-
pattern blocklist, shared by both this module and ``aede.gate.SafetyClassifier``.
``DANGEROUS_PATTERNS`` is kept as an alias for backward compatibility.
"""
from __future__ import annotations
import re
from typing import Any

# Single source of truth — union of the old hooks list and the old gate list.
# Both the hard-deny layer (this module) and the soft gate (gate.py) reference
# this same list so they can never drift apart.
DANGEROUS_SHELL_PATTERNS: list[str] = [
    r"rm\s+-rf\s+/(?!\S)",                       # rm -rf / (not a subdir)
    r"del\s+/f\s+/s\s+/q\s+[A-Za-z]:\\$",       # Windows root delete
    r"format\s+[A-Za-z]:",                        # format drive
    r"rd\s+/s\s+/q\s+[A-Za-z]:\\$",             # Windows root rmdir
    r"mkfs\.",                                    # make filesystem
    r"dd\s+if=.*of=/dev/",                       # dd to device
    r"shutdown",                                  # shutdown/reboot
    r":\(\)\s*\{\s*:\|:&\s*\}",                  # fork bomb
    r"curl\s+.*\|\s*(ba)?sh",                    # curl | sh
    r"wget\s+.*\|\s*(ba)?sh",                    # wget | sh
    r"git\s+push\s+.*--force",                   # git push --force
    r"git\s+push\s+-f\b",                        # git push -f
    r"git\s+push\s+origin\s+(HEAD:)?main\b",     # git push origin main
    r"git\s+push\s+origin\s+(HEAD:)?master\b",   # git push origin master
]

# Backward-compatible alias — existing callers that imported DANGEROUS_PATTERNS
# continue to work unchanged.
DANGEROUS_PATTERNS = DANGEROUS_SHELL_PATTERNS

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_SHELL_PATTERNS]

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
