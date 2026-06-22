"""
Tests for image content block handling across all three providers.

Covers T-004: Provider image content block handling.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_system_prompt(stable: str = "stable", dynamic: str = "dynamic"):
    from aede.agent import SystemPrompt
    return SystemPrompt(stable=stable, dynamic=dynamic)


# ---------------------------------------------------------------------------
# 1. Anthropic message with image block passes through unchanged
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anthropic_image_block_passthrough():
    """
    When the last message content is a list containing an image block,
    cache_control must be injected at the block level (not inside source),
    and the image block's type/source fields must remain intact.
    """
    from aede.provider import AnthropicProvider

    image_source = {
        "type": "base64",
        "media_type": "image/png",
        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk",
    }

    messages = [
        {"role": "user", "content": "Look at this photo:"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What do you see?"},
                {"type": "image", "source": image_source},
            ],
        },
    ]

    captured: dict = {}

    fake_message = MagicMock()
    fake_message.usage = MagicMock(
        input_tokens=15, output_tokens=8, cache_read_input_tokens=0
    )
    fake_message.content = []

    async def fake_text_stream():
        return
        yield

    fake_stream = MagicMock()
    fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
    fake_stream.__aexit__ = AsyncMock(return_value=None)
    fake_stream.text_stream = fake_text_stream()
    fake_stream.get_final_message = AsyncMock(return_value=fake_message)

    fake_client = MagicMock()
    def capture_stream(**kwargs):
        captured.update(kwargs)
        return fake_stream
    fake_client.messages.stream = capture_stream

    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider._api_key = "test"
    provider._client = fake_client

    console = MagicMock()
    console.print = MagicMock()

    await provider.stream_turn(
        model="claude-test",
        system="You are helpful.",
        tools=[],
        messages=messages,
        max_tokens=100,
        console=console,
    )

    sent_messages = captured.get("messages", [])
    # last message should be the one with the image block
    last_msg = sent_messages[-1]
    last_content = last_msg["content"]

    # The second message (with list content) gets cache_control injected on last block
    assert isinstance(last_content, list)
    assert len(last_content) == 2

    text_block = last_content[0]
    assert text_block["type"] == "text"
    assert text_block["text"] == "What do you see?"
    assert "cache_control" not in text_block

    image_block = last_content[1]
    assert image_block["type"] == "image"
    assert image_block["source"] == image_source
    assert image_block.get("cache_control") == {"type": "ephemeral"}
    assert "cache_control" not in image_block.get("source", {}), (
        "cache_control must not leak into image source"
    )


# ---------------------------------------------------------------------------
# 2. OpenAI conversion produces correct image_url block
# ---------------------------------------------------------------------------

class TestOpenAIImageConversion:
    def _convert(self, system: str, messages: list[dict]) -> list[dict]:
        from aede.provider import _convert_messages_to_openai
        return _convert_messages_to_openai(system, messages)

    def test_single_image_block(self):
        image_source = {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "abc123base64data",
        }
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": image_source},
                ],
            }
        ]
        result = self._convert("sys", messages)

        # system + user
        assert len(result) == 2
        user_msg = result[1]
        assert user_msg["role"] == "user"
        assert isinstance(user_msg["content"], list)
        assert user_msg["content"][0]["type"] == "image_url"
        assert user_msg["content"][0]["image_url"]["url"] == "data:image/jpeg;base64,abc123base64data"
        assert user_msg["content"][0]["image_url"]["detail"] == "auto"

    def test_single_image_defaults_to_png(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"data": "AAAA"}},
                ],
            }
        ]
        result = self._convert("sys", messages)
        url = result[1]["content"][0]["image_url"]["url"]
        assert url == "data:image/png;base64,AAAA"

    def test_text_and_image_interleaved(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Compare these:"},
                    {"type": "image", "source": {"media_type": "image/png", "data": "img1"}},
                    {"type": "text", "text": "vs this:"},
                    {"type": "image", "source": {"media_type": "image/png", "data": "img2"}},
                ],
            }
        ]
        result = self._convert("sys", messages)

        # Expect: system, user(text "Compare these:"), user(image img1),
        #         user(text "vs this:"), user(image img2)
        assert len(result) == 5
        assert result[1] == {"role": "user", "content": "Compare these:"}
        assert result[2]["role"] == "user"
        assert result[2]["content"][0]["type"] == "image_url"
        assert "img1" in result[2]["content"][0]["image_url"]["url"]
        assert result[3] == {"role": "user", "content": "vs this:"}
        assert result[4]["role"] == "user"
        assert result[4]["content"][0]["type"] == "image_url"
        assert "img2" in result[4]["content"][0]["image_url"]["url"]

    def test_multiple_images_in_one_message(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"media_type": "image/png", "data": "a"}},
                    {"type": "image", "source": {"media_type": "image/png", "data": "b"}},
                    {"type": "image", "source": {"media_type": "image/png", "data": "c"}},
                ],
            }
        ]
        result = self._convert("sys", messages)

        # Each image becomes its own user message with image_url content list
        assert len(result) == 4  # system + 3 image messages
        for i in range(1, 4):
            assert result[i]["role"] == "user"
            assert result[i]["content"][0]["type"] == "image_url"

    def test_image_with_tool_result(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-1",
                        "content": "result1",
                    },
                    {"type": "image", "source": {"media_type": "image/png", "data": "zzz"}},
                ],
            }
        ]
        result = self._convert("sys", messages)

        # system + tool + user(image)
        assert len(result) == 3
        assert result[1]["role"] == "tool"
        assert result[1]["tool_call_id"] == "call-1"
        assert result[2]["role"] == "user"
        assert result[2]["content"][0]["type"] == "image_url"


# ---------------------------------------------------------------------------
# 3. ACP prompt_text produces [Image attached] for image blocks
# ---------------------------------------------------------------------------

class TestAcpImageBuildPromptText:
    def test_image_block_emits_placeholder(self):
        from aede.provider import _build_prompt_text

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this:"},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"},
                    },
                ],
            }
        ]

        text = _build_prompt_text(messages)
        assert "[Image attached]" in text
        assert "Describe this:" in text
        assert "[user]" in text

    def test_multiple_images_in_one_message(self):
        from aede.provider import _build_prompt_text

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"data": "a"}},
                    {"type": "image", "source": {"data": "b"}},
                    {"type": "image", "source": {"data": "c"}},
                ],
            }
        ]

        text = _build_prompt_text(messages)
        assert text.count("[Image attached]") == 3

    def test_mixed_text_image_tool_result(self):
        from aede.provider import _build_prompt_text

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Before"},
                    {"type": "image", "source": {"data": "img"}},
                    {"type": "text", "text": "Middle"},
                    {"type": "tool_result", "content": "tool output"},
                    {"type": "image", "source": {"data": "img2"}},
                    {"type": "text", "text": "After"},
                ],
            }
        ]

        text = _build_prompt_text(messages)
        assert text.count("[Image attached]") == 2
        assert "Before" in text
        assert "Middle" in text
        assert "After" in text
        assert "[tool result]: tool output" in text


# ---------------------------------------------------------------------------
# 4. String-only messages are unchanged in all providers / conversions
# ---------------------------------------------------------------------------

class TestStringOnlyMessagesUnchanged:
    def test_convert_to_openai_string_only(self):
        from aede.provider import _convert_messages_to_openai

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "user", "content": "how are you?"},
        ]
        result = _convert_messages_to_openai("sys", messages)
        assert len(result) == 4  # system + 3
        assert result[1] == {"role": "user", "content": "hello"}
        assert result[2] == {"role": "assistant", "content": "hi there"}
        assert result[3] == {"role": "user", "content": "how are you?"}

    def test_build_prompt_text_string_only(self):
        from aede.provider import _build_prompt_text

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        text = _build_prompt_text(messages)
        assert text == "[user]: hello\n[assistant]: hi"

    @pytest.mark.asyncio
    async def test_anthropic_string_only_still_gets_cache_control(self):
        from aede.provider import AnthropicProvider

        captured: dict = {}

        fake_message = MagicMock()
        fake_message.usage = MagicMock(
            input_tokens=10, output_tokens=5, cache_read_input_tokens=0
        )
        fake_message.content = []

        async def fake_text_stream():
            return
            yield

        fake_stream = MagicMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=None)
        fake_stream.text_stream = fake_text_stream()
        fake_stream.get_final_message = AsyncMock(return_value=fake_message)

        fake_client = MagicMock()
        def capture_stream(**kwargs):
            captured.update(kwargs)
            return fake_stream
        fake_client.messages.stream = capture_stream

        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider._api_key = "test"
        provider._client = fake_client

        console = MagicMock()
        console.print = MagicMock()

        await provider.stream_turn(
            model="claude-test",
            system="sys",
            tools=[],
            messages=[{"role": "user", "content": "plain string"}],
            max_tokens=100,
            console=console,
        )

        sent = captured.get("messages", [])
        last_content = sent[-1]["content"]
        assert isinstance(last_content, list)
        assert last_content[-1].get("cache_control") == {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# 5. Cache control is added to last block of list correctly in Anthropic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_control_on_last_block_of_list():
    """
    When content is a list of blocks (text + image), cache_control must appear
    only on the very last block, at the block level.
    """
    from aede.provider import AnthropicProvider

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Text first"},
                {"type": "image", "source": {"media_type": "image/png", "data": "AAAA"}},
                {"type": "text", "text": "Text last"},
            ],
        },
    ]

    captured: dict = {}

    fake_message = MagicMock()
    fake_message.usage = MagicMock(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=0
    )
    fake_message.content = []

    async def fake_text_stream():
        return
        yield

    fake_stream = MagicMock()
    fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
    fake_stream.__aexit__ = AsyncMock(return_value=None)
    fake_stream.text_stream = fake_text_stream()
    fake_stream.get_final_message = AsyncMock(return_value=fake_message)

    fake_client = MagicMock()
    def capture_stream(**kwargs):
        captured.update(kwargs)
        return fake_stream
    fake_client.messages.stream = capture_stream

    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider._api_key = "test"
    provider._client = fake_client

    console = MagicMock()
    console.print = MagicMock()

    await provider.stream_turn(
        model="claude-test",
        system="sys",
        tools=[],
        messages=messages,
        max_tokens=100,
        console=console,
    )

    sent = captured.get("messages", [])
    blocks = sent[-1]["content"]

    assert len(blocks) == 3
    # First two blocks must NOT have cache_control
    assert "cache_control" not in blocks[0]
    assert "cache_control" not in blocks[1]
    # Last block must have cache_control at block level
    assert blocks[2].get("cache_control") == {"type": "ephemeral"}
    assert blocks[2]["type"] == "text"

    # Original messages unmodified
    original_last_content = messages[0]["content"]
    for block in original_last_content:
        assert "cache_control" not in block, "Original messages were mutated!"


@pytest.mark.asyncio
async def test_cache_control_on_image_as_last_block():
    """
    When the last block is an image, cache_control goes at block level,
    not inside the source dict.
    """
    from aede.provider import AnthropicProvider

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Look at this"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "ZZZZ"}},
            ],
        },
    ]

    captured: dict = {}

    fake_message = MagicMock()
    fake_message.usage = MagicMock(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=0
    )
    fake_message.content = []

    async def fake_text_stream():
        return
        yield

    fake_stream = MagicMock()
    fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
    fake_stream.__aexit__ = AsyncMock(return_value=None)
    fake_stream.text_stream = fake_text_stream()
    fake_stream.get_final_message = AsyncMock(return_value=fake_message)

    fake_client = MagicMock()
    def capture_stream(**kwargs):
        captured.update(kwargs)
        return fake_stream
    fake_client.messages.stream = capture_stream

    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider._api_key = "test"
    provider._client = fake_client

    console = MagicMock()
    console.print = MagicMock()

    await provider.stream_turn(
        model="claude-test",
        system="sys",
        tools=[],
        messages=messages,
        max_tokens=100,
        console=console,
    )

    sent = captured.get("messages", [])
    blocks = sent[-1]["content"]

    text_block = blocks[0]
    image_block = blocks[1]

    assert text_block["type"] == "text"
    assert "cache_control" not in text_block

    assert image_block["type"] == "image"
    assert image_block.get("cache_control") == {"type": "ephemeral"}
    assert "cache_control" not in image_block.get("source", {}), (
        "cache_control must NOT appear inside image source dict"
    )


# ---------------------------------------------------------------------------
# 6. Tool result content with list of blocks (image mixed) — OpenAI
# ---------------------------------------------------------------------------

def test_tool_result_content_as_list_of_blocks_unchanged():
    """
    Tool result content can be a list of text blocks. This path must not
    interfere with image handling.
    """
    from aede.provider import _convert_messages_to_openai

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call-a",
                    "content": [
                        {"type": "text", "text": "result line 1"},
                        {"type": "text", "text": "result line 2"},
                    ],
                },
            ],
        }
    ]
    result = _convert_messages_to_openai("sys", messages)
    assert result[1]["role"] == "tool"
    assert result[1]["content"] == "result line 1result line 2"
