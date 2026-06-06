"""
Tests for SystemPrompt dataclass and build_system_prompt stable/dynamic split.
RED tests for cache_control bug fix (phase2-tasks-bug-cache-control.md, Tasks 1-4).
"""
from __future__ import annotations

from pathlib import Path
import pytest

from aede.config import AedeConfig


def _make_cfg(**overrides) -> AedeConfig:
    defaults = {
        "model": "claude-sonnet-4-20250514",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 200000,
        "compaction_threshold": 0.85,
    }
    defaults.update(overrides)
    return AedeConfig(defaults, home=Path("/tmp"))


# ---------------------------------------------------------------------------
# Task 1 — build_system_prompt returns SystemPrompt dataclass
# ---------------------------------------------------------------------------

def test_returns_stable_and_dynamic():
    """build_system_prompt must return a SystemPrompt with .stable and .dynamic."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT, SystemPrompt

    cfg = _make_cfg()
    result = build_system_prompt(
        cfg=cfg,
        session_id="SID001",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
    )

    assert isinstance(result, SystemPrompt), (
        f"Expected SystemPrompt, got {type(result)}"
    )
    # Stable part must be exactly STABLE_SYSTEM_PROMPT (no dynamic content)
    assert result.stable == STABLE_SYSTEM_PROMPT
    # Dynamic part must contain configuration section
    assert "## Configuration" in result.dynamic
    assert "SID001" in result.dynamic


def test_system_prompt_stable_is_immutable_across_sessions():
    """Stable part must not change between different sessions/configs."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT

    cfg1 = _make_cfg(model="claude-sonnet-4-20250514")
    cfg2 = _make_cfg(model="claude-opus-4-20250514")

    sp1 = build_system_prompt(cfg=cfg1, session_id="A", is_resume=False, session_notes=None, compaction_summary=None)
    sp2 = build_system_prompt(cfg=cfg2, session_id="B", is_resume=True, session_notes="note", compaction_summary="sum")

    assert sp1.stable == sp2.stable == STABLE_SYSTEM_PROMPT


def test_system_prompt_dynamic_contains_model():
    """Dynamic part contains model and session config."""
    from aede.agent import build_system_prompt

    cfg = _make_cfg(model="claude-opus-4-20250514")
    sp = build_system_prompt(cfg=cfg, session_id="SID999", is_resume=False, session_notes=None, compaction_summary=None)
    assert "claude-opus-4-20250514" in sp.dynamic
    assert "SID999" in sp.dynamic


def test_system_prompt_resume_notes_in_dynamic():
    """Session notes and compaction summaries appear in dynamic part."""
    from aede.agent import build_system_prompt

    cfg = _make_cfg()
    sp = build_system_prompt(
        cfg=cfg,
        session_id="SID-R",
        is_resume=True,
        session_notes="use pathlib always",
        compaction_summary="fixed the bug",
    )
    assert "use pathlib always" in sp.dynamic
    assert "fixed the bug" in sp.dynamic
    # Stable must not contain notes
    assert "use pathlib always" not in sp.stable


# ---------------------------------------------------------------------------
# Task 3 — initialize stores SystemPrompt dataclass
# ---------------------------------------------------------------------------

def test_initialize_stores_system_prompt_dataclass():
    """AgentLoop.initialize must store a SystemPrompt dataclass, not a str."""
    from aede.agent import AgentLoop, SystemPrompt
    from unittest.mock import MagicMock

    cfg = _make_cfg()
    session = MagicMock()
    session.id = "sess-init-test"

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = session
    loop._db = MagicMock()
    loop._rollout = MagicMock()
    loop._router = MagicMock()
    loop._gate_store = MagicMock()
    loop._tracker = MagicMock()
    loop._console = MagicMock()
    loop._project_dir = Path("/tmp")
    loop._messages = []
    loop._turn = 0
    loop._provider = None
    loop._system_prompt = None  # type: ignore[assignment]

    loop.initialize(is_resume=False, session_notes=None, compaction_summary=None)

    assert isinstance(loop._system_prompt, SystemPrompt), (
        f"Expected SystemPrompt after initialize, got {type(loop._system_prompt)}"
    )
