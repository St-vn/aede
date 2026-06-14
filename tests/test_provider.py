"""
Tests for aede/provider.py.

All tests are hermetic — no network calls. SDK clients are mocked.
"""
from __future__ import annotations

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(model: str, api_base_url: str | None = None) -> MagicMock:
    cfg = MagicMock()
    cfg.model = model
    cfg.api_base_url = api_base_url
    return cfg


# ---------------------------------------------------------------------------
# get_provider — factory logic
# ---------------------------------------------------------------------------

class TestGetProvider:
    def test_openai_provider_when_base_url_and_non_anthropic_model(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
        from aede.provider import get_provider, OpenAIProvider
        cfg = _make_cfg(model="google/gemini-2.5-flash", api_base_url="https://openrouter.ai/api/v1")
        provider = get_provider(cfg)
        assert isinstance(provider, OpenAIProvider)

    def test_anthropic_provider_for_claude_model_even_with_base_url(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from aede.provider import get_provider, AnthropicProvider
        cfg = _make_cfg(model="claude-sonnet-4-20250514", api_base_url="https://openrouter.ai/api/v1")
        provider = get_provider(cfg)
        assert isinstance(provider, AnthropicProvider)

    def test_anthropic_provider_for_anthropic_slash_prefix(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from aede.provider import get_provider, AnthropicProvider
        cfg = _make_cfg(model="anthropic/claude-opus-4", api_base_url="https://openrouter.ai/api/v1")
        provider = get_provider(cfg)
        assert isinstance(provider, AnthropicProvider)

    def test_anthropic_provider_when_no_base_url(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from aede.provider import get_provider, AnthropicProvider
        cfg = _make_cfg(model="google/gemini-2.5-flash", api_base_url=None)
        provider = get_provider(cfg)
        assert isinstance(provider, AnthropicProvider)

    def test_openai_provider_fallback_to_openai_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        from aede.provider import get_provider, OpenAIProvider
        cfg = _make_cfg(model="google/gemini-2.5-flash", api_base_url="https://openrouter.ai/api/v1")
        provider = get_provider(cfg)
        assert isinstance(provider, OpenAIProvider)

    def test_missing_openrouter_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from aede.provider import get_provider
        cfg = _make_cfg(model="google/gemini-2.5-flash", api_base_url="https://openrouter.ai/api/v1")
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            get_provider(cfg)

    def test_missing_anthropic_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from aede.provider import get_provider
        cfg = _make_cfg(model="claude-sonnet-4-20250514", api_base_url=None)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            get_provider(cfg)

    # -----------------------------------------------------------------------
    # P01-03, P01-04 — OpenCode Zen and Go providers
    # -----------------------------------------------------------------------

    def test_opencode_zen_routes_to_openai_compatible(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_ZEN_API_KEY", "zen-test-key")
        from aede.provider import get_provider, OpenAIProvider
        cfg = _make_cfg(model="deepseek-v4-flash-free")
        cfg.providers = {
            "opencode-zen": {
                "api_key_env": "OPENCODE_ZEN_API_KEY",
                "base_url": "https://opencode.ai/zen/v1",
            },
        }
        provider = get_provider(cfg)
        assert isinstance(provider, OpenAIProvider)
        assert provider._base_url == "https://opencode.ai/zen/v1"
        assert provider._api_key == "zen-test-key"

    def test_opencode_zen_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_ZEN_API_KEY", raising=False)
        from aede.provider import get_provider
        cfg = _make_cfg(model="deepseek-v4-flash-free")
        cfg.providers = {
            "opencode-zen": {
                "api_key_env": "OPENCODE_ZEN_API_KEY",
                "base_url": "https://opencode.ai/zen/v1",
            },
        }
        with pytest.raises(RuntimeError, match="OPENCODE_ZEN_API_KEY"):
            get_provider(cfg)

    def test_opencode_go_routes_to_openai_compatible(self, monkeypatch):
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "go-test-key")
        from aede.provider import get_provider, OpenAIProvider
        cfg = _make_cfg(model="deepseek-v4-pro")
        cfg.providers = {
            "opencode-go": {
                "api_key_env": "OPENCODE_GO_API_KEY",
                "base_url": "https://opencode.ai/zen/go",
            },
        }
        provider = get_provider(cfg)
        assert isinstance(provider, OpenAIProvider)
        assert provider._base_url == "https://opencode.ai/zen/go"
        assert provider._api_key == "go-test-key"

    def test_opencode_go_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        from aede.provider import get_provider
        cfg = _make_cfg(model="deepseek-v4-pro")
        cfg.providers = {
            "opencode-go": {
                "api_key_env": "OPENCODE_GO_API_KEY",
                "base_url": "https://opencode.ai/zen/go",
            },
        }
        with pytest.raises(RuntimeError, match="OPENCODE_GO_API_KEY"):
            get_provider(cfg)

    def test_opencode_zen_not_supported_model_goes_to_anthropic(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from aede.provider import get_provider, AnthropicProvider
        cfg = _make_cfg(model="claude-sonnet-4-20250514")
        cfg.providers = {
            "opencode-zen": {
                "api_key_env": "OPENCODE_ZEN_API_KEY",
                "base_url": "https://opencode.ai/zen/v1",
            },
        }
        provider = get_provider(cfg)
        assert isinstance(provider, AnthropicProvider)


# ---------------------------------------------------------------------------
# Message conversion: Anthropic → OpenAI
# ---------------------------------------------------------------------------

class TestConvertMessagesToOpenAI:
    def _convert(self, system: str, messages: list[dict]) -> list[dict]:
        from aede.provider import _convert_messages_to_openai
        return _convert_messages_to_openai(system, messages)

    def test_system_becomes_first_message(self):
        result = self._convert("You are helpful.", [])
        assert result[0] == {"role": "system", "content": "You are helpful."}

    def test_plain_user_string_passthrough(self):
        result = self._convert("sys", [{"role": "user", "content": "hello"}])
        assert result[1] == {"role": "user", "content": "hello"}

    def test_plain_assistant_string_passthrough(self):
        result = self._convert("sys", [{"role": "assistant", "content": "hi"}])
        assert result[1] == {"role": "assistant", "content": "hi"}

    def test_tool_result_user_block_becomes_role_tool(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-abc",
                        "content": "the result text",
                        "is_error": False,
                    }
                ],
            }
        ]
        result = self._convert("sys", messages)
        # system + tool message
        assert len(result) == 2
        tool_msg = result[1]
        assert tool_msg["role"] == "tool"
        assert tool_msg["tool_call_id"] == "tool-abc"
        assert tool_msg["content"] == "the result text"

    def test_assistant_with_tool_use_block_becomes_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call-xyz",
                        "name": "read_file",
                        "input": {"path": "/tmp/foo.txt"},
                    }
                ],
            }
        ]
        result = self._convert("sys", messages)
        assert len(result) == 2
        asst_msg = result[1]
        assert asst_msg["role"] == "assistant"
        assert "tool_calls" in asst_msg
        tc = asst_msg["tool_calls"][0]
        assert tc["id"] == "call-xyz"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "read_file"
        assert json.loads(tc["function"]["arguments"]) == {"path": "/tmp/foo.txt"}

    def test_assistant_with_text_and_tool_use(self):
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me read that file."},
                    {
                        "type": "tool_use",
                        "id": "call-123",
                        "name": "read_file",
                        "input": {"path": "/foo"},
                    },
                ],
            }
        ]
        result = self._convert("sys", messages)
        asst_msg = result[1]
        assert asst_msg["content"] == "Let me read that file."
        assert len(asst_msg["tool_calls"]) == 1

    def test_mixed_tool_result_and_text_in_user_content(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-1",
                        "content": "result1",
                        "is_error": False,
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-2",
                        "content": "result2",
                        "is_error": False,
                    },
                ],
            }
        ]
        result = self._convert("sys", messages)
        assert result[1]["role"] == "tool"
        assert result[1]["tool_call_id"] == "call-1"
        assert result[2]["role"] == "tool"
        assert result[2]["tool_call_id"] == "call-2"


# ---------------------------------------------------------------------------
# Tool schema conversion: Anthropic → OpenAI
# ---------------------------------------------------------------------------

class TestConvertToolsToOpenAI:
    def _convert(self, tools: list[dict]) -> list[dict]:
        from aede.provider import _convert_tools_to_openai
        return _convert_tools_to_openai(tools)

    def test_single_tool_conversion(self):
        tools = [
            {
                "name": "read_file",
                "description": "Read a file at the given path.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The file path."}
                    },
                    "required": ["path"],
                },
            }
        ]
        result = self._convert(tools)
        assert len(result) == 1
        oai = result[0]
        assert oai["type"] == "function"
        assert oai["function"]["name"] == "read_file"
        assert oai["function"]["description"] == "Read a file at the given path."
        assert oai["function"]["parameters"]["type"] == "object"
        assert "path" in oai["function"]["parameters"]["properties"]

    def test_multiple_tools(self):
        tools = [
            {"name": "tool_a", "description": "A", "input_schema": {"type": "object", "properties": {}}},
            {"name": "tool_b", "description": "B", "input_schema": {"type": "object", "properties": {}}},
        ]
        result = self._convert(tools)
        assert len(result) == 2
        assert result[0]["function"]["name"] == "tool_a"
        assert result[1]["function"]["name"] == "tool_b"

    def test_empty_tools(self):
        assert self._convert([]) == []


# ---------------------------------------------------------------------------
# AnthropicProvider stream_turn — mocked SDK
# ---------------------------------------------------------------------------

class TestAnthropicProviderStreamTurn:
    @pytest.mark.asyncio
    async def test_returns_normalized_response(self):
        from aede.provider import AnthropicProvider

        # Build a fake final message from the Anthropic SDK
        fake_text_block = MagicMock()
        fake_text_block.type = "text"
        fake_text_block.text = "Hello, world!"

        fake_tool_block = MagicMock()
        fake_tool_block.type = "tool_use"
        fake_tool_block.id = "tu-001"
        fake_tool_block.name = "read_file"
        fake_tool_block.input = {"path": "/foo"}

        fake_usage = MagicMock()
        fake_usage.input_tokens = 100
        fake_usage.output_tokens = 50
        fake_usage.cache_read_input_tokens = 10

        fake_final = MagicMock()
        fake_final.content = [fake_text_block, fake_tool_block]
        fake_final.usage = fake_usage

        # Fake async context manager for stream
        fake_stream = AsyncMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=False)

        async def _fake_text_stream():
            yield "Hello, "
            yield "world!"

        fake_stream.text_stream = _fake_text_stream()
        fake_stream.get_final_message = AsyncMock(return_value=fake_final)

        fake_client = MagicMock()
        fake_client.messages.stream = MagicMock(return_value=fake_stream)

        console = MagicMock()

        provider = AnthropicProvider(api_key="test-key")
        provider._client = fake_client  # inject mock

        resp = await provider.stream_turn(
            model="claude-sonnet-4-20250514",
            system="You are helpful.",
            tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000,
            console=console,
        )

        assert resp.text == "Hello, world!"
        assert resp.input_tokens == 100
        assert resp.output_tokens == 50
        assert resp.cached_tokens == 10
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["name"] == "read_file"
        assert resp.tool_calls[0]["id"] == "tu-001"
        assert resp.tool_calls[0]["input"] == {"path": "/foo"}
        # assistant_content_blocks should be the raw blocks
        assert resp.assistant_content_blocks == [fake_text_block, fake_tool_block]


# ---------------------------------------------------------------------------
# OpenAIProvider stream_turn — mocked SDK
# ---------------------------------------------------------------------------

class TestOpenAIProviderStreamTurn:
    def _make_chunk(
        self,
        content: str | None = None,
        tool_calls=None,
        usage=None,
    ) -> MagicMock:
        chunk = MagicMock()
        chunk.usage = usage

        delta = MagicMock()
        delta.content = content
        delta.tool_calls = tool_calls

        choice = MagicMock()
        choice.delta = delta

        chunk.choices = [choice]
        return chunk

    @pytest.mark.asyncio
    async def test_plain_text_response(self):
        from aede.provider import OpenAIProvider

        chunks = [
            self._make_chunk(content="Hello "),
            self._make_chunk(content="there!"),
            self._make_chunk(content=None, usage=MagicMock(
                prompt_tokens=80, completion_tokens=20, prompt_tokens_details=None
            )),
        ]
        chunks[-1].choices = []  # usage-only chunk has no choices

        async def _fake_stream():
            for c in chunks:
                yield c

        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

        console = MagicMock()
        provider = OpenAIProvider(api_key="or-key", base_url="https://openrouter.ai/api/v1")
        provider._client = fake_client

        resp = await provider.stream_turn(
            model="google/gemini-2.5-flash",
            system="sys",
            tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000,
            console=console,
        )

        assert resp.text == "Hello there!"
        assert resp.tool_calls == []
        assert resp.input_tokens == 80
        assert resp.output_tokens == 20
        assert resp.cached_tokens == 0

    @pytest.mark.asyncio
    async def test_tool_call_accumulation(self):
        from aede.provider import OpenAIProvider

        # Simulate fragmented tool_call deltas
        def _tc_delta(index, id=None, name=None, arguments=None):
            tc = MagicMock()
            tc.index = index
            tc.id = id
            tc.function = MagicMock()
            tc.function.name = name
            tc.function.arguments = arguments
            return tc

        chunk1 = self._make_chunk(content=None, tool_calls=[_tc_delta(0, id="tc-1", name="read_file", arguments='{"pa')])
        chunk2 = self._make_chunk(content=None, tool_calls=[_tc_delta(0, id=None, name=None, arguments='th": "/foo"}')])
        chunk3 = self._make_chunk(content=None)
        chunk3.choices = []  # final usage chunk

        async def _fake_stream():
            for c in [chunk1, chunk2, chunk3]:
                yield c

        fake_client = MagicMock()
        fake_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

        console = MagicMock()
        provider = OpenAIProvider(api_key="or-key", base_url="https://openrouter.ai/api/v1")
        provider._client = fake_client

        resp = await provider.stream_turn(
            model="google/gemini-2.5-flash",
            system="sys",
            tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000,
            console=console,
        )

        assert len(resp.tool_calls) == 1
        tc = resp.tool_calls[0]
        assert tc["id"] == "tc-1"
        assert tc["name"] == "read_file"
        assert tc["input"] == {"path": "/foo"}

        # assistant_content_blocks should have a tool_use dict
        tool_block = next(b for b in resp.assistant_content_blocks if b.get("type") == "tool_use")
        assert tool_block["name"] == "read_file"
        assert tool_block["id"] == "tc-1"


# ---------------------------------------------------------------------------
# _is_html_body helper (via agent module)
# ---------------------------------------------------------------------------

class TestIsHtmlBody:
    def test_detects_doctype(self):
        from aede.agent import _is_html_body
        assert _is_html_body("<!DOCTYPE html><html>...")

    def test_detects_html_tag(self):
        from aede.agent import _is_html_body
        assert _is_html_body("<html><head>...</head>")

    def test_detects_next_js_marker(self):
        from aede.agent import _is_html_body
        assert _is_html_body('self.__next_f.push([1,""])')

    def test_plain_error_not_html(self):
        from aede.agent import _is_html_body
        assert not _is_html_body("404 Not Found — resource missing")

    def test_empty_string(self):
        from aede.agent import _is_html_body
        assert not _is_html_body("")
