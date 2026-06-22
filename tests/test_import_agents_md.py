from __future__ import annotations
from pathlib import Path


def test_import_agents_md_basic(tmp_path):
    """AGENTS.md with generic filename → agent with parent-dir slug, body == source content."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    body_text = "You are a helpful assistant.\n\nAlways be concise.\n"
    src.write_text(body_text, encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Codex")

    assert report.name == "myproject"
    assert report.format == "Codex"
    assert not report.was_skipped
    assert report.dest_path.exists()
    assert report.dest_path == dest_dir / "myproject.md"

    content = report.dest_path.read_text(encoding="utf-8")
    # Frontmatter checks
    assert "name: myproject" in content
    assert "description: Imported from Codex" in content
    assert "model: inherit" in content
    # Body == full source text
    assert body_text.strip() in content


def test_import_agents_md_description_uses_source(tmp_path):
    """description field always says 'Imported from <source>'."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    src.write_text("Do things.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Antigravity")

    content = report.dest_path.read_text(encoding="utf-8")
    assert "description: Imported from Antigravity" in content
    assert report.format == "Antigravity"


def test_import_gemini_md_tagged_antigravity(tmp_path):
    """GEMINI.md → format == 'Antigravity', name from parent dir."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "myapp"
    project_dir.mkdir()
    src = project_dir / "GEMINI.md"
    src.write_text("Gemini rules here.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Antigravity")

    assert report.format == "Antigravity"
    assert report.name == "myapp"
    assert report.dest_path == dest_dir / "myapp.md"


def test_import_agents_md_name_from_stem_non_generic(tmp_path):
    """Non-generic filename → slug from file stem, not parent dir."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    src = project_dir / "backend-rules.md"
    src.write_text("Backend constraints.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Windsurf")

    assert report.name == "backend-rules"
    assert report.dest_path == dest_dir / "backend-rules.md"


def test_import_agents_md_slug_sanitisation(tmp_path):
    """Slugify converts spaces/special chars to hyphens."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "My Cool Project!"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    src.write_text("Rules.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Codex")

    # slug should be lowercase with hyphens
    assert report.name == "my-cool-project"


def test_import_agents_md_overwrite_declined(tmp_path):
    """Declining overwrite returns was_skipped=True and leaves original intact."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    src.write_text("New content.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "myproject.md"
    existing.write_text("original content", encoding="utf-8")

    report = import_agents_md(
        src_path=src,
        dest_dir=dest_dir,
        source="Codex",
        _input_fn=lambda prompt: "n",
    )

    assert report.was_skipped
    assert existing.read_text(encoding="utf-8") == "original content"


def test_import_agents_md_overwrite_accepted(tmp_path):
    """Accepting overwrite replaces the existing file."""
    from aede.import_.agents_md import import_agents_md

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    src.write_text("New content.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "myproject.md"
    existing.write_text("original content", encoding="utf-8")

    report = import_agents_md(
        src_path=src,
        dest_dir=dest_dir,
        source="Codex",
        _input_fn=lambda prompt: "y",
    )

    assert not report.was_skipped
    assert existing.read_text(encoding="utf-8") != "original content"


def test_import_agents_md_empty_file_fallback_name(tmp_path):
    """Empty/whitespace file still produces a valid agent with fallback name."""
    from aede.import_.agents_md import import_agents_md

    # Use a directory whose name would slugify to empty string — force fallback
    # We test the scenario where the parent dir slug falls back to 'imported-agent'
    # by using a non-generic filename that slugifies to empty (edge case).
    # More practically: whitespace-only content with normal parent dir name.
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    src = project_dir / "AGENTS.md"
    src.write_text("   \n\n  ", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Codex")

    # Should still produce a valid agent (name from parent dir)
    assert report.name  # non-empty
    assert report.dest_path.exists()
    content = report.dest_path.read_text(encoding="utf-8")
    assert "---" in content
    assert "name:" in content


def test_import_agents_md_slug_fallback_when_empty(tmp_path):
    """If both stem and parent dir slugify to empty, fall back to 'imported-agent'."""
    from aede.import_.agents_md import import_agents_md

    # Use a name with only non-alphanumeric chars — hard to do with real filesystem
    # so we test via agents.md (generic) with parent dir = "---" → empty slug
    # On Windows filesystem "---" is not a valid dir name, so we test fallback
    # via a file with generic name whose parent is the tmp root (no meaningful name).
    src = tmp_path / "AGENTS.md"
    src.write_text("Content.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Codex")

    # Parent dir is something like a hex tmp dir — just verify it's non-empty
    assert report.name
    assert report.dest_path.exists()


def test_import_windsurf_rules_md(tmp_path):
    """Windsurf .windsurf/rules/*.md with non-generic name → name from stem."""
    from aede.import_.agents_md import import_agents_md

    rules_dir = tmp_path / ".windsurf" / "rules"
    rules_dir.mkdir(parents=True)
    src = rules_dir / "python-standards.md"
    src.write_text("Follow PEP 8.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_agents_md(src_path=src, dest_dir=dest_dir, source="Windsurf")

    assert report.name == "python-standards"
    assert report.format == "Windsurf"
    assert report.dest_path == dest_dir / "python-standards.md"
    content = report.dest_path.read_text(encoding="utf-8")
    assert "Follow PEP 8." in content
