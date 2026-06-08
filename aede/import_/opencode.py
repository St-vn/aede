from __future__ import annotations
from pathlib import Path
from typing import Callable

from aede.import_.claude_code import ImportReport, import_claude_code_agent


def import_opencode_agent(
    src_path: Path,
    dest_dir: Path,
    _input_fn: Callable[[str], str] | None = None,
) -> ImportReport:
    """Import an OpenCode agent .md file into aede AGENT.md format.

    OpenCode agent schema is structurally identical to Claude Code agent schema.
    Delegates to claude_code import logic, then tags format as "OpenCode".
    """
    report = import_claude_code_agent(
        src_path=src_path,
        dest_dir=dest_dir,
        _input_fn=_input_fn,
    )
    report.format = "OpenCode"
    return report
