import asyncio
import pytest
from unittest.mock import MagicMock
from aede.agent import AgentLoop


def test_agent_loop_exposes_stop_events():
    loop = AgentLoop.__new__(AgentLoop)
    assert hasattr(loop, "request_stop")
    assert hasattr(loop, "request_stop_after_current_tool")


def test_agent_loop_stop_events_initialized():
    from unittest.mock import MagicMock
    loop = AgentLoop(
        cfg=MagicMock(),
        session=MagicMock(),
        db=MagicMock(),
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=MagicMock(),
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=MagicMock(),
    )
    assert isinstance(loop._stop_requested, asyncio.Event)
    assert isinstance(loop._stop_after_current_tool, asyncio.Event)
    assert not loop._stop_requested.is_set()
    assert not loop._stop_after_current_tool.is_set()


def test_request_stop_sets_event():
    from unittest.mock import MagicMock
    loop = AgentLoop(
        cfg=MagicMock(),
        session=MagicMock(),
        db=MagicMock(),
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=MagicMock(),
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=MagicMock(),
    )
    assert not loop._stop_requested.is_set()
    loop.request_stop()
    assert loop._stop_requested.is_set()
    assert not loop._stop_after_current_tool.is_set()


def test_request_stop_after_current_tool_sets_event():
    from unittest.mock import MagicMock
    loop = AgentLoop(
        cfg=MagicMock(),
        session=MagicMock(),
        db=MagicMock(),
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=MagicMock(),
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=MagicMock(),
    )
    assert not loop._stop_after_current_tool.is_set()
    loop.request_stop_after_current_tool()
    assert loop._stop_after_current_tool.is_set()
    assert not loop._stop_requested.is_set()
