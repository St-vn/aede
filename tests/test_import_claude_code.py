import pytest
from pathlib import Path


def test_import_claude_code_fidelity(tmp_path):
    """Claude Code agent .md file maps 1:1 to AGENT.md format."""
    from aede.import_.claude_code import import_claude_code_agent

    src = tmp_path / "claude_agent.md"
    src.write_text("""\
---
name: my-researcher
description: A research specialist
model: claude-sonnet-4-20250514
permissionMode: default
mcpServers:
  filesystem: {}
memory: true
isolation: default
effort: high
color: blue
hooks:
  postToolUse: "echo done"
---

Focus on finding information.
""")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_claude_code_agent(src_path=src, dest_dir=dest_dir)

    assert report.name == "my-researcher"
    assert report.dest_path.exists()
    assert report.dest_path.suffix == ".md"

    content = report.dest_path.read_text()
    assert "name: my-researcher" in content
    assert "description: A research specialist" in content
    assert "model: claude-sonnet-4-20250514" in content
    assert "# permissionMode" in content
    assert "# mcpServers" in content
    assert "# memory" in content
    # Unsupported fields are commented out
    assert "# isolation" in content
    assert "# effort" in content
    assert "# color" in content
    assert "# hooks" in content
    # Supported fields present without comment prefix
    assert "Focus on finding information." in content


def test_import_claude_code_prompt_before_overwrite(tmp_path):
    """Prompts before overwriting existing file."""
    from aede.import_.claude_code import import_claude_code_agent

    src = tmp_path / "agent.md"
    src.write_text("""\
---
name: tester
description: Test agent
---

Body.
""")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "tester.md"
    existing.write_text("original")

    prompt_called = [False]

    def fake_input(prompt_text):
        prompt_called[0] = True
        return "y"

    report = import_claude_code_agent(
        src_path=src, dest_dir=dest_dir,
        _input_fn=fake_input,
    )

    assert prompt_called[0]
    assert report.dest_path.read_text() != "original"


def test_import_claude_code_skip_on_no_overwrite(tmp_path):
    """When user declines overwrite, original file is preserved."""
    from aede.import_.claude_code import import_claude_code_agent

    src = tmp_path / "agent.md"
    src.write_text("""\
---
name: tester
description: Test agent
---

Body.
""")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "tester.md"
    existing.write_text("original")

    def fake_input(prompt_text):
        return "n"

    report = import_claude_code_agent(
        src_path=src, dest_dir=dest_dir,
        _input_fn=fake_input,
    )

    assert report.dest_path.read_text() == "original"
    assert report.was_skipped
