import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


def test_subagent_model_override():
    """Agent with explicit model overrides config; 'inherit' uses orchestrator model."""
    from aede.agents.orchestration import build_sub_cfg
    from aede.agents.schema import AgentDef

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

    agent_haiku = AgentDef(name="haiku", description="Uses Haiku", model="claude-haiku-3-20240307")
    sub_cfg = build_sub_cfg(orchestrator_cfg=cfg, agent_def=agent_haiku)
    assert sub_cfg.model == "claude-haiku-3-20240307"

    agent_inherit = AgentDef(name="inherit", description="Inherits")
    sub_cfg2 = build_sub_cfg(orchestrator_cfg=cfg, agent_def=agent_inherit)
    assert sub_cfg2.model == "claude-sonnet-4-20250514"
