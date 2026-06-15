from __future__ import annotations
import re
from pathlib import Path


class FileSet:
    """Tracks which paths the agent is allowed to read/write during a task.

    Default-deny: any path not explicitly allowed is rejected.
    """

    def __init__(self) -> None:
        self._allowed: set[Path] = set()
        self._workspace: Path | None = None

    def allow(self, path: Path) -> None:
        self._allowed.add(path.resolve())

    def declare_workspace(self, workspace: Path) -> None:
        self._workspace = workspace.resolve()

    def declared_set(self) -> set[Path]:
        allowed = set(self._allowed)
        if self._workspace:
            allowed.add(self._workspace)
        return allowed

    def allowed_paths(self) -> set[Path]:
        return set(self._allowed)

    def allowed(self, target: str | Path) -> bool:
        target_path = Path(target).resolve()
        if target_path in self._allowed:
            return True
        for allowed in self._allowed:
            try:
                target_path.relative_to(allowed)
                return True
            except ValueError:
                continue
        if self._workspace:
            try:
                target_path.relative_to(self._workspace)
                return True
            except ValueError:
                pass
        return False

    def reset(self) -> None:
        self._allowed.clear()
        self._workspace = None

    def declare_from_prompt(self, prompt: str) -> None:
        for match in re.finditer(r'(?:(?:src|tests?|lib|app|scripts?|docs?)\S*(?:\.\w+)?)', prompt):
            p = Path(match.group(0))
            if p.suffix in {".py", ".js", ".ts", ".rs", ".go", ".md", ".toml", ".yml", ".yaml", ".json", ".txt"}:
                self._allowed.add(p.resolve())
