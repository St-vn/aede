from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass
class FileSet:
    declared: set[str]            # absolute host paths (as strings)
    session_id: str
    declared_at: int = 0           # ULID/ts (use time.time_ns() for simplicity)
    source: Literal["explicit", "inferred"] = "inferred"
    inferred_from_prompt: str = ""  # for audit
    project_dir: Optional[Path] = field(default=None, compare=False)

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
    def infer(cls, project_dir: Path, session_id: str, prompt_hint: str = "") -> "FileSet":
        """Default file set at session start: the project directory."""
        return cls(
            declared={str(project_dir.resolve())},
            session_id=session_id,
            source="inferred",
            inferred_from_prompt=prompt_hint,
            project_dir=project_dir.resolve(),
        )


def declare_fileset(paths: list[str], reason: str, current_fs: FileSet) -> FileSet:
    """Set FileSet to declared paths, constrained to within the session project_dir.

    All declared paths must be under the session's project_dir.  An LLM that
    supplies a system path like /etc is rejected with ValueError so the tool
    router can return the error to the model.
    """
    project_dir: Optional[Path] = getattr(current_fs, "project_dir", None)

    resolved: set[str] = set()
    for p in paths:
        resolved_path = Path(p).resolve()
        if project_dir is not None:
            resolved_project = project_dir.resolve()
            resolved_str = str(resolved_path)
            project_str = str(resolved_project)
            remainder = resolved_str[len(project_str):]
            inside = resolved_str.startswith(project_str) and (
                remainder == "" or remainder.startswith("/") or remainder.startswith("\\")
            )
            if not inside:
                raise ValueError(
                    f"declare_fileset: path {p!r} (resolved: {resolved_path}) is outside "
                    f"the session project_dir ({project_dir}).  "
                    f"Only paths under the project root may be declared."
                )
        resolved.add(str(resolved_path))

    return FileSet(
        declared=resolved,
        session_id=current_fs.session_id,
        source="explicit",
        inferred_from_prompt=reason,
        project_dir=current_fs.project_dir,
    )


def infer_fileset(project_dir: Path, session_id: str) -> FileSet:
    """Default: project root. Gets called at session start."""
    return FileSet.infer(project_dir, session_id)
