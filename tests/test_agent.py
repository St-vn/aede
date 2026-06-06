import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aede.agent import build_system_prompt, count_context_tokens


def test_build_system_prompt_stable_prefix():
    from aede.config import AedeConfig
    from pathlib import Path
    cfg = AedeConfig({
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
    assert "aede" in prompt
    assert "powershell" in prompt
    assert "read_file" in prompt
    assert "research" in prompt.lower()
    assert "web_search" in prompt
    assert "SID001" in prompt
    assert "claude-sonnet-4-20250514" in prompt


def test_build_system_prompt_no_timestamps_in_stable():
    """Stable prefix must never change between sessions — no dynamic content."""
    from aede.config import AedeConfig
    from pathlib import Path
    import time
    cfg = AedeConfig({
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
    from aede.config import AedeConfig
    from pathlib import Path
    cfg = AedeConfig({
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


@pytest.mark.asyncio
async def test_compaction_fallback_uses_anthropic_model_not_gemini():
    """On a non-Anthropic provider, compaction must NOT pass the active
    (e.g. Gemini) model id to the Anthropic compaction client — that id
    would 404 against api.anthropic.com. It must substitute an Anthropic id."""
    from aede.agent import AgentLoop
    from aede.config import AedeConfig, DEFAULT_CONFIG
    from aede.provider import OpenAIProvider
    from pathlib import Path

    cfg = AedeConfig({
        "model": "google/gemini-2.5-flash",
        "shell": "powershell",
        "tool_output_max_tokens": 8000,
        "context_window": 100,           # tiny window so compaction triggers
        "compaction_threshold": 0.01,
        "api_base_url": "https://openrouter.ai/api/v1",
    }, home=Path("/tmp"))

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._console = MagicMock()
    loop._session = MagicMock(id="SID")
    loop._rollout = MagicMock()
    loop._messages = [{"role": "user", "content": "x" * 4000}]

    # Active provider is OpenAI (Gemini) — but a bare Anthropic client exists for compaction.
    loop._get_provider = MagicMock(return_value=OpenAIProvider(api_key="k", base_url="u"))

    captured = {}

    async def fake_run_compaction(**kwargs):
        captured.update(kwargs)
        return {"method": "none"}

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ak"}), \
         patch("anthropic.AsyncAnthropic", MagicMock()), \
         patch("aede.compaction.run_compaction", side_effect=fake_run_compaction):
        await loop._maybe_compact()

    assert captured, "run_compaction was not called"
    assert captured["model"].startswith("claude-"), \
        f"compaction sent non-Anthropic model id: {captured['model']!r}"
    assert captured["model"] == DEFAULT_CONFIG["model"]


def test_count_context_tokens_empty():
    assert count_context_tokens([]) == 0


def test_count_context_tokens_sums_content():
    messages = [
        {"role": "user", "content": "a" * 400},
        {"role": "assistant", "content": "b" * 400},
    ]
    total = count_context_tokens(messages)
    assert total == pytest.approx(200, abs=20)
