import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_depth_limit_enforced(tmp_path):
    """Orchestrator (depth 0) can spawn subagent (depth 1); subagent cannot spawn."""
    from aede.agents.orchestration import run_subagent, MAX_SPAWN_DEPTH
    from aede.agents.schema import AgentDef

    assert MAX_SPAWN_DEPTH == 1

    agent_def = AgentDef(name="sub", description="Subagent", max_turns=2)
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
    cfg.max_spawn_depth = 1
    gate_store = MagicMock()

    # Run at depth 1 should fail when trying to spawn another
    with patch("aede.agent.AgentLoop.__init__", return_value=None), \
         patch("aede.agent.AgentLoop.initialize"), \
         patch("aede.agent.AgentLoop.run_turn", new_callable=AsyncMock), \
         patch("aede.session.Session") as mock_session:

        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-005"
        mock_session.create.return_value = mock_session_instance

        result = await run_subagent(
            agent_def=agent_def,
            task="test",
            orchestrator_cfg=cfg,
            orchestrator_gate_store=gate_store,
            orchestrator_spawn_depth=1,
        )

    assert "spawn rejected" in result or "max depth" in result


def test_spawn_subagent_tool_includes_depth():
    """_spawn closure in router passes orchestrator_spawn_depth=1 to run_subagent."""
    from aede.tools.router import ToolRouter
    from pathlib import Path
    from unittest.mock import patch, MagicMock

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
        _cfg=MagicMock(),
        _gate_store=MagicMock(),
        _agent_registry={
            "sub": MagicMock(spec=["name", "tools", "disallowed_tools", "max_turns"]),
        },
        _session_id="test-001",
        data_dir=Path("/tmp"),
    )
    router._agent_registry["sub"].name = "sub"
    router._agent_registry["sub"].tools = []
    router._agent_registry["sub"].disallowed_tools = []
    router._agent_registry["sub"].max_turns = 2

    handler = router._registry.get("spawn_subagent")
    assert handler is not None, "spawn_subagent not registered"

    with patch("aede.agents.orchestration.run_subagent") as mock_run:
        mock_run.return_value = "done"
        handler({"agent_name": "sub", "task": "test"})

    _, kwargs = mock_run.call_args
    assert kwargs.get("orchestrator_spawn_depth") == 1, (
        f"Expected orchestrator_spawn_depth=1, got {kwargs.get('orchestrator_spawn_depth')}"
    )
