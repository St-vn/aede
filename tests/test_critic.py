"""
Tests for aede/critic.py — BC-03.

All tests must pass WITHOUT hitting a real LLM API.
"""
from __future__ import annotations

import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# BC-03 helpers
# ---------------------------------------------------------------------------

def _make_cfg(*, model="claude-sonnet-4-20250514", api_base_url=None, critic_model=None, critic_api_base_url=None):
    cfg = MagicMock()
    cfg.model = model
    cfg.api_base_url = api_base_url
    cfg.critic_model = critic_model
    cfg.critic_api_base_url = critic_api_base_url
    return cfg


# ---------------------------------------------------------------------------
# BC-03 tests
# ---------------------------------------------------------------------------

def test_critic_finding_struct():
    """CriticFinding must have at least severity and message fields."""
    from aede.critic import CriticFinding
    f = CriticFinding(severity="HIGH", message="logic bug: off-by-one")
    assert f.severity == "HIGH"
    assert f.message == "logic bug: off-by-one"


def test_critic_provider_fallback():
    """When critic_model is None, get_critic_provider uses cfg.model (same-model fallback)."""
    from aede.critic import get_critic_provider
    from aede.provider import AnthropicProvider

    cfg = _make_cfg(model="claude-sonnet-4-20250514", critic_model=None, critic_api_base_url=None)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        provider = get_critic_provider(cfg)

    assert isinstance(provider, AnthropicProvider)


def test_critic_provider_custom_model():
    """When critic_model is set (Anthropic model), get_critic_provider builds an AnthropicProvider."""
    from aede.critic import get_critic_provider
    from aede.provider import AnthropicProvider

    cfg = _make_cfg(
        model="claude-sonnet-4-20250514",
        critic_model="claude-haiku-4-20250514",
        critic_api_base_url=None,
    )

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        provider = get_critic_provider(cfg)

    assert isinstance(provider, AnthropicProvider)


def test_critic_provider_openrouter_model():
    """When critic_model + critic_api_base_url are set for a non-Anthropic model, returns OpenAIProvider."""
    from aede.critic import get_critic_provider
    from aede.provider import OpenAIProvider

    cfg = _make_cfg(
        model="claude-sonnet-4-20250514",
        critic_model="google/gemini-2.5-flash",
        critic_api_base_url="https://openrouter.ai/api/v1",
    )

    with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-or-key"}):
        provider = get_critic_provider(cfg)

    assert isinstance(provider, OpenAIProvider)


def test_critic_system_prompt_exists():
    """CRITIC_SYSTEM_PROMPT must be a non-empty string."""
    from aede.critic import CRITIC_SYSTEM_PROMPT
    assert isinstance(CRITIC_SYSTEM_PROMPT, str)
    assert len(CRITIC_SYSTEM_PROMPT) > 50


@pytest.mark.asyncio
async def test_evaluate_returns_list_of_findings():
    """evaluate() must return a list (possibly empty) of CriticFinding instances."""
    from aede.critic import evaluate, CriticFinding

    cfg = _make_cfg()

    # Mock provider stream_turn to return JSON findings
    mock_provider = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '[{"severity": "HIGH", "message": "null pointer dereference"}]'
    mock_provider.stream_turn = AsyncMock(return_value=mock_resp)

    with patch("aede.critic.get_critic_provider", return_value=mock_provider):
        findings = await evaluate(cfg, code="def foo():\n    return None.x", task_context="test task")

    assert isinstance(findings, list)
    assert len(findings) == 1
    assert findings[0].severity == "HIGH"
    assert "null pointer" in findings[0].message


@pytest.mark.asyncio
async def test_evaluate_returns_empty_on_no_findings():
    """evaluate() must return empty list when model reports no issues."""
    from aede.critic import evaluate

    cfg = _make_cfg()
    mock_provider = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "[]"
    mock_provider.stream_turn = AsyncMock(return_value=mock_resp)

    with patch("aede.critic.get_critic_provider", return_value=mock_provider):
        findings = await evaluate(cfg, code="x = 1", task_context="task")

    assert findings == []


@pytest.mark.asyncio
async def test_evaluate_handles_malformed_json():
    """evaluate() must not crash if the model returns non-JSON; returns empty list."""
    from aede.critic import evaluate

    cfg = _make_cfg()
    mock_provider = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Sorry, I cannot evaluate this."
    mock_provider.stream_turn = AsyncMock(return_value=mock_resp)

    with patch("aede.critic.get_critic_provider", return_value=mock_provider):
        findings = await evaluate(cfg, code="x = 1", task_context="task")

    assert isinstance(findings, list)
