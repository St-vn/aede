from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_SUPPORTED_FIELDS = frozenset({
    "name",
    "description",
    "trigger_phrases",
    "allowed_tools",
    "model",
})


class SkillLoadError(Exception):
    """Raised when a skill definition cannot be parsed or validated."""


@dataclass
class SkillDef:
    name: str
    description: str
    trigger_phrases: list[str] = field(default_factory=list)
    allowed_tools: list[str] | None = None
    model: str | None = None
    body: str = ""
    source_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise SkillLoadError("SkillDef requires a non-empty 'name'")
        if not self.description:
            raise SkillLoadError("SkillDef requires a non-empty 'description'")

    @classmethod
    def from_file(cls, path: Path) -> SkillDef:
        file_size = path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            raise SkillLoadError(
                f"File {path} size ({file_size} bytes) exceeds maximum size "
                f"of {_MAX_FILE_SIZE} bytes"
            )

        text = path.read_text(encoding="utf-8")
        import yaml

        if not text.startswith("---"):
            raise SkillLoadError(
                f"File {path} has no frontmatter (must start with '---')"
            )

        parts = text.split("---", 2)
        if len(parts) < 3:
            raise SkillLoadError(
                f"File {path} has no frontmatter (must start with '---')"
            )

        raw_yaml = parts[1].strip()
        body = parts[2].strip()

        try:
            meta: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
        except Exception as e:
            raise SkillLoadError(f"Invalid YAML frontmatter in {path}: {e}") from e

        unknown = set(meta) - _SUPPORTED_FIELDS
        if unknown:
            logger.warning(
                "Ignoring unknown frontmatter field(s) in %s: %s",
                path,
                ", ".join(sorted(unknown)),
            )
        meta = {k: v for k, v in meta.items() if k in _SUPPORTED_FIELDS}

        name = meta.get("name", "")
        description = meta.get("description", "")
        trigger_phrases: list[str] = meta.get("trigger_phrases") or []
        allowed_tools: list[str] | None = meta.get("allowed_tools")
        model: str | None = meta.get("model")

        return cls(
            name=name,
            description=description,
            trigger_phrases=trigger_phrases,
            allowed_tools=allowed_tools,
            model=model,
            body=body,
            source_path=path,
        )
