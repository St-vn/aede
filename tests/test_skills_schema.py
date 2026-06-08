import pytest
from pathlib import Path


def test_skilldef_required_fields():
    """SkillDef requires name, description, body; defaults set for optional fields."""
    from aede.skills.schema import SkillDef

    sd = SkillDef(name="test", description="a test", body="## Body\ncontent")
    assert sd.name == "test"
    assert sd.description == "a test"
    assert sd.body == "## Body\ncontent"
    assert sd.trigger_phrases == []
    assert sd.allowed_tools is None
    assert sd.model is None


def test_skilldefs_required_fields_missing():
    """SkillLoadError raised when name or description is empty."""
    from aede.skills.schema import SkillDef, SkillLoadError

    with pytest.raises(SkillLoadError, match="name"):
        SkillDef(name="", description="desc", body="body")
    with pytest.raises(SkillLoadError, match="description"):
        SkillDef(name="n", description="", body="body")


def test_skilldefs_from_file_valid(tmp_path):
    """Parse YAML frontmatter + body from a .md file and build SkillDef."""
    from aede.skills.schema import SkillDef

    md_file = tmp_path / "test_skill.md"
    md_file.write_text("""\
---
name: my-skill
description: Does something useful
trigger_phrases: [hello, world]
allowed_tools: [read_file, web_search]
model: claude-haiku-4
---

# My Skill

Do the thing.
""")

    sd = SkillDef.from_file(md_file)
    assert sd.name == "my-skill"
    assert sd.description == "Does something useful"
    assert sd.trigger_phrases == ["hello", "world"]
    assert sd.allowed_tools == ["read_file", "web_search"]
    assert sd.model == "claude-haiku-4"
    assert "My Skill" in sd.body
    assert "Do the thing." in sd.body


def test_skilldefs_from_file_minimal(tmp_path):
    """Minimal frontmatter (name + description only) parses correctly."""
    from aede.skills.schema import SkillDef

    md_file = tmp_path / "minimal.md"
    md_file.write_text("""\
---
name: minimal
description: A minimal skill
---

Just some body text.
""")

    sd = SkillDef.from_file(md_file)
    assert sd.name == "minimal"
    assert sd.description == "A minimal skill"
    assert sd.trigger_phrases == []
    assert sd.allowed_tools is None
    assert sd.model is None
    assert "Just some body text." in sd.body


def test_skilldefs_from_file_no_frontmatter(tmp_path):
    """File without frontmatter raises SkillLoadError."""
    from aede.skills.schema import SkillDef, SkillLoadError

    md_file = tmp_path / "no_fm.md"
    md_file.write_text("Just body text without frontmatter.\n")

    with pytest.raises(SkillLoadError, match="no frontmatter"):
        SkillDef.from_file(md_file)


def test_skilldefs_from_file_invalid_yaml(tmp_path):
    """Invalid YAML frontmatter raises SkillLoadError."""
    from aede.skills.schema import SkillDef, SkillLoadError

    md_file = tmp_path / "bad_yaml.md"
    md_file.write_text("""\
---
name: bad
description: bad
invalid_yaml: [unclosed
---

body
""")

    with pytest.raises(SkillLoadError, match="YAML"):
        SkillDef.from_file(md_file)
