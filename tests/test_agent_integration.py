import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_system_prompt_contains_learnings_suffix(tmp_path):
    """build_system_prompt with learnings_suffix appends it after ## Session."""
    from aede.agent import build_system_prompt, STABLE_SYSTEM_PROMPT
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.tool_output_max_tokens = 2000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.8
    cfg.grounding_enabled = False

    learnings_suffix = "## Lessons from Prior Runs\n- Avoid bare except"
    prompt = build_system_prompt(
        cfg=cfg, session_id="SID", is_resume=False,
        session_notes=None, compaction_summary=None,
        learnings_suffix=learnings_suffix,
    )

    assert prompt.stable == STABLE_SYSTEM_PROMPT
    assert "Lessons from Prior Runs" in prompt.dynamic


@pytest.mark.asyncio
async def test_trace_written_per_turn(tmp_path):
    """TraceLogger writes are append-only JSONL."""
    from aede.trace.logger import TraceLogger

    log_dir = tmp_path / "traces"
    log_dir.mkdir()
    logger = TraceLogger(log_dir=log_dir)

    logger.write_turn_trace(
        session_id="s1", turn_number=1,
        input_tokens=10, output_tokens=5, cached_tokens=0,
        tool_calls=[], reasoning_text="", outcome="completed",
    )

    trace_file = log_dir / "s1.jsonl"
    assert trace_file.exists()
    import json
    data = json.loads(trace_file.read_text().strip())
    assert data["session_id"] == "s1"
    assert data["turn_number"] == 1
