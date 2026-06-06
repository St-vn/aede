"""
File search tool for aede, backed by ripgrep.

Searches for a regex pattern across a directory tree and returns matching
lines with file paths and line numbers.  Requires ``rg`` to be on the PATH.
"""
from __future__ import annotations
import subprocess


def search_files(args: dict) -> str:
    """Search for a regex pattern in files under a directory using ripgrep.

    Args:
        args: Must contain ``"pattern"`` (regex) and ``"path"`` (directory or file).

    Returns:
        Matching lines in ``file:line:content`` format, or ``"(no matches)"``
        if nothing was found.

    Raises:
        RuntimeError: if ripgrep exits with an error code, or if ``rg`` is not
            installed.
    """
    pattern = args["pattern"]
    path = args["path"]

    try:
        result = subprocess.run(
            ["rg", "--line-number", "--with-filename", pattern, path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout or "(no matches)"
        if result.returncode == 1:
            return "(no matches)"
        raise RuntimeError(f"ripgrep error: {result.stderr}")
    except FileNotFoundError:
        raise RuntimeError("ripgrep (rg) not found. Install ripgrep: https://github.com/BurntSushi/ripgrep")
