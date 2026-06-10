from unittest.mock import MagicMock
from aede.acp.client import AcpError
from aede.acp.auth import (
    NeedsBrowser, NeedsTerminal, NeedsKey, Progress, Connected, Failed, AuthStep,
    is_auth_required, terminal_auth_for, drive_auth,
)
from aede.acp.registry import AgentConfig, AgentTransport


def test_auth_step_types_carry_their_payloads():
    nb = NeedsBrowser(method_id="oauth-google")
    assert isinstance(nb, AuthStep)
    assert nb.method_id == "oauth-google"

    nt = NeedsTerminal(command="claude", args=["auth", "login"])
    assert nt.command == "claude" and nt.args == ["auth", "login"]

    nk = NeedsKey(env_var="OPENAI_API_KEY")
    assert nk.env_var == "OPENAI_API_KEY"

    pr = Progress(message="Opening browser...")
    assert pr.message == "Opening browser..."

    co = Connected(session_id="sess_123")
    assert co.session_id == "sess_123"

    fa = Failed(reason="login cancelled")
    assert fa.reason == "login cancelled"

    # SEC-002: no event type carries a raw token/secret field
    for cls in (NeedsBrowser, NeedsTerminal, NeedsKey, Progress, Connected, Failed):
        assert "token" not in getattr(cls, "__annotations__", {})
        assert "secret" not in getattr(cls, "__annotations__", {})


def test_is_auth_required_matches_code():
    err = AcpError(-32000, "auth required")
    assert is_auth_required(err)


def test_is_auth_required_other_code():
    err = AcpError(-1, "something else")
    assert not is_auth_required(err)


def test_terminal_auth_for_claude_code():
    spec = terminal_auth_for("claude-code")
    assert spec is not None
    cmd, args = spec
    assert cmd == "claude"
    assert args == ["auth", "login"]


def test_terminal_auth_for_sub_entry():
    spec = terminal_auth_for("claude-code/opus-4-8")
    assert spec is not None


def test_terminal_auth_for_unknown():
    assert terminal_auth_for("codex") is None


def _mock_client(auth_methods=None, init_ok=True, session_ok=True, init_error=None, session_error=None):
    client = MagicMock()
    if init_error:
        client.initialize.side_effect = init_error
    else:
        result = MagicMock()
        result.auth_methods = auth_methods or []
        client.initialize.return_value = result
    if session_error:
        client.new_session.side_effect = session_error
    else:
        client.new_session.return_value = "sess_000"
    if init_ok and not init_error:
        client._init_result = client.initialize()
    return client


def test_drive_auth_happy_path():
    client = _mock_client()
    steps = list(drive_auth("codex", client=client, vault=None, registry=None))
    assert len(steps) == 1
    assert isinstance(steps[0], Connected)
    assert steps[0].session_id == "sess_000"


def test_drive_auth_initialize_error():
    client = _mock_client(init_error=AcpError(-1, "command not found"))
    steps = list(drive_auth("codex", client=client, vault=None, registry=None))
    assert len(steps) == 1
    assert isinstance(steps[0], Failed)
    assert "command not found" in steps[0].reason


def test_drive_auth_session_auth_required_with_key():
    vault = MagicMock()
    vault.get_for_agent.return_value = "sk-abc123"
    config = AgentConfig(name="codex", transport=AgentTransport.LOCAL,
                         command="codex-acp", args=[], credentials_ref="OPENAI_API_KEY")
    registry = MagicMock()
    registry.get.return_value = config
    client = MagicMock()
    result = MagicMock()
    result.auth_methods = []
    client.initialize.return_value = result
    client._init_result = result
    # First new_session fails with AUTH_REQUIRED, second succeeds
    client.new_session.side_effect = [AcpError(-32000, "auth required"), "sess_retry"]
    steps = list(drive_auth("codex", client=client, vault=vault, registry=registry))
    assert len(steps) == 2
    assert isinstance(steps[0], Progress)
    assert isinstance(steps[1], Connected)
    assert steps[1].session_id == "sess_retry"
    assert client.new_session.call_count == 2


def test_drive_auth_auth_required_no_key_no_terminal():
    vault = MagicMock()
    vault.get_for_agent.side_effect = KeyError("not found")
    config = AgentConfig(name="codex", transport=AgentTransport.LOCAL,
                         command="codex-acp", args=[], credentials_ref="OPENAI_API_KEY")
    registry = MagicMock()
    registry.get.return_value = config
    client = MagicMock()
    result = MagicMock()
    result.auth_methods = []
    client.initialize.return_value = result
    client._init_result = result
    client.new_session.side_effect = AcpError(-32000, "auth required")
    steps = list(drive_auth("codex", client=client, vault=vault, registry=registry))
    assert len(steps) == 1
    assert isinstance(steps[0], Failed)


def test_drive_auth_auth_required_terminal_fallback():
    vault = MagicMock()
    vault.get_for_agent.side_effect = KeyError("not found")
    config = AgentConfig(name="claude-code", transport=AgentTransport.LOCAL,
                         command="claude-agent-acp", args=[])
    registry = MagicMock()
    registry.get.return_value = config
    client = MagicMock()
    result = MagicMock()
    result.auth_methods = []
    client.initialize.return_value = result
    client._init_result = result
    client.new_session.side_effect = AcpError(-32000, "auth required")
    steps = list(drive_auth("claude-code", client=client, vault=vault, registry=registry))
    assert len(steps) == 1
    assert isinstance(steps[0], NeedsTerminal)
    assert steps[0].command == "claude"
