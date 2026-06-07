from __future__ import annotations
from pathlib import Path
from typing import Optional
import json

from .registry import AgentConfig


class CredentialProvider:
    def __init__(self, vault_dir: Path) -> None:
        self._path = vault_dir / "credentials.json"
        self._cache: dict[str, str] = {}
        self._load()

    def get(self, name: str) -> str:
        if name not in self._cache:
            raise KeyError(f"Credential '{name}' not found in vault")
        return self._cache[name]

    def get_for_agent(self, config: AgentConfig) -> Optional[str]:
        if not config.credentials_ref:
            return None
        return self.get(config.credentials_ref)

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        self._cache = {k: v for k, v in data.items() if isinstance(v, str)}
