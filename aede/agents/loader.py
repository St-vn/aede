from __future__ import annotations
from pathlib import Path

from aede.agents.schema import AgentDef, AgentLoadError


def _scan_dir(agents_dir: Path) -> dict[str, AgentDef]:
    """Scan a single agents directory and return {name -> AgentDef}."""
    registry: dict[str, AgentDef] = {}
    if not agents_dir.is_dir():
        return registry
    for child in sorted(agents_dir.iterdir()):
        if child.suffix.lower() == ".md":
            try:
                ad = AgentDef.from_file(child)
                registry[ad.name] = ad
            except AgentLoadError:
                pass
    return registry


def load_agents(
    global_dir: Path,
    project_dir: Path,
    skill_registry: dict[str, object],
    all_tool_names: list[str],
) -> dict[str, AgentDef]:
    """Scan global and project agents dirs, validate, return {name -> AgentDef}.

    Validates that each agent's declared skills exist in skill_registry
    and each declared tool exists in all_tool_names. Raises AgentLoadError
    on mismatch.

    Project agents shadow global agents with the same name.
    """
    global_agents_dir = global_dir / "agents"
    project_agents_dir = project_dir / "agents"

    raw: dict[str, AgentDef] = {}
    raw.update(_scan_dir(global_agents_dir))
    raw.update(_scan_dir(project_agents_dir))

    for name, ad in raw.items():
        for skill_name in ad.skills:
            if skill_name not in skill_registry:
                raise AgentLoadError(
                    f"Agent {name!r} declares unknown skill {skill_name!r}"
                )
        if ad.tools is not None:
            for tool_name in ad.tools:
                if tool_name not in all_tool_names:
                    raise AgentLoadError(
                        f"Agent {name!r} declares unknown tool {tool_name!r}"
                    )

    return raw
