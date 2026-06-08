import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_subagent_result_returned(tmp_path):
    """run_subagent returns final text response from subagent."""
    from aede.agents.orchestration import run_subagent
    from aede.agents.schema import AgentDef

    agent_def = AgentDef(name="helper", description="Helper", max_turns=5)
    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    cfg.data_dir = tmp_path / "data"
    cfg.home = tmp_path
    cfg.api_base_url = None
    cfg.batch_approval_max = 20
    cfg.auto_approve = []
    cfg.model_prices = {}
    gate_store = MagicMock()

    mock_agent = MagicMock()
    mock_agent._messages = [{"role": "assistant", "content": "Final result text."}]
    mock_agent.run_turn = AsyncMock()

    with patch("aede.session.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-002"
        mock_session.create.return_value = mock_session_instance

        with patch("aede.agent.AgentLoop", return_value=mock_agent):
            result = await run_subagent(
                agent_def=agent_def,
                task="Do the thing",
                orchestrator_cfg=cfg,
                orchestrator_gate_store=gate_store,
            )

    assert result == "Final result text."


@pytest.mark.asyncio
async def test_subagent_max_turns_exceeded(tmp_path):
    """maxTurns exceeded returns error string."""
    from aede.agents.orchestration import run_subagent
    from aede.agents.schema import AgentDef

    agent_def = AgentDef(name="looper", description="Loops", max_turns=2)
    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    cfg.data_dir = tmp_path / "data"
    cfg.home = tmp_path
    cfg.api_base_url = None
    cfg.batch_approval_max = 20
    cfg.auto_approve = []
    cfg.model_prices = {}
    gate_store = MagicMock()

    mock_agent = MagicMock()
    mock_agent._messages = []
    mock_agent.run_turn = AsyncMock()

    with patch("aede.session.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-003"
        mock_session.create.return_value = mock_session_instance

        with patch("aede.agent.AgentLoop", return_value=mock_agent):
            result = await run_subagent(
                agent_def=agent_def,
                task="Loop forever",
                orchestrator_cfg=cfg,
                orchestrator_gate_store=gate_store,
            )

    assert "maxTurns" in result
    assert "2" in result
