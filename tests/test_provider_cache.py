"""
Tests for cache_control breakpoints in AnthropicProvider and OpenAIProvider.
RED tests for cache_control bug fix (phase2-tasks-bug-cache-control.md, Tasks 5-8).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_system_prompt(stable: str = "stable content", dynamic: str = "dynamic content"):
    """Create a SystemPrompt dataclass for testing."""
    from aede.agent import SystemPrompt
    return SystemPrompt(stable=stable, dynamic=dynamic)


# ---------------------------------------------------------------------------
# Task 5/6 — AnthropicProvider: system param has cache_control breakpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_system_param_has_cache_breakpoint():
    """
    AnthropicProvider.stream_turn must pass system as a 2-element list where:
    - Block 0: {type: text, text: sp.stable, cache_control: {type: ephemeral}}
    - Block 1: {type: text, text: sp.dynamic}  (no cache_control)
    """
    from aede.provider import AnthropicProvider

    sp = _make_system_prompt(stable="STABLE PART", dynamic="DYNAMIC PART")

    captured: dict = {}

    # Build a fake streaming context manager
    fake_message = MagicMock()
    fake_message.usage = MagicMock(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=0
    )
    fake_message.content = []

    async def fake_text_stream():
        return
        yield  # make it an async generator

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
        system=sp,
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        console=console,
    )

    system_kwarg = captured.get("system")
    assert isinstance(system_kwarg, list), f"system must be a list, got {type(system_kwarg)}"
    assert len(system_kwarg) == 2, f"system must have 2 blocks, got {len(system_kwarg)}"

    block0 = system_kwarg[0]
    assert block0["type"] == "text"
    assert block0["text"] == "STABLE PART"
    assert block0.get("cache_control") == {"type": "ephemeral"}, (
        f"Block 0 must have cache_control ephemeral, got {block0.get('cache_control')}"
    )

    block1 = system_kwarg[1]
    assert block1["type"] == "text"
    assert block1["text"] == "DYNAMIC PART"
    assert "cache_control" not in block1, (
        f"Block 1 must NOT have cache_control, got {block1.get('cache_control')}"
    )


# ---------------------------------------------------------------------------
# Task 7/8 — last message gets cache_control; original messages unmodified
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_last_message_cache_breakpoint():
    """
    AnthropicProvider must inject cache_control on the last content block of the
    last message in the API call. The original messages list must be unmodified.
    """
    from aede.provider import AnthropicProvider

    sp = _make_system_prompt()
    original_messages = [
        {"role": "user", "content": "first message"},
        {"role": "assistant", "content": "assistant reply"},
        {"role": "user", "content": "second message"},
    ]
    # Keep a deep copy to check immutability
    import copy
    original_snapshot = copy.deepcopy(original_messages)

    captured: dict = {}

    fake_message = MagicMock()
    fake_message.usage = MagicMock(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=3
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
        system=sp,
        tools=[],
        messages=original_messages,
        max_tokens=100,
        console=console,
    )

    sent_messages = captured.get("messages", [])

    # The last message's content must carry cache_control
    last_msg = sent_messages[-1]
    last_content = last_msg["content"]

    # Content may be a string or a list of blocks after our injection
    if isinstance(last_content, str):
        # We need the provider to have converted it to a block list with cache_control
        pytest.fail(
            "Expected last message content to be a list of blocks with cache_control, got plain string"
        )

    assert isinstance(last_content, list), f"Expected list of blocks, got {type(last_content)}"
    last_block = last_content[-1]
    assert last_block.get("cache_control") == {"type": "ephemeral"}, (
        f"Last block must carry cache_control ephemeral, got {last_block.get('cache_control')}"
    )

    # CRITICAL: Original messages must be unmodified
    assert original_messages == original_snapshot, (
        "Original messages list was mutated by stream_turn!"
    )


# ---------------------------------------------------------------------------
# Task 6 (OpenAI) — OpenAIProvider gracefully flattens SystemPrompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_provider_accepts_system_prompt():
    """
    OpenAIProvider.stream_turn must accept a SystemPrompt dataclass and
    concatenate stable + dynamic as its system string (no cache_control).
    Must not raise and must pass a proper system string to the OAI API.
    """
    from aede.provider import OpenAIProvider

    sp = _make_system_prompt(stable="STABLE", dynamic="DYNAMIC")

    captured_messages: list = []

    async def fake_stream_iter():
        # Yield one empty chunk then finish
        chunk = MagicMock()
        chunk.usage = None
        chunk.choices = []
        yield chunk

    fake_completion = MagicMock()
    fake_completion.__aiter__ = lambda self: fake_stream_iter()

    fake_client = MagicMock()
    async def fake_create(**kwargs):
        # Capture the system message from oai_messages
        captured_messages.extend(kwargs.get("messages", []))
        return fake_completion

    fake_client.chat.completions.create = AsyncMock(side_effect=fake_create)

    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider._api_key = "test"
    provider._base_url = "https://example.com"
    provider._client = fake_client

    console = MagicMock()
    console.print = MagicMock()

    # Must not raise even though system is a SystemPrompt, not a str
    result = await provider.stream_turn(
        model="gpt-test",
        system=sp,
        tools=[],
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        console=console,
    )

    # The OAI system message content must be the concatenation
    sys_msgs = [m for m in captured_messages if m.get("role") == "system"]
    assert len(sys_msgs) == 1
    sys_content = sys_msgs[0]["content"]
    assert "STABLE" in sys_content
    assert "DYNAMIC" in sys_content
