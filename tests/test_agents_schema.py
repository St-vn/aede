import pytest
from pathlib import Path


def test_agentdef_required_fields():
    """AgentDef requires name, description, body; defaults set for optional fields."""
    from aede.agents.schema import AgentDef

    ad = AgentDef(name="researcher", description="Research agent", body="## Body")
    assert ad.name == "researcher"
    assert ad.description == "Research agent"
    assert ad.body == "## Body"
    assert ad.model == "inherit"
    assert ad.skills == []
    assert ad.tools is None
    assert ad.disallowed_tools == []
    assert ad.max_turns == 20
    assert ad.system_prompt == ""


def test_agentdefs_required_fields_missing():
    """AgentLoadError raised when name or description is empty."""
    from aede.agents.schema import AgentDef, AgentLoadError

    with pytest.raises(AgentLoadError, match="name"):
        AgentDef(name="", description="desc", body="body")
    with pytest.raises(AgentLoadError, match="description"):
        AgentDef(name="n", description="", body="body")


def test_agentdefs_from_file_valid(tmp_path):
    """Parse YAML frontmatter + body from AGENT.md and build AgentDef."""
    from aede.agents.schema import AgentDef

    md_file = tmp_path / "researcher.md"
    md_file.write_text("""\
---
name: researcher
description: A research specialist
model: claude-haiku-4
skills: [web_search, data_analysis]
tools: [web_search, fetch_url]
disallowedTools: [powershell, write_file]
maxTurns: 15
systemPrompt: You are a research specialist.
---

# Research Agent

You focus on finding information.
""")

    ad = AgentDef.from_file(md_file)
    assert ad.name == "researcher"
    assert ad.description == "A research specialist"
    assert ad.model == "claude-haiku-4"
    assert ad.skills == ["web_search", "data_analysis"]
    assert ad.tools == ["web_search", "fetch_url"]
    assert ad.disallowed_tools == ["powershell", "write_file"]
    assert ad.max_turns == 15
    assert ad.system_prompt == "You are a research specialist."
    assert "Research Agent" in ad.body


def test_agentdefs_from_file_minimal(tmp_path):
    """Minimal frontmatter parses with defaults."""
    from aede.agents.schema import AgentDef

    md_file = tmp_path / "minimal.md"
    md_file.write_text("""\
---
name: helper
description: A simple helper
---

Helper body.
""")

    ad = AgentDef.from_file(md_file)
    assert ad.name == "helper"
    assert ad.description == "A simple helper"
    assert ad.model == "inherit"
    assert ad.skills == []
    assert ad.tools is None
    assert ad.disallowed_tools == []
    assert ad.max_turns == 20
    assert ad.system_prompt == ""


def test_agentdefs_from_file_no_frontmatter(tmp_path):
    """File without frontmatter raises AgentLoadError."""
    from aede.agents.schema import AgentDef, AgentLoadError

    md_file = tmp_path / "no_fm.md"
    md_file.write_text("Just body text.\n")

    with pytest.raises(AgentLoadError, match="no frontmatter"):
        AgentDef.from_file(md_file)


def test_agentdefs_from_file_invalid_yaml(tmp_path):
    """Invalid YAML frontmatter raises AgentLoadError."""
    from aede.agents.schema import AgentDef, AgentLoadError

    md_file = tmp_path / "bad_yaml.md"
    md_file.write_text("""\
---
name: bad
invalid: [unclosed
---

body
""")

    with pytest.raises(AgentLoadError, match="YAML"):
        AgentDef.from_file(md_file)
