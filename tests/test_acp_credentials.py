import json
import pytest
from pathlib import Path
from aede.acp.credentials import CredentialProvider
from aede.acp.registry import AgentConfig, AgentTransport


def test_get_credential_from_vault(tmp_path):
    """US-ACP-006 AC-1: Retrieve a credential from the vault by key."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"CLAUDE_API_KEY": "sk-ant-abc123"}))

    provider = CredentialProvider(vault_dir=tmp_path)
    key = provider.get("CLAUDE_API_KEY")

    assert key == "sk-ant-abc123"


def test_missing_credential_raises(tmp_path):
    """Missing credential produces clear error."""
    provider = CredentialProvider(vault_dir=tmp_path)

    with pytest.raises(KeyError, match="Credential 'MISSING_KEY' not found"):
        provider.get("MISSING_KEY")


def test_credential_not_logged(capsys, tmp_path):
    """SEC-001: Credential values must not appear in stdout/logs."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"SECRET": "sk-secret-xyz"}))

    provider = CredentialProvider(vault_dir=tmp_path)
    _key = provider.get("SECRET")

    captured = capsys.readouterr()
    assert "sk-secret-xyz" not in captured.out
    assert "sk-secret-xyz" not in captured.err


def test_get_with_agent_config_field(tmp_path):
    """Resolve credentials_ref from AgentConfig."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"GEMINI_API_KEY": "gemini-key-456"}))

    config = AgentConfig(
        name="gemini",
        transport=AgentTransport.LOCAL,
        command="gemini",
        args=["--experimental-acp"],
        credentials_ref="GEMINI_API_KEY",
    )

    provider = CredentialProvider(vault_dir=tmp_path)
    key = provider.get_for_agent(config)

    assert key == "gemini-key-456"


def test_get_for_agent_no_ref(tmp_path):
    """get_for_agent returns None when agent has no credentials_ref."""
    config = AgentConfig(
        name="no-auth",
        transport=AgentTransport.LOCAL,
        command="python",
        args=[],
        credentials_ref=None,
    )

    provider = CredentialProvider(vault_dir=tmp_path)
    key = provider.get_for_agent(config)
    assert key is None
