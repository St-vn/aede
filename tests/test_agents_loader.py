import pytest
from pathlib import Path


def _write_agent(dir: Path, name: str, description: str, extra: str = "") -> Path:
    path = dir / "agents" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: {description}
{extra}
---

# {name.title()}

Body of {name}.
"""
    path.write_text(content)
    return path


def _write_skill(skills_dir: Path, name: str) -> Path:
    path = skills_dir / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
name: {name}
description: Skill {name}
---

Body.
"""
    path.write_text(content)
    return path


def test_agents_load_validate_skill_tool(tmp_path):
    """Agent declaring nonexistent skill or invalid tool raises AgentLoadError."""
    from aede.skills.loader import load_skills
    from aede.agents.loader import load_agents
    from aede.agents.schema import AgentLoadError

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"

    # Create a valid skill
    _write_skill(global_dir / "skills", "web_search_skill")

    # Agent that references a valid skill
    _write_agent(project_dir, "good_agent", "Uses web search",
                 extra="skills: [web_search_skill]\ntools: [web_search]")

    # Agent that references a NONEXISTENT skill
    _write_agent(project_dir, "bad_skill_agent", "References unknown skill",
                 extra="skills: [nonexistent_skill]")

    skill_registry = load_skills(global_dir=global_dir, project_dir=project_dir)
    assert "web_search_skill" in skill_registry

    # Should raise for bad_skill_agent referencing nonexistent skill
    with pytest.raises(AgentLoadError, match="nonexistent_skill"):
        load_agents(
            global_dir=global_dir,
            project_dir=project_dir,
            skill_registry=skill_registry,
            all_tool_names=["read_file", "write_file", "web_search", "powershell"],
        )


def test_agents_load_validate_tools_invalid(tmp_path):
    """Agent declaring an invalid tool name raises AgentLoadError."""
    from aede.skills.loader import load_skills
    from aede.agents.loader import load_agents
    from aede.agents.schema import AgentLoadError

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"

    _write_skill(global_dir / "skills", "generic")

    _write_agent(project_dir, "bad_tool_agent", "uses bad tool",
                 extra="tools: [nonexistent_tool_xyz]")

    skill_registry = load_skills(global_dir=global_dir, project_dir=project_dir)

    with pytest.raises(AgentLoadError, match="nonexistent_tool_xyz"):
        load_agents(
            global_dir=global_dir,
            project_dir=project_dir,
            skill_registry=skill_registry,
            all_tool_names=["read_file", "write_file"],
        )


def test_agents_load_valid(tmp_path):
    """Valid agents load successfully and are returned in registry."""
    from aede.skills.loader import load_skills
    from aede.agents.loader import load_agents

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"

    _write_skill(global_dir / "skills", "search_skill")
    _write_agent(project_dir, "researcher", "Research agent",
                 extra="skills: [search_skill]\ntools: [web_search, fetch_url]")
    _write_agent(project_dir, "writer", "Writing agent",
                 extra="skills: []")

    skill_registry = load_skills(global_dir=global_dir, project_dir=project_dir)
    agent_registry = load_agents(
        global_dir=global_dir,
        project_dir=project_dir,
        skill_registry=skill_registry,
        all_tool_names=["read_file", "write_file", "web_search", "fetch_url", "powershell"],
    )

    assert "researcher" in agent_registry
    assert "writer" in agent_registry
    assert agent_registry["researcher"].description == "Research agent"
    assert agent_registry["writer"].description == "Writing agent"


def test_agents_load_shadow(tmp_path):
    """Project agent shadows global agent by name."""
    from aede.skills.loader import load_skills
    from aede.agents.loader import load_agents

    global_dir = tmp_path / "global"
    project_dir = tmp_path / "project"

    _write_skill(global_dir / "skills", "generic")
    _write_agent(global_dir, "shared", "Global version")
    _write_agent(project_dir, "shared", "Project version")
    _write_agent(project_dir, "unique", "Only project")

    skill_registry = load_skills(global_dir=global_dir, project_dir=project_dir)
    agent_registry = load_agents(
        global_dir=global_dir,
        project_dir=project_dir,
        skill_registry=skill_registry,
        all_tool_names=["read_file"],
    )

    assert agent_registry["shared"].description == "Project version"
    assert "unique" in agent_registry
