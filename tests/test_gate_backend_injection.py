# tests/test_gate_backend_injection.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def db(tmp_path):
    from aede.db import DB
    return DB(tmp_path / "test.db")

def test_agent_loop_accepts_gate_backend_kwarg(db, tmp_path):
    from aede.agent import AgentLoop
    from aede.gate import GateBackend
    mock = AsyncMock(spec=GateBackend)
    # Must not raise TypeError
    # We need to provide other required arguments to AgentLoop
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.home = tmp_path
    loop = AgentLoop(
        cfg=cfg,
        session=MagicMock(id="s_test"),
        db=db,
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=MagicMock(),
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=tmp_path,
        gate_backend=mock
    )
    assert loop._gate_backend is mock

def test_agent_loop_defaults_to_terminal_backend(db, tmp_path):
    from aede.agent import AgentLoop
    from aede.gate import TerminalGateBackend
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.home = tmp_path
    loop = AgentLoop(
        cfg=cfg,
        session=MagicMock(id="s_test"),
        db=db,
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=MagicMock(),
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=tmp_path
    )
    assert isinstance(loop._gate_backend, TerminalGateBackend)

def test_no_web_imports_in_agent():
    import ast, pathlib
    src = pathlib.Path("aede/agent.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):    
            names = [n.name for n in getattr(node, 'names', [])]
            mod = getattr(node, 'module', '') or ''
            assert 'fastapi' not in mod and 'websocket' not in mod.lower(), \
                f"Web import found in agent.py: {mod} {names}"
