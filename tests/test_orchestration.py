import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from aede.agents.schema import AgentDef


def _make_cfg(tmp_path: Path, max_spawn_depth: int = 1) -> MagicMock:
    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    cfg.api_base_url = None
    cfg.home = tmp_path
    cfg.data_dir = tmp_path / "data"
    cfg.max_spawn_depth = max_spawn_depth
    return cfg


def _make_mock_loop():
    loop = MagicMock()
    loop.run_turn = AsyncMock()
    loop.initialize = MagicMock()
    loop._messages = [{"role": "assistant", "content": "done"}]
    return loop


@pytest.mark.asyncio
async def test_depth_0_spawn_succeeds(tmp_path):
    """depth-0 spawn (orchestrator calling run_subagent) must NOT be rejected."""
    from aede.agents.orchestration import run_subagent

    agent_def = AgentDef(name="sub", description="Subagent", max_turns=2)
    cfg = _make_cfg(tmp_path, max_spawn_depth=1)
    gate_store = MagicMock()
    mock_loop = _make_mock_loop()

    with patch("aede.agent.AgentLoop", return_value=mock_loop), \
         patch("aede.session.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-001"
        mock_session.create.return_value = mock_session_instance

        result = await run_subagent(
            agent_def=agent_def,
            task="test",
            orchestrator_cfg=cfg,
            orchestrator_gate_store=gate_store,
            orchestrator_spawn_depth=0,
        )

    assert "spawn rejected" not in result


@pytest.mark.asyncio
async def test_depth_1_rejected_with_max_1(tmp_path):
    """With max_spawn_depth=1, a depth-1 spawn IS rejected."""
    from aede.agents.orchestration import run_subagent

    agent_def = AgentDef(name="sub", description="Subagent", max_turns=2)
    cfg = _make_cfg(tmp_path, max_spawn_depth=1)
    gate_store = MagicMock()

    result = await run_subagent(
        agent_def=agent_def,
        task="test",
        orchestrator_cfg=cfg,
        orchestrator_gate_store=gate_store,
        orchestrator_spawn_depth=1,
    )

    assert "spawn rejected" in result


@pytest.mark.asyncio
async def test_depth_1_succeeds_with_max_2(tmp_path):
    """With max_spawn_depth=2, a depth-1 spawn SUCCEEDS."""
    from aede.agents.orchestration import run_subagent

    agent_def = AgentDef(name="sub", description="Subagent", max_turns=2)
    cfg = _make_cfg(tmp_path, max_spawn_depth=2)
    gate_store = MagicMock()
    mock_loop = _make_mock_loop()

    with patch("aede.agent.AgentLoop", return_value=mock_loop), \
         patch("aede.session.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-003"
        mock_session.create.return_value = mock_session_instance

        result = await run_subagent(
            agent_def=agent_def,
            task="test",
            orchestrator_cfg=cfg,
            orchestrator_gate_store=gate_store,
            orchestrator_spawn_depth=1,
        )

    assert "spawn rejected" not in result
