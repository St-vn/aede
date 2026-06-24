"""Tests for aede.mcp.client — env isolation, secret leakage, var expansion."""
from __future__ import annotations

import pytest

from aede.mcp.client import MCPServerConfig, _build_mcp_env, expand_env_vars


class TestEnvIsolation:
    """CWE-532: parent env must NOT leak into MCP subprocesses."""

    def test_secrets_not_in_built_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set os.environ["FAKE_SECRET_KEY"]="leak", build MCPServerConfig
        env={"X":"1"}, call _build_mcp_env, assert FAKE_SECRET_KEY
        not in built_env and PATH is in built_env."""
        monkeypatch.setenv("FAKE_SECRET_KEY", "leak")
        cfg = MCPServerConfig(env={"X": "1"})
        built_env = _build_mcp_env(cfg)
        assert "FAKE_SECRET_KEY" not in built_env
        assert "PATH" in built_env or "Path" in built_env

    def test_expand_env_vars_rejects_secrets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """expand_env_vars("${FAKE_SECRET_KEY}") must NOT return the secret."""
        monkeypatch.setenv("FAKE_SECRET_KEY", "exposed-value")
        with pytest.raises(ValueError, match="FAKE_SECRET_KEY"):
            expand_env_vars("${FAKE_SECRET_KEY}")


class TestExpandEnvVars:
    """expand_env_vars behaviour for non-secret vars."""

    def test_expand_normal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_VAR", "hello")
        assert expand_env_vars("${MY_VAR}") == "hello"

    def test_expand_with_default(self) -> None:
        assert expand_env_vars("${UNDEFINED:-fallback}") == "fallback"

    def test_expand_missing_no_default_raises(self) -> None:
        with pytest.raises(KeyError):
            expand_env_vars("${DEFINITELY_NOT_SET}")

    def test_expand_secret_patterns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "MY_API_KEY",
            "MY_TOKEN",
            "MY_SECRET",
            "PASSWORD",
            "DB_PASSWORD",
        ):
            monkeypatch.setenv(name, "exposed")
            with pytest.raises(ValueError, match=name):
                expand_env_vars(f"${{{name}}}")


class TestBuildMcpEnv:
    """_build_mcp_env helper behaviour."""

    def test_none_env_returns_none(self) -> None:
        assert _build_mcp_env(MCPServerConfig(env=None)) is None

    def test_empty_env_uses_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAKE_SECRET_KEY", "leak")
        built_env = _build_mcp_env(MCPServerConfig(env={}))
        assert "FAKE_SECRET_KEY" not in built_env
        assert built_env is not None
        assert "X" not in built_env

    def test_cfg_env_overlaid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FAKE_SECRET_KEY", "leak")
        built_env = _build_mcp_env(MCPServerConfig(env={"X": "1", "Y": "2"}))
        assert built_env is not None
        assert built_env.get("X") == "1"
        assert built_env.get("Y") == "2"
        assert "FAKE_SECRET_KEY" not in built_env
