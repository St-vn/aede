"""
Shell execution tool for aede.

Supports three shell backends (``powershell``, ``cmd``, ``wsl``) selected at
router initialisation time.  All three return combined stdout+stderr; a
non-zero exit code is surfaced as a ``RuntimeError`` so the router can return
it to the model as a tool error.
"""
from __future__ import annotations
import subprocess


def run_powershell(args: dict, shell: str = "powershell", wsl_distro: str = "") -> str:
    """Execute a shell command and return its combined stdout+stderr output.

    Args:
        args: Must contain ``"cmd"`` — the command string to execute.
        shell: Backend to use: ``"powershell"`` (default), ``"cmd"``, or
            ``"wsl"``.
        wsl_distro: WSL distribution name; only used when ``shell="wsl"``.
            Passes ``-d <wsl_distro>`` to ``wsl.exe`` when set.

    Returns:
        Combined stdout and stderr as a single string.

    Raises:
        RuntimeError: if the command exits with a non-zero code or times out
            after 120 seconds.
    """
    cmd = args["cmd"]
    if shell == "wsl":
        if wsl_distro:
            command = ["wsl", "-d", wsl_distro, "--", "bash", "-c", cmd]
        else:
            command = ["wsl", "--", "bash", "-c", cmd]
    elif shell == "cmd":
        command = ["cmd", "/c", cmd]
    else:
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        if result.stderr:
            output += result.stderr
        if result.returncode != 0:
            raise RuntimeError(f"Exit code {result.returncode}:\n{output}")
        return output
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out after 120 seconds")
