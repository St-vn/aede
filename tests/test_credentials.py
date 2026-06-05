import json
import pytest

from jarvis.credentials import (
    credentials_path,
    load_credentials_into_env,
    set_credential,
    CredentialsError,
)


def test_credentials_path(tmp_path):
    assert credentials_path(tmp_path) == tmp_path / "credentials.json"


def test_set_credential_writes_json(tmp_path):
    set_credential(tmp_path, "OPENROUTER_API_KEY", "sk-or-v1-abc")
    path = tmp_path / "credentials.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"OPENROUTER_API_KEY": "sk-or-v1-abc"}


def test_load_populates_env_for_unset_name(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    set_credential(tmp_path, "OPENROUTER_API_KEY", "sk-or-v1-abc")
    loaded = load_credentials_into_env(tmp_path)
    import os
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-v1-abc"
    assert "OPENROUTER_API_KEY" in loaded


def test_real_env_takes_precedence(tmp_path, monkeypatch):
    # Real env var already set — vault value must NOT overwrite it.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-env-value")
    set_credential(tmp_path, "ANTHROPIC_API_KEY", "vault-value")
    loaded = load_credentials_into_env(tmp_path)
    import os
    assert os.environ["ANTHROPIC_API_KEY"] == "real-env-value"
    assert "ANTHROPIC_API_KEY" not in loaded


def test_set_credential_preserves_existing_keys(tmp_path, monkeypatch):
    set_credential(tmp_path, "KEY_ONE", "value-one")
    set_credential(tmp_path, "KEY_TWO", "value-two")
    data = json.loads((tmp_path / "credentials.json").read_text(encoding="utf-8"))
    assert data == {"KEY_ONE": "value-one", "KEY_TWO": "value-two"}


def test_set_credential_updates_existing_key(tmp_path):
    set_credential(tmp_path, "KEY_ONE", "old")
    set_credential(tmp_path, "KEY_TWO", "keep-me")
    set_credential(tmp_path, "KEY_ONE", "new")
    data = json.loads((tmp_path / "credentials.json").read_text(encoding="utf-8"))
    assert data == {"KEY_ONE": "new", "KEY_TWO": "keep-me"}


def test_malformed_json_raises_catchable_error(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(CredentialsError):
        load_credentials_into_env(tmp_path)
    # CredentialsError is a ValueError subclass, so it's catchable as ValueError too.
    assert issubclass(CredentialsError, ValueError)


def test_non_object_json_raises(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text('["not", "a", "dict"]', encoding="utf-8")
    with pytest.raises(CredentialsError):
        load_credentials_into_env(tmp_path)


def test_missing_file_returns_empty_no_raise(tmp_path):
    # No credentials.json present in tmp_path.
    result = load_credentials_into_env(tmp_path)
    assert result == []


def test_handle_setkey_writes_vault_and_sets_env(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from unittest.mock import MagicMock
    from jarvis.commands import handle_setkey

    console = MagicMock()
    handle_setkey(["openrouter_api_key", "sk-or-v1-xyz"], console, tmp_path)

    import os
    # Vault file written
    data = json.loads((tmp_path / "credentials.json").read_text(encoding="utf-8"))
    assert data == {"OPENROUTER_API_KEY": "sk-or-v1-xyz"}
    # Current session env set
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-v1-xyz"

    # Message must not make false "new shells" / OS env var claims.
    printed = " ".join(str(c.args[0]) for c in console.print.call_args_list if c.args)
    assert "credentials.json" in printed
    assert "new shell" not in printed.lower()
    assert "windows user env" not in printed.lower()


def test_handle_setkey_usage_when_too_few_args(tmp_path):
    from unittest.mock import MagicMock
    from jarvis.commands import handle_setkey
    console = MagicMock()
    handle_setkey(["only_one"], console, tmp_path)
    assert not (tmp_path / "credentials.json").exists()
