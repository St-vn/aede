import pytest
from pathlib import Path


def test_import_skill_fidelity(tmp_path):
    """Claude Code skill maps 1:1 to aede SKILL.md format."""
    from aede.import_.skills import import_claude_code_skill

    src = tmp_path / "kaizen"
    src.mkdir()
    (src / "SKILL.md").write_text("""\
---
name: kaizen
description: |
  Continuous improvement logger.
model: claude-sonnet-4-20250514
hidden: true
trigger: /kaizen
allowed-tools:
  - Read
  - Write
---

Log post-mortems.
""")

    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir)

    assert report.name == "kaizen"
    assert report.dest_path.exists()
    assert report.dest_path.suffix == ".md"

    content = report.dest_path.read_text()
    assert "name: kaizen" in content
    assert "description:" in content
    assert "Continuous improvement logger" in content
    assert "model: claude-sonnet-4-20250514" in content
    assert "allowed_tools:" in content
    assert "trigger_phrases:" in content
    assert "# hidden" in content
    assert "Log post-mortems." in content


def test_import_skill_directory_detection(tmp_path):
    """Passing a directory finds SKILL.md inside."""
    from aede.import_.skills import import_claude_code_skill

    src = tmp_path / "my_skill"
    src.mkdir()
    (src / "SKILL.md").write_text("""\
---
name: my-skill
description: Test skill
---

Body here.
""")

    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir)
    assert report.name == "my-skill"
    assert "Body here." in report.dest_path.read_text()


def test_import_skill_prompt_before_overwrite(tmp_path):
    """Prompts before overwriting existing file."""
    from aede.import_.skills import import_claude_code_skill

    src = tmp_path / "skill.md"
    src.write_text("""\
---
name: tester
description: Test skill
---

Body.
""")

    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()
    existing = dest_dir / "tester.md"
    existing.write_text("original")

    prompt_called = [False]

    def fake_input(prompt_text):
        prompt_called[0] = True
        return "y"

    report = import_claude_code_skill(
        src_path=src, dest_dir=dest_dir,
        _input_fn=fake_input,
    )

    assert prompt_called[0]
    assert report.dest_path.read_text() != "original"


def test_import_skill_traversal_blocked(tmp_path):
    """name: ../../../EVIL in frontmatter is slugified to evil.md inside dest_dir."""
    from aede.import_.skills import import_claude_code_skill

    src = tmp_path / "evil_frontmatter.md"
    src.write_text("""\
---
name: ../../../EVIL
description: Traversal attempt
---
Body.
""")

    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir)

    assert report.name == "evil"
    assert report.dest_path == dest_dir / "evil.md"
    assert report.dest_path.exists()
    children = list(dest_dir.iterdir())
    assert len(children) == 1
    assert children[0].name == "evil.md"


def test_import_skill_skip_on_no_overwrite(tmp_path):
    """When user declines overwrite, original file is preserved."""
    from aede.import_.skills import import_claude_code_skill

    src = tmp_path / "skill.md"
    src.write_text("""\
---
name: tester
description: Test skill
---

Body.
""")

    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()
    existing = dest_dir / "tester.md"
    existing.write_text("original")

    def fake_input(prompt_text):
        return "n"

    report = import_claude_code_skill(
        src_path=src, dest_dir=dest_dir,
        _input_fn=fake_input,
    )

    assert report.dest_path.read_text() == "original"
    assert report.was_skipped
