import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_subagent_session_parent_recorded(tmp_path):
    """Subagent session has parent_id set when creating Session."""
    from aede.agents.orchestration import run_subagent
    from aede.agents.schema import AgentDef

    agent_def = AgentDef(name="db-agent", description="DB test", max_turns=2)
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
    cfg.batch_approval_max = 20
    cfg.auto_approve = []
    cfg.model_prices = {}
    gate_store = MagicMock()

    captured_parent_id = []
    captured_model = []

    def fake_session_create(db, model, parent_id, title=None):
        captured_parent_id.append(parent_id)
        captured_model.append(model)
        instance = MagicMock()
        instance.id = "sub-db-001"
        instance.status = "active"
        return instance

    mock_agent = MagicMock()
    mock_agent._messages = [{"role": "assistant", "content": "Done."}]
    mock_agent.run_turn = AsyncMock()

    with patch("aede.session.Session.create", side_effect=fake_session_create), \
         patch("aede.agent.AgentLoop", return_value=mock_agent):

        result = await run_subagent(
            agent_def=agent_def,
            task="test",
            orchestrator_cfg=cfg,
            orchestrator_gate_store=gate_store,
            orchestrator_session_id="parent-001",
        )

    assert captured_parent_id == ["parent-001"]
    assert captured_model == [cfg.model]
    assert result == "Done."
