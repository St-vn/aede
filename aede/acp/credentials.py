from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import os

from .registry import AgentConfig


class CredentialProvider:
    def __init__(self, home: Path) -> None:
        self._path = home / "credentials.json"
        self._cache: dict[str, str] = {}
        self._load()

    def get(self, name: str) -> str:
        val = os.environ.get(name)
        if val is not None:
            return val
        if name in self._cache:
            return self._cache[name]
        raise KeyError(f"Credential '{name}' not found in vault")

    def get_for_agent(self, config: AgentConfig) -> Optional[str]:
        if not config.credentials_ref:
            return None
        return self.get(config.credentials_ref)

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for k, v in data.items():
            if isinstance(v, dict):
                self._cache[k] = v.get("value", "")
            elif isinstance(v, str):
                self._cache[k] = v

    def set(self, name: str, value: str) -> None:
        self._cache[name] = value
        data = {}
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
        data[name] = value
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if os.name != "nt":
            os.chmod(self._path, 0o600)
