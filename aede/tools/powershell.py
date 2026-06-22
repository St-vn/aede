"""
Shell execution tool for aede.

Supports three shell backends (``powershell``, ``cmd``, ``wsl``) selected at
router initialisation time.  All three return combined stdout+stderr; a
non-zero exit code is surfaced as a ``RuntimeError`` so the router can return
it to the model as a tool error.
"""
from __future__ import annotations
import subprocess
from typing import Any


def run_powershell(args: dict, shell: str = "powershell", wsl_distro: str = "", stream_callback: Any = None, sandbox: Any = None) -> str:
    """Execute a shell command and return its combined stdout+stderr output.

    Args:
        args: Must contain ``"cmd"`` — the command string to execute.
        shell: Backend to use: ``"powershell"`` (default), ``"cmd"``, or
            ``"wsl"``.
        wsl_distro: WSL distribution name; only used when ``shell="wsl"``.
            Passes ``-d <wsl_distro>`` to ``wsl.exe`` when set.
        sandbox: Optional ``DockerSandbox`` instance.  When set, the command
            runs inside the sandbox container instead of via ``subprocess.Popen``.

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
        if sandbox is not None:
            exit_code, output = sandbox.exec_cmd_sync(command, stream_callback=stream_callback)
            if exit_code != 0:
                raise RuntimeError(f"Exit code {exit_code}:\n{output}")
            return output

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output_parts = []
        for line in iter(proc.stdout.readline, ''):
            output_parts.append(line)
            if stream_callback:
                stream_callback(line)
        proc.wait(timeout=120)
        output = ''.join(output_parts)
        if proc.returncode != 0:
            raise RuntimeError(f"Exit code {proc.returncode}:\n{output}")
        return output
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {command[0]}")
