import json
import pytest
from pathlib import Path
from aede.acp.credentials import CredentialProvider
from aede.acp.registry import AgentConfig, AgentTransport


def test_get_credential_from_vault(tmp_path):
    """US-ACP-006 AC-1: Retrieve a credential from the vault by key."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"CLAUDE_API_KEY": "sk-ant-abc123"}))

    provider = CredentialProvider(home=tmp_path)
    key = provider.get("CLAUDE_API_KEY")

    assert key == "sk-ant-abc123"


def test_missing_credential_raises(tmp_path):
    """Missing credential produces clear error."""
    provider = CredentialProvider(home=tmp_path)

    with pytest.raises(KeyError, match="Credential 'MISSING_KEY' not found"):
        provider.get("MISSING_KEY")


def test_credential_not_logged(capsys, tmp_path):
    """SEC-001: Credential values must not appear in stdout/logs."""
    vault_path = tmp_path / "credentials.json"
    vault_path.write_text(json.dumps({"SECRET": "sk-secret-xyz"}))

    provider = CredentialProvider(home=tmp_path)
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

    provider = CredentialProvider(home=tmp_path)
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

    provider = CredentialProvider(home=tmp_path)
    key = provider.get_for_agent(config)
    assert key is None


def test_credential_provider_reads_main_vault_nested_format(tmp_path):
    """Must read the nested {value, provider} format from main vault."""
    vault = tmp_path / "credentials.json"
    vault.write_text(json.dumps({
        "ANTHROPIC_API_KEY": {"value": "sk-ant-abc", "provider": "claude-code"}
    }))
    provider = CredentialProvider(home=tmp_path)
    assert provider.get("ANTHROPIC_API_KEY") == "sk-ant-abc"


def test_credential_provider_reads_flat_format_backward_compat(tmp_path):
    """Must still support old flat {key: value} format."""
    vault = tmp_path / "credentials.json"
    vault.write_text(json.dumps({"MY_KEY": "flat-value"}))
    provider = CredentialProvider(home=tmp_path)
    assert provider.get("MY_KEY") == "flat-value"


def test_credential_provider_falls_back_to_environ(tmp_path, monkeypatch):
    """Must fall back to os.environ if key not in vault cache."""
    monkeypatch.setenv("ENV_ONLY_KEY", "from-env")
    provider = CredentialProvider(home=tmp_path)
    assert provider.get("ENV_ONLY_KEY") == "from-env"


def test_credential_provider_missing_raises(tmp_path):
    """Must raise KeyError if key not in vault or environment."""
    provider = CredentialProvider(home=tmp_path)
    with pytest.raises(KeyError):
        provider.get("NONEXISTENT")


def test_get_for_agent_returns_none_when_no_ref(tmp_path):
    """get_for_agent returns None when agent has no credentials_ref."""
    from aede.acp.registry import AgentConfig, AgentTransport
    provider = CredentialProvider(home=tmp_path)
    config = AgentConfig(name="test", transport=AgentTransport.LOCAL, command="echo")
    assert provider.get_for_agent(config) is None


def test_env_wins_over_vault_us_sec_7(tmp_path, monkeypatch):
    """US-SEC-7 Scenario 7.1: env var takes precedence over vault/cache entry for same name."""
    vault = tmp_path / "credentials.json"
    vault.write_text(json.dumps({"CONFLICT_KEY": "vault-value"}))

    monkeypatch.setenv("CONFLICT_KEY", "env-value")

    provider = CredentialProvider(home=tmp_path)
    # Both vault AND env define CONFLICT_KEY — env must win.
    result = provider.get("CONFLICT_KEY")
    assert result == "env-value", (
        f"Expected env-value but got {result!r}. "
        "US-SEC-7: env vars must take precedence over vault entries."
    )
