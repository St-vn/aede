from __future__ import annotations
import subprocess


def run_powershell(args: dict, shell: str = "powershell", wsl_distro: str = "") -> str:
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
