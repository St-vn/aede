from __future__ import annotations
from pathlib import Path
import pytest


def test_import_cursor_mdc_full_frontmatter(tmp_path):
    """Full .mdc with description, globs, alwaysApply → all mapped correctly."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "python-rules.mdc"
    src.write_text(
        "---\n"
        "description: Python best practices\n"
        "globs:\n"
        "  - '**/*.py'\n"
        "  - '**/*.pyi'\n"
        "alwaysApply: true\n"
        "---\n"
        "\n"
        "Always use type hints.\n"
        "\n"
        "Follow PEP 8.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    assert report.name == "python-rules"
    assert report.format == "Cursor"
    assert not report.was_skipped
    assert report.dest_path.exists()
    assert report.dest_path == dest_dir / "python-rules.md"

    content = report.dest_path.read_text(encoding="utf-8")

    # description should be written
    assert "description: Python best practices" in content
    # globs commented out
    assert "# globs:" in content
    # alwaysApply commented out
    assert "# alwaysApply:" in content
    # body preserved
    assert "Always use type hints." in content
    assert "Follow PEP 8." in content
    # model set to inherit
    assert "model: inherit" in content


def test_import_cursor_mdc_missing_description(tmp_path):
    """Missing description → fallback 'Imported from Cursor'."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "ts-rules.mdc"
    src.write_text(
        "---\n"
        "globs:\n"
        "  - '**/*.ts'\n"
        "alwaysApply: false\n"
        "---\n"
        "\n"
        "Use strict TypeScript.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    content = report.dest_path.read_text(encoding="utf-8")
    assert "description: Imported from Cursor" in content
    assert "Use strict TypeScript." in content


def test_import_cursor_mdc_no_frontmatter_raises(tmp_path):
    """No frontmatter (no leading ---) → ValueError naming the file."""
    import re
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "plain.mdc"
    src.write_text("Just plain markdown.\n", encoding="utf-8")

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    with pytest.raises(ValueError, match=re.escape(str(src))):
        import_cursor_mdc(src_path=src, dest_dir=dest_dir)


def test_import_cursor_mdc_overwrite_declined(tmp_path):
    """Declining overwrite → was_skipped=True, original file intact."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "rules.mdc"
    src.write_text(
        "---\n"
        "description: Some rules\n"
        "---\n"
        "\n"
        "New body.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "rules.md"
    existing.write_text("original", encoding="utf-8")

    report = import_cursor_mdc(
        src_path=src,
        dest_dir=dest_dir,
        _input_fn=lambda prompt: "n",
    )

    assert report.was_skipped
    assert existing.read_text(encoding="utf-8") == "original"


def test_import_cursor_mdc_overwrite_accepted(tmp_path):
    """Accepting overwrite replaces existing file."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "rules.mdc"
    src.write_text(
        "---\n"
        "description: Updated rules\n"
        "---\n"
        "\n"
        "Updated body.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()
    existing = dest_dir / "rules.md"
    existing.write_text("original", encoding="utf-8")

    report = import_cursor_mdc(
        src_path=src,
        dest_dir=dest_dir,
        _input_fn=lambda prompt: "y",
    )

    assert not report.was_skipped
    content = existing.read_text(encoding="utf-8")
    assert "Updated rules" in content
    assert "Updated body." in content


def test_import_cursor_mdc_name_from_stem(tmp_path):
    """Name is slugified from the .mdc file stem."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "react-component-style.mdc"
    src.write_text(
        "---\n"
        "description: React style guide\n"
        "---\n"
        "\n"
        "Use functional components.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    assert report.name == "react-component-style"
    assert report.dest_path == dest_dir / "react-component-style.md"


def test_import_cursor_mdc_body_preserved_exactly(tmp_path):
    """Body (after closing ---) is preserved 1:1 in the output."""
    from aede.import_.cursor import import_cursor_mdc

    body = "Line one.\n\nLine two.\n\n- bullet\n- another\n"
    src = tmp_path / "detail.mdc"
    src.write_text(
        "---\n"
        "description: Detailed rules\n"
        "alwaysApply: false\n"
        "---\n"
        "\n" + body,
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    content = report.dest_path.read_text(encoding="utf-8")
    assert body.strip() in content


def test_import_cursor_mdc_unsupported_fields_commented(tmp_path):
    """globs and alwaysApply appear as YAML comment lines in frontmatter."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "rules.mdc"
    src.write_text(
        "---\n"
        "description: Test\n"
        "globs: ['**/*.js']\n"
        "alwaysApply: false\n"
        "---\n"
        "\n"
        "Body.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    content = report.dest_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    # Find lines that are commented out
    commented = [l for l in lines if l.startswith("# ")]
    assert any("globs" in l for l in commented)
    assert any("alwaysApply" in l for l in commented)


def test_import_cursor_mdc_format_is_cursor(tmp_path):
    """report.format is always 'Cursor'."""
    from aede.import_.cursor import import_cursor_mdc

    src = tmp_path / "any.mdc"
    src.write_text(
        "---\n"
        "description: Any\n"
        "---\n"
        "\n"
        "Content.\n",
        encoding="utf-8",
    )

    dest_dir = tmp_path / "agents"
    dest_dir.mkdir()

    report = import_cursor_mdc(src_path=src, dest_dir=dest_dir)

    assert report.format == "Cursor"
