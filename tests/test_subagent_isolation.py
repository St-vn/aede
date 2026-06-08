import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_subagent_router_filtered():
    """Subagent creates ToolRouter with only declared tools."""
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=["read_file", "web_search"],
        disallowed_tools=["powershell"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    tool_names = router.tool_names()
    assert "read_file" in tool_names
    assert "web_search" in tool_names
    assert "powershell" not in tool_names
    assert "write_file" not in tool_names


@pytest.mark.asyncio
async def test_subagent_router_from_agent_tools(tmp_path):
    """run_subagent constructs ToolRouter matching agent_def tools."""
    from aede.agents.orchestration import run_subagent
    from aede.agents.schema import AgentDef

    agent_def = AgentDef(
        name="researcher",
        description="Research agent",
        tools=["read_file", "web_search"],
        disallowed_tools=["powershell"],
        max_turns=3,
    )

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

    Router_result = []

    original_from_allowlist = None
    from aede.tools.router import ToolRouter

    def spy_from_allowlist(names=None, disallowed_tools=None, shell="powershell", wsl_distro="", tool_output_max_tokens=8000):
        result = ToolRouter(shell=shell, wsl_distro=wsl_distro, tool_output_max_tokens=tool_output_max_tokens)
        Router_result.append((names, disallowed_tools))
        return result

    # Set a class-level _messages so the orchestration loop can access it
    # when __init__ runs (it sets instance attr, but keep class fallback)
    from aede.agent import AgentLoop as _AgentLoop
    _AgentLoop._messages = []

    with patch("aede.tools.router.ToolRouter.from_allowlist", side_effect=spy_from_allowlist), \
         patch("aede.agent.AgentLoop.initialize"), \
         patch("aede.agent.AgentLoop.run_turn", new_callable=AsyncMock), \
         patch("aede.session.Session") as mock_session:

        mock_session_instance = MagicMock()
        mock_session_instance.id = "sub-001"
        mock_session.create.return_value = mock_session_instance

        await run_subagent(
            agent_def=agent_def,
            task="Find information",
            orchestrator_cfg=cfg,
            orchestrator_gate_store=gate_store,
        )

    assert len(Router_result) == 1
    names, disallowed = Router_result[0]
    assert "read_file" in names
    assert "web_search" in names
    assert "powershell" in disallowed
