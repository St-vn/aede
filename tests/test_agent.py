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


@pytest.mark.asyncio
async def test_compact_forced_runs_below_threshold():
    """agent.compact() must invoke run_compaction even when under threshold."""
    from aede.agent import AgentLoop
    from aede.config import AedeConfig
    from pathlib import Path

    cfg = AedeConfig(
        {
            "model": "claude-sonnet-4-20250514",
            "shell": "powershell",
            "tool_output_max_tokens": 8000,
            "context_window": 200000,
            "compaction_threshold": 0.85,  # high threshold — won't trigger normally
        },
        home=Path("/tmp"),
    )

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = MagicMock(id="SID")
    loop._rollout = MagicMock()
    loop._console = MagicMock()
    loop._messages = [{"role": "user", "content": "hello"}]  # tiny, well under threshold
    loop._provider = MagicMock()

    fake_result = {
        "method": "string_pass_only",
        "messages": loop._messages,
        "messages_compacted": 1,
        "summary": "",
        "tokens_reclaimed": 0,
    }

    from aede.provider import AnthropicProvider
    mock_provider = MagicMock(spec=AnthropicProvider)
    mock_provider.raw_client = MagicMock()
    loop._get_provider = MagicMock(return_value=mock_provider)

    with patch("aede.compaction.run_compaction", new_callable=AsyncMock, return_value=fake_result) as mock_compact:
        result = await loop.compact()

    mock_compact.assert_called_once()
    assert result["method"] == "string_pass_only"


@pytest.mark.asyncio
async def test_maybe_compact_not_called_below_threshold():
    """_maybe_compact() must NOT call run_compaction when under threshold."""
    from aede.agent import AgentLoop
    from aede.config import AedeConfig
    from pathlib import Path

    cfg = AedeConfig(
        {
            "model": "claude-sonnet-4-20250514",
            "shell": "powershell",
            "tool_output_max_tokens": 8000,
            "context_window": 200000,
            "compaction_threshold": 0.85,
        },
        home=Path("/tmp"),
    )

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = MagicMock(id="SID")
    loop._rollout = MagicMock()
    loop._console = MagicMock()
    loop._messages = [{"role": "user", "content": "hello"}]  # tiny
    loop._provider = MagicMock()

    with patch("aede.compaction.run_compaction", new_callable=AsyncMock) as mock_compact:
        await loop._maybe_compact()

    mock_compact.assert_not_called()


def _make_agent_loop_for_gate_test(batch_approval_max: int) -> "AgentLoop":
    """Build a minimal AgentLoop suitable for gate/batch tests.

    The loop has no real provider, router, or DB.  Callers are expected to
    monkeypatch ``_stream_response``, ``_router``, and ``_gate_store`` as needed.
    """
    from aede.agent import AgentLoop
    from aede.config import AedeConfig
    from pathlib import Path

    cfg = AedeConfig(
        {
            "model": "claude-sonnet-4-20250514",
            "shell": "powershell",
            "tool_output_max_tokens": 8000,
            "context_window": 200000,
            "compaction_threshold": 0.85,
            "batch_approval_max": batch_approval_max,
        },
        home=Path("/tmp"),
    )

    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = MagicMock(id="SID")
    loop._db = MagicMock()
    loop._rollout = MagicMock()
    loop._console = MagicMock()
    loop._project_dir = Path("/tmp")
    loop._messages = []
    loop._turn = 0
    loop._provider = MagicMock()
    loop._system_prompt = ""
    loop._tracker = MagicMock()
    loop._tracker.record = MagicMock()
    return loop


def _make_tool_result():
    """Return a minimal ToolResult-like object for mocked router execution."""
    result = MagicMock()
    result.status = "ok"
    result.output = "done"
    result.duration_ms = 1
    return result


def _make_response(tool_calls: list[dict]) -> MagicMock:
    """Return a NormalizedResponse-like mock with the given tool calls."""
    resp = MagicMock()
    resp.text = ""
    resp.tool_calls = tool_calls
    resp.assistant_content_blocks = []
    resp.input_tokens = 10
    resp.output_tokens = 5
    resp.cached_tokens = 0
    return resp


@pytest.mark.asyncio
async def test_batch_approve_over_cap_prompts_per_tool():
    """When BATCH_APPROVE fires but len(tool_calls) > batch_approval_max,
    the gate must be consulted for EVERY tool — no blanket skip."""
    from aede.gate import GateDecision

    loop = _make_agent_loop_for_gate_test(batch_approval_max=2)

    # 3 tool calls; cap is 2  →  batch approve must NOT skip remaining calls
    tool_calls = [
        {"id": f"tc{i}", "name": "read_file", "input": {"path": f"/f{i}"}}
        for i in range(3)
    ]

    # First provider call returns 3 tool calls; second returns nothing (stop).
    resp_tools = _make_response(tool_calls)
    resp_done = _make_response([])
    resp_done.text = "done"
    call_count = {"n": 0}

    async def fake_stream(*a, **kw):
        call_count["n"] += 1
        return resp_tools if call_count["n"] == 1 else resp_done

    loop._stream_response = fake_stream

    # Gate always returns BATCH_APPROVE
    gate_calls: list[str] = []

    def fake_prompt_gate(tool_name, **kwargs):
        gate_calls.append(tool_name)
        return GateDecision.BATCH_APPROVE, ""

    # Router: read_file requires no approval (not in GATE_TOOLS), so we
    # must make it require approval to exercise the gate path.
    router = MagicMock()
    router.validate_name = MagicMock()
    router.requires_approval = MagicMock(return_value=True)
    router.execute_sync = MagicMock(return_value=_make_tool_result())
    loop._router = router

    gate_store = MagicMock()
    gate_store.is_allowed = MagicMock(return_value=False)  # always needs gate
    loop._gate_store = gate_store

    # Compact is a no-op for this test
    async def no_compact():
        pass
    loop._maybe_compact = no_compact

    with patch("aede.gate.prompt_gate", side_effect=fake_prompt_gate):
        await loop.run_turn("do it")

    # Gate must have been called for all 3 tools (cap=2, batch=3 → over cap)
    assert len(gate_calls) == 3, (
        f"Expected gate called 3 times (once per tool), got {len(gate_calls)}: {gate_calls}"
    )


@pytest.mark.asyncio
async def test_batch_approve_within_cap_skips_remaining():
    """When BATCH_APPROVE fires and len(tool_calls) <= batch_approval_max,
    the remaining tool calls in the same assistant message skip the gate."""
    from aede.gate import GateDecision

    loop = _make_agent_loop_for_gate_test(batch_approval_max=5)

    # 3 tool calls; cap is 5  →  batch approve skips calls 2 and 3
    tool_calls = [
        {"id": f"tc{i}", "name": "read_file", "input": {"path": f"/f{i}"}}
        for i in range(3)
    ]

    resp_tools = _make_response(tool_calls)
    resp_done = _make_response([])
    resp_done.text = "done"
    call_count = {"n": 0}

    async def fake_stream(*a, **kw):
        call_count["n"] += 1
        return resp_tools if call_count["n"] == 1 else resp_done

    loop._stream_response = fake_stream

    gate_calls: list[str] = []

    def fake_prompt_gate(tool_name, **kwargs):
        gate_calls.append(tool_name)
        return GateDecision.BATCH_APPROVE, ""

    router = MagicMock()
    router.validate_name = MagicMock()
    router.requires_approval = MagicMock(return_value=True)
    router.execute_sync = MagicMock(return_value=_make_tool_result())
    loop._router = router

    gate_store = MagicMock()
    gate_store.is_allowed = MagicMock(return_value=False)
    loop._gate_store = gate_store

    async def no_compact():
        pass
    loop._maybe_compact = no_compact

    with patch("aede.gate.prompt_gate", side_effect=fake_prompt_gate):
        await loop.run_turn("do it")

    # Gate should only be called ONCE (for the first tool); remaining skip
    assert len(gate_calls) == 1, (
        f"Expected gate called once (batch approved remaining), got {len(gate_calls)}: {gate_calls}"
    )
