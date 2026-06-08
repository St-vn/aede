import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_subagent_e2e_orchestrator_spawn(tmp_path):
    """Orchestrator calls spawn_subagent tool, subagent runs independently, result returned."""
    from aede.tools.router import ToolRouter

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

    from aede.agents.schema import AgentDef
    agent_def = AgentDef(
        name="researcher",
        description="Research agent",
        tools=["read_file"],
        max_turns=3,
        body="## Researcher\nResearch.",
    )
    agent_registry = {"researcher": agent_def}

    router = ToolRouter(
        shell=cfg.shell,
        wsl_distro=cfg.wsl_distro,
        tool_output_max_tokens=cfg.tool_output_max_tokens,
        _cfg=cfg,
        _gate_store=gate_store,
        _agent_registry=agent_registry,
        _session_id="orch-sess-001",
    )

    assert "spawn_subagent" in router.tool_names()

    def mock_run_subagent(**kwargs):
        return "Research complete: found 42 answers."

    with patch("aede.agents.orchestration.run_subagent", side_effect=mock_run_subagent):
        result = router.execute_sync("spawn_subagent", {
            "agent_name": "researcher",
            "task": "find the answer",
        })

    assert result.status == "success", f"Got error output: {result.output}"
    assert "Research complete" in result.output
    assert "42" in result.output


def test_subagent_e2e_unknown_agent(tmp_path):
    """spawn_subagent with unknown agent returns error."""
    from aede.tools.router import ToolRouter

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
    agent_registry = {}

    router = ToolRouter(
        shell=cfg.shell,
        wsl_distro=cfg.wsl_distro,
        tool_output_max_tokens=cfg.tool_output_max_tokens,
        _cfg=cfg,
        _gate_store=gate_store,
        _agent_registry=agent_registry,
        _session_id="orch-sess-002",
    )

    result = router.execute_sync("spawn_subagent", {
        "agent_name": "nonexistent",
        "task": "do something",
    })

    assert result.status == "success"
    assert "unknown agent" in result.output.lower() or "nonexistent" in result.output
