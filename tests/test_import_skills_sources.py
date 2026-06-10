"""Tests for the `source` parameter on import_claude_code_skill."""
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill_dir(parent: Path, name: str, description: str, body: str = "Body text.") -> Path:
    """Create a SKILL.md directory and return the directory path."""
    skill_dir = parent / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_dir


def _make_flat_skill(parent: Path, name: str, description: str, body: str = "Body text.") -> Path:
    """Create a flat .md skill file and return its path."""
    skill_file = parent / f"{name}.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_source_antigravity_dir(tmp_path):
    """source='Antigravity' on a SKILL.md directory sets report.format correctly."""
    from aede.import_.skills import import_claude_code_skill

    src = _make_skill_dir(tmp_path, "deploy", "Deploy things.")
    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir, source="Antigravity")

    assert report.format == "Antigravity"
    assert report.name == "deploy"
    assert report.dest_path.exists()
    content = report.dest_path.read_text(encoding="utf-8")
    assert "name: deploy" in content
    assert "description:" in content
    assert "Deploy things." in content


def test_source_windsurf_flat_file(tmp_path):
    """source='Windsurf' on a flat .md skill sets report.format correctly."""
    from aede.import_.skills import import_claude_code_skill

    src = _make_flat_skill(tmp_path, "search", "Search the web.")
    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir, source="Windsurf")

    assert report.format == "Windsurf"
    assert report.name == "search"
    assert report.dest_path.exists()


def test_source_codex_unknown_frontmatter_field(tmp_path):
    """source='Codex' with an unrecognized frontmatter field: field is commented out, import succeeds."""
    from aede.import_.skills import import_claude_code_skill

    skill_dir = tmp_path / "analyse"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: analyse\n"
        "description: Analyse stuff.\n"
        "hidden: true\n"
        "unknown_future_field: some_value\n"
        "---\n\n"
        "Run the analyser.\n",
        encoding="utf-8",
    )
    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(
        src_path=skill_dir, dest_dir=dest_dir, source="Codex"
    )

    assert report.format == "Codex"
    assert not report.was_skipped
    content = report.dest_path.read_text(encoding="utf-8")
    # Both unsupported fields must be commented out, not crash
    assert "# hidden" in content
    # unknown_future_field is not in _UNSUPPORTED_FIELDS so it passes through
    assert "unknown_future_field" in content
    assert "Run the analyser." in content


def test_source_default_is_claude_code(tmp_path):
    """Calling without source= defaults to 'Claude Code' (backward compat)."""
    from aede.import_.skills import import_claude_code_skill

    src = _make_flat_skill(tmp_path, "helper", "Generic helper.")
    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()

    report = import_claude_code_skill(src_path=src, dest_dir=dest_dir)

    assert report.format == "Claude Code"


def test_source_propagates_on_skip(tmp_path):
    """source is reflected in report.format even when the import is skipped (user declines overwrite)."""
    from aede.import_.skills import import_claude_code_skill

    src = _make_flat_skill(tmp_path, "tester", "Test skill.")
    dest_dir = tmp_path / "skills"
    dest_dir.mkdir()
    # Pre-create the destination so overwrite prompt is triggered
    (dest_dir / "tester.md").write_text("original", encoding="utf-8")

    def fake_input(_prompt: str) -> str:
        return "n"

    report = import_claude_code_skill(
        src_path=src, dest_dir=dest_dir, _input_fn=fake_input, source="Antigravity"
    )

    assert report.was_skipped
    assert report.format == "Antigravity"
    # Original file must be untouched
    assert report.dest_path.read_text(encoding="utf-8") == "original"
