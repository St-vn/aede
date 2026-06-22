"""Tests for ACP registry seeding and sub-model resolution in AcpProvider.

Covers:
- seed_default_agents registers the 6 base agents and is idempotent
- seeding does NOT overwrite pre-existing user configs (only-add-if-missing)
- After seeding, connect('claude-code') no longer raises KeyError (registry side)
- AcpProvider.stream_turn with sub-model resolves base agent + sets model_override
- Disconnect/reconnect when override changes between turns
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, call

from aede.acp.registry import AgentRegistry, AgentConfig, AgentTransport, seed_default_agents
from aede.acp.credentials import CredentialProvider


# ---------------------------------------------------------------------------
# seed_default_agents — registration
# ---------------------------------------------------------------------------

BASE_AGENT_NAMES = {"codex", "claude-code", "gemini", "cline", "cursor", "goose"}


def test_seed_default_agents_registers_all_6(tmp_path):
    """seed_default_agents should register exactly the 6 base ACP agents."""
    registry = AgentRegistry(config_dir=tmp_path)
    seed_default_agents(registry)
    names = {a.name for a in registry.list_all()}
    assert BASE_AGENT_NAMES == names


def test_seed_idempotent_no_raise(tmp_path):
    """Calling seed_default_agents twice must not raise and must not duplicate."""
    registry = AgentRegistry(config_dir=tmp_path)
    seed_default_agents(registry)
    seed_default_agents(registry)  # second call — must be silent
    assert len(registry.list_all()) == 6


def test_seed_does_not_overwrite_user_config(tmp_path):
    """If user already has a custom claude-code config, seed must leave it untouched."""
    registry = AgentRegistry(config_dir=tmp_path)
    # Pre-add a customised claude-code entry
    custom_cfg = AgentConfig(
        name="claude-code",
        transport=AgentTransport.LOCAL,
        command="my-custom-cmd",
        args=["--custom-flag"],
        credentials_ref="MY_CUSTOM_KEY",
    )
    registry.add(custom_cfg)

    seed_default_agents(registry)

    cfg = registry.get("claude-code")
    assert cfg.command == "my-custom-cmd", "seed overwrote user config — it must not"
    assert cfg.args == ["--custom-flag"]
    assert cfg.credentials_ref == "MY_CUSTOM_KEY"


def test_seed_credentials_ref_for_known_agents(tmp_path):
    """Seeded agents with known credentials_ref should have them set correctly."""
    registry = AgentRegistry(config_dir=tmp_path)
    seed_default_agents(registry)

    assert registry.get("codex").credentials_ref == "OPENAI_API_KEY"
    assert registry.get("claude-code").credentials_ref == "ANTHROPIC_API_KEY"
    assert registry.get("gemini").credentials_ref == "GEMINI_API_KEY"
    assert registry.get("cursor").credentials_ref == "CURSOR_API_KEY"
    # cline, goose have no credentials_ref
    assert registry.get("cline").credentials_ref is None
    assert registry.get("goose").credentials_ref is None


def test_seed_commands_match_acp_commands(tmp_path):
    """Seeded base-agent command/args should match ACP_COMMANDS in commands.py."""
    from aede.commands import ACP_COMMANDS
    registry = AgentRegistry(config_dir=tmp_path)
    seed_default_agents(registry)

    for name in BASE_AGENT_NAMES:
        cfg = registry.get(name)
        expected_cmd, expected_args = ACP_COMMANDS[name]
        assert cfg.command == expected_cmd, f"{name}: command mismatch"
        assert cfg.args == expected_args, f"{name}: args mismatch"


# ---------------------------------------------------------------------------
# After seeding: registry lookup no longer raises KeyError
# ---------------------------------------------------------------------------

def test_registry_get_succeeds_after_seed(tmp_path):
    """After seeding, registry.get('claude-code') returns a valid config (no KeyError)."""
    registry = AgentRegistry(config_dir=tmp_path)
    # Without seeding this would raise KeyError
    with pytest.raises(KeyError):
        registry.get("claude-code")

    seed_default_agents(registry)
    # After seeding it must succeed
    cfg = registry.get("claude-code")
    assert cfg.name == "claude-code"
    assert cfg.command == "npx"


def test_registry_get_all_base_agents_after_seed(tmp_path):
    """After seeding, registry.get() works for all 7 base agent names."""
    registry = AgentRegistry(config_dir=tmp_path)
    seed_default_agents(registry)

    for name in BASE_AGENT_NAMES:
        cfg = registry.get(name)  # must not raise
        assert cfg.name == name


async def test_connect_without_seed_raises_key_error(tmp_path):
    """Without seeding, connect('claude-code') raises KeyError (regression guard)."""
    from aede.acp.manager import AcpManager

    registry = AgentRegistry(config_dir=tmp_path)  # empty
    manager = AcpManager(registry, CredentialProvider(home=tmp_path))

    with pytest.raises(KeyError, match="not found"):
        await manager.connect("claude-code")


# ---------------------------------------------------------------------------
# AcpProvider.stream_turn — sub-model resolution
# ---------------------------------------------------------------------------

def _make_mock_manager(connected=None):
    """Build a MagicMock that stands in for AcpManager."""
    manager = MagicMock()
    manager.list_connected.return_value = list(connected or [])
    manager.connect = AsyncMock(return_value="sess_1")
    manager.disconnect = AsyncMock()

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "response from agent"
    mock_result.stop_reason = "end_turn"
    mock_session.session.prompt = AsyncMock(return_value=mock_result)
    manager.active_session.return_value = mock_session

    # Registry mock: get() returns a writable AgentConfig
    registry = MagicMock()
    base_config = AgentConfig(
        name="claude-code",
        transport=AgentTransport.LOCAL,
        command="npx",
        args=["-y", "@agentclientprotocol/claude-agent-acp"],
    )
    registry.get.return_value = base_config
    manager._registry = registry

    return manager, base_config


async def test_acp_provider_submodel_resolves_base_agent():
    """stream_turn with 'claude-code/opus-4-8' should connect to 'claude-code'."""
    from aede.provider import AcpProvider

    manager, _ = _make_mock_manager()
    provider = AcpProvider(model="claude-code/opus-4-8", acp_manager=manager)
    console = MagicMock()

    await provider.stream_turn(
        model="claude-code/opus-4-8",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    # Must connect to the BASE agent, not the sub-model id
    manager.connect.assert_called_once_with("claude-code")


async def test_acp_provider_submodel_sets_model_override():
    """stream_turn with 'claude-code/opus-4-8' must set model_override on the config."""
    from aede.provider import AcpProvider

    manager, base_config = _make_mock_manager()
    provider = AcpProvider(model="claude-code/opus-4-8", acp_manager=manager)
    console = MagicMock()

    await provider.stream_turn(
        model="claude-code/opus-4-8",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    # model_override should be set to the resolved string
    assert base_config.model_override == "claude-opus-4-8"
    # upsert should have been called to persist the override
    manager._registry.upsert.assert_called_once()


async def test_acp_provider_base_model_no_override():
    """stream_turn with bare 'claude-code' should not touch model_override."""
    from aede.provider import AcpProvider

    manager, base_config = _make_mock_manager()
    provider = AcpProvider(model="claude-code", acp_manager=manager)
    console = MagicMock()

    await provider.stream_turn(
        model="claude-code",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    # No model_override interaction for base model
    manager._registry.get.assert_not_called()
    manager._registry.upsert.assert_not_called()
    manager.connect.assert_called_once_with("claude-code")


async def test_acp_provider_override_change_triggers_reconnect():
    """Switching from opus-4-8 to sonnet-4-6 sub-models should disconnect+reconnect."""
    from aede.provider import AcpProvider

    # Use a mutable set so that list_connected reflects disconnect calls
    connected_set = {"claude-code"}
    manager, base_config = _make_mock_manager(connected=["claude-code"])
    # Simulate already connected to claude-code with opus-4-8 override
    base_config.model_override = "claude-opus-4-8"

    # Make list_connected reflect the actual state (updated by disconnect side-effect)
    async def _disconnect(name):
        connected_set.discard(name)
    manager.disconnect.side_effect = _disconnect
    manager.list_connected.side_effect = lambda: list(connected_set)

    provider = AcpProvider(model="claude-code/opus-4-8", acp_manager=manager)
    provider._current_agent = "claude-code"
    console = MagicMock()

    # Now switch to sonnet-4-6 — should disconnect to restart subprocess with new env
    await provider.stream_turn(
        model="claude-code/sonnet-4-6",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    # Must have disconnected (because override changed) then reconnected
    manager.disconnect.assert_called_with("claude-code")
    manager.connect.assert_called_with("claude-code")
    # Override must be updated to the new value
    assert base_config.model_override == "claude-sonnet-4-6"


async def test_acp_provider_same_override_no_unnecessary_reconnect():
    """Same sub-model on second turn must NOT disconnect/reconnect."""
    from aede.provider import AcpProvider

    manager, base_config = _make_mock_manager(connected=["claude-code"])
    # Override already set to same value
    base_config.model_override = "claude-opus-4-8"

    provider = AcpProvider(model="claude-code/opus-4-8", acp_manager=manager)
    provider._current_agent = "claude-code"
    console = MagicMock()

    await provider.stream_turn(
        model="claude-code/opus-4-8",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    # No disconnect — override unchanged
    manager.disconnect.assert_not_called()
    # Already connected → switch_to, not connect
    manager.switch_to.assert_called_once_with("claude-code")


async def test_acp_provider_current_agent_tracks_base():
    """_current_agent should be set to base agent name, not sub-model id."""
    from aede.provider import AcpProvider

    manager, _ = _make_mock_manager()
    provider = AcpProvider(model="agy/gemini-3-5-flash", acp_manager=manager)

    # Patch registry.get for the agy base config
    agy_config = AgentConfig(
        name="agy", transport=AgentTransport.LOCAL, command="agy", args=["--acp"]
    )
    manager._registry.get.return_value = agy_config

    console = MagicMock()
    await provider.stream_turn(
        model="agy/gemini-3-5-flash",
        system="sys",
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=1000,
        console=console,
    )

    assert provider._current_agent == "agy"
