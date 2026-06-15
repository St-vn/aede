from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


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
