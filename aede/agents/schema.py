from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class AgentLoadError(Exception):
    """Raised when an agent definition cannot be parsed or validated."""


@dataclass
class AgentDef:
    name: str
    description: str
    model: str = "inherit"
    skills: list[str] = field(default_factory=list)
    tools: list[str] | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    max_turns: int = 20
    system_prompt: str = ""
    body: str = ""
    source_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise AgentLoadError("AgentDef requires a non-empty 'name'")
        if not self.description:
            raise AgentLoadError("AgentDef requires a non-empty 'description'")
        if self.max_turns < 1 or self.max_turns > 200:
            raise AgentLoadError(
                f"AgentDef 'max_turns' must be between 1 and 200, got {self.max_turns}"
            )

    @classmethod
    def from_file(cls, path: Path) -> AgentDef:
        text = path.read_text(encoding="utf-8")
        import yaml

        if not text.startswith("---"):
            raise AgentLoadError(
                f"File {path} has no frontmatter (must start with '---')"
            )

        parts = text.split("---", 2)
        if len(parts) < 3:
            raise AgentLoadError(
                f"File {path} has no frontmatter (must start with '---')"
            )

        raw_yaml = parts[1].strip()
        body = parts[2].strip()

        try:
            meta: dict[str, Any] = yaml.safe_load(raw_yaml) or {}
        except Exception as e:
            raise AgentLoadError(f"Invalid YAML frontmatter in {path}: {e}") from e

        name = meta.get("name", "")
        description = meta.get("description", "")
        model = meta.get("model", "inherit")
        skills: list[str] = meta.get("skills") or []
        tools: list[str] | None = meta.get("tools")
        disallowed_tools: list[str] = meta.get("disallowedTools") or []
        max_turns: int = meta.get("maxTurns", 20)
        max_turns = max(1, min(200, max_turns))
        system_prompt: str = meta.get("systemPrompt", "")

        return cls(
            name=name,
            description=description,
            model=model,
            skills=skills,
            tools=tools,
            disallowed_tools=disallowed_tools,
            max_turns=max_turns,
            system_prompt=system_prompt,
            body=body,
            source_path=path,
        )
