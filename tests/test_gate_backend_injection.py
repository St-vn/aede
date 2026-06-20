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

def test_agent_mode_tracks_gate_store_after_switch(db, tmp_path):
    """Regression: ``/mode`` mutates gate_store only. The agent must read its
    mode live from the gate_store, not from a stale copy captured at init,
    otherwise EXECUTION/AUTO keep prompting after a mid-session switch."""
    from aede.agent import AgentLoop
    from aede.gate import PermissionStore, PermissionMode
    from aede.commands import handle_mode
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.home = tmp_path
    cfg.gate_mode = "normal"
    store = PermissionStore(project_dir=tmp_path)
    # Session reports no stored mode so init does not override the store.
    session = MagicMock(id="s_test", gate_mode=None)
    loop = AgentLoop(
        cfg=cfg,
        session=session,
        db=db,
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=store,
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=tmp_path,
        gate_backend=AsyncMock(),
    )
    assert loop._mode is PermissionMode.NORMAL

    handle_mode(["auto"], gate_store=store, console=MagicMock(),
                cfg=cfg, session=None, db=None)
    assert loop._mode is PermissionMode.AUTO

    handle_mode(["execution"], gate_store=store, console=MagicMock(),
                cfg=cfg, session=None, db=None)
    assert loop._mode is PermissionMode.EXECUTION


def test_agent_init_seeds_store_from_session_mode(db, tmp_path):
    """A session with a stored gate_mode (via /resume) seeds the gate_store."""
    from aede.agent import AgentLoop
    from aede.gate import PermissionStore, PermissionMode
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.home = tmp_path
    cfg.gate_mode = "normal"
    store = PermissionStore(project_dir=tmp_path)
    session = MagicMock(id="s_test", gate_mode="execution")
    loop = AgentLoop(
        cfg=cfg,
        session=session,
        db=db,
        rollout=MagicMock(),
        router=MagicMock(),
        gate_store=store,
        tracker=MagicMock(),
        console=MagicMock(),
        project_dir=tmp_path,
        gate_backend=AsyncMock(),
    )
    assert loop._mode is PermissionMode.EXECUTION
    assert store.mode is PermissionMode.EXECUTION


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
