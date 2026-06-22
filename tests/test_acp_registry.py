import pytest
from pathlib import Path
from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport


def test_add_and_list_agents(tmp_path):
    """US-ACP-002 AC-1: Register an agent and verify it appears in the list."""
    registry = AgentRegistry(config_dir=tmp_path)

    registry.add(AgentConfig(
        name="claude-agent",
        transport=AgentTransport.LOCAL,
        command="npx",
        args=["@agentclientprotocol/claude-agent-acp"],
    ))

    agents = registry.list_all()
    assert len(agents) == 1
    assert agents[0].name == "claude-agent"
    assert agents[0].transport == AgentTransport.LOCAL
    assert agents[0].command == "npx"


def test_add_duplicate_raises(tmp_path):
    """US-ACP-002 AC-2: Adding an agent with a duplicate name raises ValueError."""
    registry = AgentRegistry(config_dir=tmp_path)

    registry.add(AgentConfig(
        name="claude-agent",
        transport=AgentTransport.LOCAL,
        command="npx",
        args=["@agentclientprotocol/claude-agent-acp"],
    ))

    with pytest.raises(ValueError, match="already exists"):
        registry.add(AgentConfig(
            name="claude-agent",
            transport=AgentTransport.LOCAL,
            command="npx",
            args=["@agentclientprotocol/claude-agent-acp"],
        ))


def test_get_agent(tmp_path):
    """Retrieve a single agent by name."""
    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(
        name="test-agent",
        transport=AgentTransport.LOCAL,
        command="python",
        args=["-m", "test"],
    ))

    agent = registry.get("test-agent")
    assert agent.name == "test-agent"
    assert agent.command == "python"


def test_get_missing_raises(tmp_path):
    """Getting a non-existent agent raises KeyError."""
    registry = AgentRegistry(config_dir=tmp_path)
    with pytest.raises(KeyError, match="not found"):
        registry.get("nonexistent")


def test_remove_agent(tmp_path):
    """Remove an agent from the registry."""
    registry = AgentRegistry(config_dir=tmp_path)
    registry.add(AgentConfig(
        name="to-remove",
        transport=AgentTransport.LOCAL,
        command="echo",
        args=[],
    ))

    registry.remove("to-remove")
    assert len(registry.list_all()) == 0


def test_persistence_across_instances(tmp_path):
    """Agents survive Registry re-initialization (persisted to disk)."""
    registry1 = AgentRegistry(config_dir=tmp_path)
    registry1.add(AgentConfig(
        name="persistent-agent",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[],
    ))

    registry2 = AgentRegistry(config_dir=tmp_path)
    agents = registry2.list_all()
    assert len(agents) == 1
    assert agents[0].name == "persistent-agent"


def test_transport_enum_values():
    """AgentTransport enum has expected values."""
    assert AgentTransport.LOCAL.value == "local"
