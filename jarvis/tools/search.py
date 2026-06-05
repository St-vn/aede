from __future__ import annotations
import subprocess


def search_files(args: dict) -> str:
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
