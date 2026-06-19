"""
Tests for vision capability metadata and provider detection (T-002).
"""
from __future__ import annotations

import pytest


class TestVisionCapability:
    def test_known_anthropic_vision_model_returns_true(self):
        from aede.provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key", model_id="claude-sonnet-4-6")
        assert provider.has_vision() is True

    def test_known_openai_vision_model_returns_true(self):
        from aede.provider import OpenAIProvider
        provider = OpenAIProvider(api_key="test-key", base_url="https://api.openai.com", model_id="gpt-4o")
        assert provider.has_vision() is True

    def test_acp_provider_returns_true_always(self):
        from aede.provider import AcpProvider
        provider = AcpProvider(model="codex", acp_manager=None)
        assert provider.has_vision() is True

    def test_unknown_model_returns_false(self):
        from aede.provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key", model_id="claude-unknown-model")
        assert provider.has_vision() is False

    def test_default_sonnet_4_model_has_vision(self):
        from aede.provider import AnthropicProvider
        provider = AnthropicProvider(api_key="test-key", model_id="claude-sonnet-4-20250514")
        assert provider.has_vision() is True
