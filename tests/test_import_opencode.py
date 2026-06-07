import pytest
from pathlib import Path


def test_import_opencode_fidelity(tmp_path):
    """OpenCode agent maps 1:1 to AGENT.md (schema identical to Claude Code)."""
    from aede.import_.opencode import import_opencode_agent

    src = tmp_path / "opencode_agent.md"
    src.write_text("""\
---
name: code-helper
description: Helps with coding
model: claude-sonnet-4-20250514
permissionMode: default
mcpServers: {}
---

Write good code.
""")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_opencode_agent(src_path=src, dest_dir=dest_dir)

    assert report.name == "code-helper"
    assert report.format == "OpenCode"
    assert report.dest_path.exists()

    content = report.dest_path.read_text()
    assert "name: code-helper" in content
    assert "description: Helps with coding" in content
    assert "model: claude-sonnet-4-20250514" in content
    assert "# permissionMode" in content
    assert "# mcpServers" in content
    assert "Write good code." in content


def test_import_opencode_prompt_before_overwrite(tmp_path):
    """Prompts before overwrite, same pattern as Claude Code import."""
    from aede.import_.opencode import import_opencode_agent

    src = tmp_path / "agent.md"
    src.write_text("""\
---
name: helper
description: Helper
---

Body.
""")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "helper.md"
    existing.write_text("original")

    prompt_called = [False]

    def fake_input(prompt_text):
        prompt_called[0] = True
        return "y"

    report = import_opencode_agent(
        src_path=src, dest_dir=dest_dir,
        _input_fn=fake_input,
    )

    assert prompt_called[0]
    assert report.dest_path.read_text() != "original"
