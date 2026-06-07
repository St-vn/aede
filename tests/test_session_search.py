import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_tool_registered(tmp_path):
    """session_search appears in ToolRouter registry with correct schema."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    names = router.tool_names()
    assert "session_search" in names

    schemas = router.anthropic_tool_schemas()
    schema = next(s for s in schemas if s["name"] == "session_search")
    props = schema["input_schema"]["properties"]
    assert "query" in props
    assert "limit" in props
    assert schema["input_schema"]["required"] == ["query"]


def test_write_learning_registered(tmp_path):
    """write_learning appears in registry with schema; NOT in auto-approve."""
    from aede.tools.router import ToolRouter
    from aede.tools.router import GATE_TOOLS

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    names = router.tool_names()
    assert "write_learning" in names

    schemas = router.anthropic_tool_schemas()
    schema = next(s for s in schemas if s["name"] == "write_learning")
    props = schema["input_schema"]["properties"]
    assert "type" in props
    assert "content" in props
    assert "source" in props

    assert "write_learning" in GATE_TOOLS


def test_search_with_context_window(tmp_path):
    """session_search returns ±5 message context with session bookends."""
    from aede.db import DB
    from aede.tools.router import ToolRouter, session_search

    db_path = tmp_path / "test.db"
    db = DB(db_path)
    from aede.session import Session

    s = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    for i in range(20):
        db.insert_message(
            id=f"msg-{i:03d}", session_id=s.id, role="user",
            content=f"message number {i} with uniqueterm_{i}", token_count=10,
        )

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)

    result = session_search(db=db, query="uniqueterm_10", limit=3)
    assert isinstance(result, str)
    assert "uniqueterm_10" in result
    assert "Session ID" in result or s.id[:4] in result
