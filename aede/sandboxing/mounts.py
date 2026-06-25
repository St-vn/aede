from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from pathlib import Path


class SandboxConfigError(ValueError):
    pass


def _host_to_container_path(host: Path) -> str:
    if sys.platform == "win32":
        s = str(host)
        drive, _ = os.path.splitdrive(s)
        if drive.startswith("\\\\") or drive.startswith("//"):
            raise ValueError("UNC host paths not supported for container mount")
        if len(s) < 2:
            raise ValueError("host path too short")
        drive_letter = s[0].lower()
        rest = s[2:].replace("\\", "/")
        return f"/mnt/{drive_letter}{rest}"
    return str(host)


def path_in_shared_paths(container_path: str, shared_paths: list[str]) -> bool:
    return any(container_path.startswith(sp) for sp in shared_paths)


@dataclass
class Mount:
    source: Path
    target: str
    type: str = "bind"
    read_only: bool = False

    def to_docker_mount(self) -> dict:
        return {
            "Source": str(self.source),
            "Target": self.target,
            "Type": self.type,
            "ReadOnly": self.read_only,
        }
