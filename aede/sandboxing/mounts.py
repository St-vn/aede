from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path


class SandboxConfigError(ValueError):
    pass


def _host_to_container_path(host: Path) -> str:
    if sys.platform == "win32":
        drive = str(host)[0].lower()
        rest = str(host)[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
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
