"""
Tests for the three-tier instruction discovery system (SOUL.md, AGENTS.md, CLAUDE.md).
"""
from __future__ import annotations

from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# SOUL.md
# ---------------------------------------------------------------------------

def test_load_soul_returns_none_when_missing(tmp_home):
    """No SOUL.md → None (not empty string)."""
    from aede.instructions import load_soul
    assert load_soul(tmp_home) is None


def test_load_soul_returns_content(tmp_home):
    """SOUL.md exists with content → returns stripped content."""
    from aede.instructions import load_soul
    tmp_home.mkdir(parents=True, exist_ok=True)
    (tmp_home / "SOUL.md").write_text("  You are a helpful assistant.  \n")
    assert load_soul(tmp_home) == "You are a helpful assistant."


def test_load_soul_returns_none_for_empty_file(tmp_home):
    """SOUL.md exists but is empty → None."""
    from aede.instructions import load_soul
    tmp_home.mkdir(parents=True, exist_ok=True)
    (tmp_home / "SOUL.md").write_text("   \n\n  ")
    assert load_soul(tmp_home) is None


# ---------------------------------------------------------------------------
# Global AGENTS.md
# ---------------------------------------------------------------------------

def test_load_global_instructions_none_when_missing(tmp_home):
    """No global AGENTS.md → None."""
    from aede.instructions import load_global_instructions
    assert load_global_instructions(tmp_home) is None


def test_load_global_instructions_returns_content(tmp_home):
    """Global AGENTS.md exists → returns content."""
    from aede.instructions import load_global_instructions
    tmp_home.mkdir(parents=True, exist_ok=True)
    (tmp_home / "AGENTS.md").write_text("Use pathlib for all paths.")
    assert load_global_instructions(tmp_home) == "Use pathlib for all paths."


# ---------------------------------------------------------------------------
# Git root detection
# ---------------------------------------------------------------------------

def test_find_git_root_none(tmp_path):
    """No .git anywhere → None."""
    from aede.instructions import _find_git_root
    assert _find_git_root(tmp_path) is None


def test_find_git_root_found(tmp_path):
    """.git in an ancestor → returns that ancestor."""
    from aede.instructions import _find_git_root
    git_root = tmp_path / "repo"
    (git_root / ".git").mkdir(parents=True)
    subdir = git_root / "src" / "lib"
    subdir.mkdir(parents=True)
    assert _find_git_root(subdir) == git_root


def test_find_git_root_returns_self(tmp_path):
    """.git in the directory itself → returns it."""
    from aede.instructions import _find_git_root
    (tmp_path / ".git").mkdir()
    assert _find_git_root(tmp_path) == tmp_path


# ---------------------------------------------------------------------------
# Project instructions discovery
# ---------------------------------------------------------------------------

def test_discover_empty_when_no_files(tmp_path):
    """No AGENTS.md or CLAUDE.md → empty list."""
    from aede.instructions import discover_project_instructions
    (tmp_path / ".git").mkdir()
    assert discover_project_instructions(tmp_path) == []


def test_discover_single_agents_md(tmp_path):
    """AGENTS.md in project_dir → found."""
    from aede.instructions import discover_project_instructions
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("build: uv run pytest")
    result = discover_project_instructions(tmp_path)
    assert len(result) == 1
    assert result[0][0].name == "AGENTS.md"
    assert "build: uv run pytest" in result[0][1]


def test_discover_falls_back_to_claude_md(tmp_path):
    """No AGENTS.md, but CLAUDE.md exists → uses CLAUDE.md."""
    from aede.instructions import discover_project_instructions
    (tmp_path / ".git").mkdir()
    (tmp_path / "CLAUDE.md").write_text("# Project rules")
    result = discover_project_instructions(tmp_path)
    assert len(result) == 1
    assert result[0][0].name == "CLAUDE.md"


def test_discover_prefers_agents_md_over_claude_md(tmp_path):
    """AGENTS.md takes priority when both exist in the same directory."""
    from aede.instructions import discover_project_instructions
    (tmp_path / ".git").mkdir()
    (tmp_path / "CLAUDE.md").write_text("# Claude rules")
    (tmp_path / "AGENTS.md").write_text("# Agent rules")
    result = discover_project_instructions(tmp_path)
    assert len(result) == 1
    assert result[0][0].name == "AGENTS.md"


def test_discover_walks_git_root_to_cwd(tmp_path):
    """Walks from git root to CWD, collecting files in order."""
    from aede.instructions import discover_project_instructions
    git_root = tmp_path / "repo"
    (git_root / ".git").mkdir(parents=True)
    subdir = git_root / "src" / "lib"
    subdir.mkdir(parents=True)

    (git_root / "AGENTS.md").write_text("# Root rules")
    (subdir / "AGENTS.md").write_text("# Lib rules")

    result = discover_project_instructions(subdir)
    assert len(result) == 2
    assert result[0][0].parent == git_root
    assert result[1][0].parent == subdir


def test_discover_no_git_root_checks_project_dir(tmp_path):
    """No .git found → still checks the project directory itself."""
    from aede.instructions import discover_project_instructions
    (tmp_path / "AGENTS.md").write_text("fallback")
    result = discover_project_instructions(tmp_path)
    assert len(result) == 1
    assert result[0][0].parent == tmp_path


def test_discover_skips_empty_files(tmp_path):
    """Empty instruction files are omitted from results."""
    from aede.instructions import discover_project_instructions
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("   \n\n  ")
    assert discover_project_instructions(tmp_path) == []


# ---------------------------------------------------------------------------
# build_instructions_suffix — full assembly
# ---------------------------------------------------------------------------

def test_build_instructions_suffix_empty(tmp_home, tmp_path):
    """No files at all → None."""
    from aede.instructions import build_instructions_suffix
    assert build_instructions_suffix(home=tmp_home, project_dir=tmp_path) is None


def test_build_instructions_suffix_soul_only(tmp_home, tmp_path):
    """Only SOUL.md → returns identity block."""
    from aede.instructions import build_instructions_suffix
    tmp_home.mkdir(parents=True, exist_ok=True)
    (tmp_home / "SOUL.md").write_text("Be concise.")
    result = build_instructions_suffix(home=tmp_home, project_dir=tmp_path)
    assert result is not None
    assert "## Identity" in result
    assert "Be concise." in result


def test_build_instructions_suffix_all_tiers(tmp_home, tmp_path):
    """All three tiers appear in correct order."""
    from aede.instructions import build_instructions_suffix
    tmp_home.mkdir(parents=True, exist_ok=True)
    (tmp_home / "SOUL.md").write_text("Tone: professional")
    (tmp_home / "AGENTS.md").write_text("Global: always use pathlib")
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("Project: run pytest")

    result = build_instructions_suffix(home=tmp_home, project_dir=tmp_path)
    assert result is not None
    assert result.index("## Identity") < result.index("## Global Instructions")
    assert result.index("## Global Instructions") < result.index("## Project Instructions")


def test_build_instructions_suffix_project_label(tmp_path):
    """Project instruction block includes the parent dir name as label."""
    from aede.instructions import build_instructions_suffix
    from pathlib import Path
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("rules")
    result = build_instructions_suffix(home=home, project_dir=tmp_path)
    assert result is not None
    assert tmp_path.name in result


# ---------------------------------------------------------------------------
# Integration: instructions appear in system prompt dynamic part
# ---------------------------------------------------------------------------

def test_instructions_appear_in_system_prompt_dynamic(tmp_home):
    """instructions_suffix passed to build_system_prompt appears in .dynamic."""
    from aede.agent import build_system_prompt
    from aede.config import AedeConfig

    cfg = AedeConfig({
        "model": "claude-sonnet-4-20250514",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 200000,
        "compaction_threshold": 0.85,
    }, home=tmp_home)

    sp = build_system_prompt(
        cfg=cfg,
        session_id="SID",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
        instructions_suffix="## Identity\nBe concise.",
    )
    assert "## Identity" in sp.dynamic
    assert "Be concise." in sp.dynamic
    assert "## Identity" not in sp.stable
