import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jarvis.agent import build_system_prompt, count_context_tokens


def test_build_system_prompt_stable_prefix():
    from jarvis.config import JarvisConfig
    from pathlib import Path
    cfg = JarvisConfig({
        "model": "claude-sonnet-4-20250514",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 200000,
        "compaction_threshold": 0.85,
    }, home=Path("/tmp"))
    prompt = build_system_prompt(
        cfg=cfg,
        session_id="SID001",
        is_resume=False,
        session_notes=None,
        compaction_summary=None,
    )
    assert "Jarvis" in prompt
    assert "powershell" in prompt
    assert "read_file" in prompt
    assert "research" in prompt.lower()
    assert "web_search" in prompt
    assert "SID001" in prompt
    assert "claude-sonnet-4-20250514" in prompt


def test_build_system_prompt_no_timestamps_in_stable():
    """Stable prefix must never change between sessions — no dynamic content."""
    from jarvis.config import JarvisConfig
    from pathlib import Path
    import time
    cfg = JarvisConfig({
        "model": "claude-sonnet-4-20250514",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 200000,
        "compaction_threshold": 0.85,
    }, home=Path("/tmp"))
    p1 = build_system_prompt(cfg=cfg, session_id="A", is_resume=False, session_notes=None, compaction_summary=None)
    time.sleep(0.01)
    p2 = build_system_prompt(cfg=cfg, session_id="A", is_resume=False, session_notes=None, compaction_summary=None)
    stable1 = p1.split("## Configuration")[0]
    stable2 = p2.split("## Configuration")[0]
    assert stable1 == stable2


def test_build_system_prompt_resume_includes_notes():
    from jarvis.config import JarvisConfig
    from pathlib import Path
    cfg = JarvisConfig({
        "model": "claude-sonnet-4-20250514",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 200000,
        "compaction_threshold": 0.85,
    }, home=Path("/tmp"))
    prompt = build_system_prompt(
        cfg=cfg,
        session_id="SID002",
        is_resume=True,
        session_notes="remember: use pathlib",
        compaction_summary="## Session Handoff Summary\nGoal: fix the bug",
    )
    assert "remember: use pathlib" in prompt
    assert "fix the bug" in prompt


def test_count_context_tokens_empty():
    assert count_context_tokens([]) == 0


def test_count_context_tokens_sums_content():
    messages = [
        {"role": "user", "content": "a" * 400},
        {"role": "assistant", "content": "b" * 400},
    ]
    total = count_context_tokens(messages)
    assert total == pytest.approx(200, abs=20)
