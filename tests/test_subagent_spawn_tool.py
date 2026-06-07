import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_spawn_subagent_in_tool_schemas():
    """spawn_subagent(agent_name: str, task: str) appears in anthropic_tool_schemas."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    schemas = router.anthropic_tool_schemas()
    names = [s["name"] for s in schemas]
    assert "spawn_subagent" in names

    spawn_schema = next(s for s in schemas if s["name"] == "spawn_subagent")
    props = spawn_schema["input_schema"]["properties"]
    assert "agent_name" in props
    assert "task" in props
    assert spawn_schema["input_schema"]["required"] == ["agent_name", "task"]


def test_spawn_subagent_execute_returns_result():
    """spawn_subagent tool executes run_subagent and returns result string."""
    from aede.tools.router import ToolRouter
    from unittest.mock import MagicMock, patch

    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.wsl_distro = ""
    cfg.tool_output_max_tokens = 8000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.85
    cfg.api_base_url = None
    cfg.home = Path("/tmp")
    cfg.data_dir = Path("/tmp/data")

    gate_store = MagicMock()
    agent_registry = {"researcher": MagicMock()}

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
        _cfg=cfg,
        _gate_store=gate_store,
        _agent_registry=agent_registry,
        _session_id="test-sess",
    )

    mock_result = "Research complete: found 42."

    async def mock_subagent(**kwargs):
        return mock_result

    with patch("aede.agents.orchestration.run_subagent", side_effect=mock_subagent) as mock_fn:
        result = router.execute_sync("spawn_subagent", {"agent_name": "researcher", "task": "find X"})

    assert result.status == "success"
    assert result.output == mock_result
