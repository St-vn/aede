"""ACP manager lifecycle / persistence integration tests (Track 2).

The existing test_acp_manager.py drives connect()/switch via a real subprocess
fake agent, but coverage showed manager.py 70-110 (session-resume persistence) and
200-207 (disconnect active-reassignment) untested. These cover the lifecycle tail
end-to-end using the same fake-agent transport.
"""
import json
import pytest
from pathlib import Path

from aede.acp.manager import AcpManager
from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport
from aede.acp.credentials import CredentialProvider

# Reuse the real fake-agent subprocess helper from the sibling test module.
from tests.test_acp_manager import make_agent_script


def _registry_with(tmp_path: Path, *agents: tuple[str, str]) -> AgentRegistry:
    registry = AgentRegistry(config_dir=tmp_path)
    for name, sid in agents:
        script = make_agent_script(tmp_path, name, sid)
        registry.add(AgentConfig(
            name=name, transport=AgentTransport.LOCAL,
            command="python", args=[str(script)],
        ))
    return registry


async def test_connect_persists_session_to_cache(tmp_path):
    """A successful connect writes the session id to the sessions cache file."""
    registry = _registry_with(tmp_path, ("alpha", "sess_alpha"))
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    await manager.connect("alpha")

    cache = manager._sessions_cache_path
    assert cache.exists()
    data = json.loads(cache.read_text(encoding="utf-8"))
    assert data["alpha"] == "sess_alpha"


async def test_reconnect_uses_cached_session_shortcircuit(tmp_path):
    """A second connect to an already-connected agent returns the cached id
    without re-driving the transport."""
    registry = _registry_with(tmp_path, ("alpha", "sess_alpha"))
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    sid1 = await manager.connect("alpha")
    sid2 = await manager.connect("alpha")  # in-memory short-circuit (manager.py:85-87)
    assert sid1 == sid2 == "sess_alpha"
    assert manager.list_connected() == ["alpha"]


async def test_disconnect_removes_session_and_reassigns_active(tmp_path):
    """Disconnecting the active agent removes it and promotes another to active."""
    registry = _registry_with(tmp_path, ("alpha", "sess_alpha"), ("beta", "sess_beta"))
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    await manager.connect("alpha")
    await manager.connect("beta")
    assert manager.active_session_id() == "sess_beta"

    await manager.disconnect("beta")  # active -> must reassign (manager.py:206-207)
    assert "beta" not in manager.list_connected()
    assert manager.active_session_id() == "sess_alpha"

    # Cache no longer holds the disconnected agent.
    data = json.loads(manager._sessions_cache_path.read_text(encoding="utf-8"))
    assert "beta" not in data


async def test_disconnect_unknown_agent_is_noop(tmp_path):
    """Disconnecting an agent that was never connected does nothing, no error."""
    registry = _registry_with(tmp_path, ("alpha", "sess_alpha"))
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))
    await manager.disconnect("never-connected")  # must not raise
    assert manager.list_connected() == []


async def test_disconnect_last_agent_clears_active(tmp_path):
    """Disconnecting the only agent leaves no active session."""
    registry = _registry_with(tmp_path, ("alpha", "sess_alpha"))
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))
    await manager.connect("alpha")
    await manager.disconnect("alpha")
    assert manager.active_session_id() is None
    assert manager.list_connected() == []
