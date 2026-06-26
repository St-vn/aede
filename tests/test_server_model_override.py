# tests/test_server_model_override.py
"""
TDD tests for #24 W1 — shared cfg.model mutation race.

RED phase: these tests fail before fix because:
  - AgentLoop.__init__ does not accept model_override param
  - shared cfg.model IS mutated in the current code
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


def _make_cfg(model: str = "claude-3-5-sonnet-20241022"):
    """Return a minimal config-like object."""
    cfg = MagicMock()
    cfg.model = model
    cfg.reasoning_effort = None
    cfg.thinking_budget = 0
    cfg.compaction_model = None
    cfg.context_window = 200_000
    cfg.compaction_threshold = 0.85
    cfg.auto_approve = []
    cfg.shell = "bash"
    cfg.wsl_distro = None
    cfg.tool_output_max_tokens = 8000
    cfg.gate_mode = "normal"
    cfg.data_dir = Path("/tmp/aede-test")
    cfg.home = Path("/tmp/aede-test")
    return cfg


def _make_session(model: str = "claude-3-5-sonnet-20241022"):
    session = MagicMock()
    session.id = "test-session-id"
    session.model = model
    session.gate_mode = None
    session.project_dir = None
    session.title = "Test"
    return session


def _make_agent_loop(cfg, model_override=None):
    """Construct an AgentLoop with the given cfg and optional model_override."""
    from aede.agent import AgentLoop

    db = MagicMock()
    db.abort_running_tool_calls.return_value = 0
    rollout = MagicMock()
    router = MagicMock()
    router.anthropic_tool_schemas.return_value = []
    gate_store = MagicMock()
    gate_store.mode = MagicMock()
    tracker = MagicMock()
    console = MagicMock()

    kwargs = dict(
        cfg=cfg,
        session=_make_session(),
        db=db,
        rollout=rollout,
        router=router,
        gate_store=gate_store,
        tracker=tracker,
        console=console,
        project_dir=Path("/tmp"),
    )
    if model_override is not None:
        kwargs["model_override"] = model_override
    return AgentLoop(**kwargs)


# ── Unit tests ────────────────────────────────────────────────────────────────


def test_agent_loop_accepts_model_override_param():
    """AgentLoop must accept model_override kwarg without raising."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent = _make_agent_loop(cfg, model_override="claude-3-opus-20240229")
    # If we got here the param is accepted
    assert agent is not None


def test_agent_loop_stores_model_override():
    """AgentLoop must store model_override as _model_override attribute."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent = _make_agent_loop(cfg, model_override="claude-3-opus-20240229")
    assert agent._model_override == "claude-3-opus-20240229"


def test_agent_loop_active_model_uses_override():
    """_active_model property/helper must return model_override when set."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent = _make_agent_loop(cfg, model_override="claude-3-opus-20240229")
    # The active model for LLM calls must be the override
    active = agent._model_override or agent._cfg.model
    assert active == "claude-3-opus-20240229"


def test_agent_loop_active_model_falls_back_to_cfg():
    """Without override, active model must be cfg.model."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent = _make_agent_loop(cfg, model_override=None)
    active = agent._model_override or agent._cfg.model
    assert active == "claude-3-5-sonnet-20241022"


def test_shared_cfg_model_unchanged_after_override():
    """Constructing a loop with a model_override must NOT mutate shared cfg.model."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    original = cfg.model
    _make_agent_loop(cfg, model_override="claude-3-opus-20240229")
    assert cfg.model == original, (
        f"cfg.model was mutated: expected {original!r}, got {cfg.model!r}"
    )


def test_two_loops_with_different_overrides_are_independent():
    """Two concurrent loops must each use their own model override."""
    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent_a = _make_agent_loop(cfg, model_override="claude-3-opus-20240229")
    agent_b = _make_agent_loop(cfg, model_override="claude-3-haiku-20240307")

    model_a = agent_a._model_override or agent_a._cfg.model
    model_b = agent_b._model_override or agent_b._cfg.model
    assert model_a == "claude-3-opus-20240229"
    assert model_b == "claude-3-haiku-20240307"
    # And shared cfg still untouched
    assert cfg.model == "claude-3-5-sonnet-20241022"


def test_stream_turn_receives_model_override():
    """stream_turn must be called with model_override, not cfg.model."""
    import asyncio

    cfg = _make_cfg("claude-3-5-sonnet-20241022")
    agent = _make_agent_loop(cfg, model_override="claude-3-opus-20240229")

    mock_provider = AsyncMock()
    # stream_turn returns a dict-like result; keep it simple
    mock_provider.stream_turn = AsyncMock(return_value=MagicMock(
        content=[],
        stop_reason="end_turn",
        usage=MagicMock(input_tokens=10, output_tokens=5),
    ))
    mock_provider.has_vision = MagicMock(return_value=False)
    agent._provider = mock_provider

    # Call the internal method that invokes stream_turn
    async def _run():
        try:
            await agent._call_provider(mock_provider)
        except Exception:
            pass  # Only care about the call args

    asyncio.run(_run())

    if mock_provider.stream_turn.called:
        call_kwargs = mock_provider.stream_turn.call_args
        # model kwarg must be the override, not cfg.model
        model_arg = call_kwargs.kwargs.get("model") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert model_arg == "claude-3-opus-20240229", (
            f"stream_turn called with model={model_arg!r}, expected override"
        )
