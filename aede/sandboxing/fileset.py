from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class FileSet:
    declared: set[str]            # absolute host paths (as strings)
    session_id: str
    declared_at: int = 0           # ULID/ts (use time.time_ns() for simplicity)
    source: Literal["explicit", "inferred"] = "inferred"
    inferred_from_prompt: str = ""  # for audit

    def is_writable(self, path: str) -> bool:
        """Prefix match: a declared directory implies all its children are writable.

        Uses Path(path).resolve() to handle symlinks and '..' traversal.
        Returns True if path starts with any declared prefix.
        """
        resolved = str(Path(path).resolve())
        for declared_path in self.declared:
            resolved_declared = str(Path(declared_path).resolve())
            if resolved.startswith(resolved_declared):
                # Ensure match is at a path boundary (not just string prefix)
                remainder = resolved[len(resolved_declared):]
                if remainder == "" or remainder.startswith("/") or remainder.startswith("\\"):
                    return True
        return False

    @classmethod
    def infer(cls, project_dir: Path, session_id: str, prompt_hint: str = "") -> FileSet:
        """Default file set at session start: the project directory."""
        return cls(
            declared={str(project_dir.resolve())},
            session_id=session_id,
            source="inferred",
            inferred_from_prompt=prompt_hint,
        )


def declare_fileset(paths: list[str], reason: str, current_fs: FileSet) -> FileSet:
    """Set FileSet to declared paths. Resolves each path first."""
    resolved = {str(Path(p).resolve()) for p in paths}
    return FileSet(
        declared=resolved,
        session_id=current_fs.session_id,
        source="explicit",
        inferred_from_prompt=reason,
    )


def infer_fileset(project_dir: Path, session_id: str) -> FileSet:
    """Default: project root. Gets called at session start."""
    return FileSet.infer(project_dir, session_id)
