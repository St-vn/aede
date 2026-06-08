"""
Subagent orchestration for aede.

Provides run_subagent() which creates an isolated AgentLoop with a filtered
ToolRouter, fresh message context, and per-agent model routing.  Subagents
are recorded in the DB with a parent_id linking them to the orchestrator
session.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from aede.agents.schema import AgentDef

MAX_SPAWN_DEPTH = 1


class DepthLimitError(Exception):
    """Raised when spawn depth exceeds MAX_SPAWN_DEPTH."""


def build_sub_cfg(orchestrator_cfg: Any, agent_def: AgentDef) -> Any:
    """Build a subagent config by copying orchestrator config and optionally
    overriding the model field.

    Args:
        orchestrator_cfg: The orchestrator's AedeConfig instance.
        agent_def: The agent definition with optional model override.

    Returns:
        A new AedeConfig (or compatible) with the model overridden if
        agent_def.model is not "inherit".
    """
    from copy import copy
    sub_cfg = copy(orchestrator_cfg)
    if agent_def.model != "inherit":
        sub_cfg.model = agent_def.model
    return sub_cfg


async def run_subagent(
    agent_def: AgentDef,
    task: str,
    orchestrator_cfg: Any,
    orchestrator_gate_store: Any,
    orchestrator_session_id: str | None = None,
    orchestrator_spawn_depth: int = 0,
) -> str:
    """Run a subagent in isolation and return its final text response.

    Args:
        agent_def: The agent definition to run.
        task: The task string to pass as the first user message.
        orchestrator_cfg: The orchestrator's AedeConfig (used as base).
        orchestrator_gate_store: Shared gate_store instance (same as orchestrator).
        orchestrator_session_id: The orchestrator's session id for parent_id linking.
        orchestrator_spawn_depth: Current spawn depth (0 = orchestrator).

    Returns:
        The final text response from the subagent, or an error string if
        the subagent was rejected or exceeded max_turns.
    """
    if orchestrator_spawn_depth >= MAX_SPAWN_DEPTH:
        return f"[subagent spawn rejected: max depth {MAX_SPAWN_DEPTH} reached]"

    from aede.tools.router import ToolRouter
    from aede.config import AedeConfig

    sub_cfg = build_sub_cfg(orchestrator_cfg, agent_def)

    if not isinstance(sub_cfg, AedeConfig):
        sub_cfg = AedeConfig(
            data={
                "model": sub_cfg.model,
                "shell": sub_cfg.shell,
                "wsl_distro": sub_cfg.wsl_distro,
                "tool_output_max_tokens": sub_cfg.tool_output_max_tokens,
                "context_window": sub_cfg.context_window,
                "compaction_threshold": sub_cfg.compaction_threshold,
                "batch_approval_max": getattr(sub_cfg, "batch_approval_max", 20),
                "auto_approve": getattr(sub_cfg, "auto_approve", []),
                "model_prices": getattr(sub_cfg, "model_prices", {}),
                "api_base_url": getattr(sub_cfg, "api_base_url", None),
            },
            home=getattr(orchestrator_cfg, "home", Path.home() / ".aede"),
        )

    sub_router = ToolRouter.from_allowlist(
        names=agent_def.tools,
        disallowed_tools=agent_def.disallowed_tools,
        shell=sub_cfg.shell,
        wsl_distro=sub_cfg.wsl_distro,
        tool_output_max_tokens=sub_cfg.tool_output_max_tokens,
    )

    from aede.db import DB
    from aede.session import Session
    from aede.rollout import Rollout
    from aede.tokens import TokenTracker
    from aede.agent import AgentLoop
    from rich.console import Console

    db = DB(sub_cfg.data_dir / "aede.db")
    sub_session = Session.create(
        db=db,
        model=sub_cfg.model,
        parent_id=orchestrator_session_id,
    )

    rollout = Rollout(sub_cfg.data_dir / "sessions", sub_session.id)
    rollout.write({"type": "subagent_start", "agent": agent_def.name, "session_id": sub_session.id})

    tracker = TokenTracker(session_id=sub_session.id, db=db)

    console = Console()

    agent = AgentLoop(
        cfg=sub_cfg,
        session=sub_session,
        db=db,
        rollout=rollout,
        router=sub_router,
        gate_store=orchestrator_gate_store,
        tracker=tracker,
        console=console,
        project_dir=Path.cwd(),
    )

    agent.initialize(is_resume=False, session_notes=None, compaction_summary=None)

    for turn in range(agent_def.max_turns):
        await agent.run_turn(task if turn == 0 else "")

        final_text = ""
        for msg in reversed(agent._messages):
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                final_text = msg["content"]
                break

        if final_text:
            sub_session.archive(db)
            rollout.write({"type": "subagent_end", "status": "completed"})
            return final_text

    sub_session.archive(db)
    rollout.write({"type": "subagent_end", "status": "max_turns"})
    return f"[subagent terminated: maxTurns ({agent_def.max_turns}) reached without final response]"
