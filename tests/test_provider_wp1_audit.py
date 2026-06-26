"""
WP-1 audit tests for aede/provider.py.

Covers findings from the holistic-audit judgment pass (2026-06-22):
  F1 — thinking_delta accumulation bug (issue #27)

All tests are hermetic — no network calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# F1 — thinking_delta must ACCUMULATE, not overwrite
# ---------------------------------------------------------------------------

class TestAnthropicThinkingAccumulation:
    """AnthropicProvider.stream_turn must concatenate thinking_delta chunks,
    not overwrite on each event (issue #27)."""

    @pytest.mark.asyncio
    async def test_multiple_thinking_deltas_all_forwarded_to_callback(self):
        """Each thinking_delta chunk must be forwarded independently to the
        stream_thinking callback.  If the accumulator assigns instead of
        appending only the LAST chunk would be forwarded."""
        from aede.provider import AnthropicProvider

        # Simulate two thinking-delta events followed by a text-delta
        def _make_event(etype, delta_type=None, delta_text=None, delta_thinking=None, cb_type=None):
            ev = MagicMock()
            ev.type = etype
            if delta_type is not None:
                delta = MagicMock()
                delta.type = delta_type
                if delta_text is not None:
                    delta.text = delta_text
                if delta_thinking is not None:
                    delta.thinking = delta_thinking
                ev.delta = delta
            if cb_type is not None:
                cb = MagicMock()
                cb.type = cb_type
                ev.content_block = cb
            return ev

        events = [
            _make_event("content_block_delta", delta_type="thinking_delta", delta_thinking="chunk A "),
            _make_event("content_block_delta", delta_type="thinking_delta", delta_thinking="chunk B"),
            _make_event("content_block_delta", delta_type="text_delta", delta_text="answer"),
        ]

        # Track what stream_thinking receives
        received_thinking: list[str] = []
        async def _capture_thinking(text: str) -> None:
            received_thinking.append(text)

        # Build a minimal fake Anthropic stream
        fake_usage = MagicMock()
        fake_usage.input_tokens = 10
        fake_usage.output_tokens = 5
        fake_usage.cache_read_input_tokens = 0

        fake_text_block = MagicMock()
        fake_text_block.type = "text"
        fake_text_block.text = "answer"

        fake_final = MagicMock()
        fake_final.content = [fake_text_block]
        fake_final.usage = fake_usage

        fake_stream = MagicMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=False)
        fake_stream.get_final_message = AsyncMock(return_value=fake_final)

        async def _async_events():
            for e in events:
                yield e

        fake_stream.__aiter__ = lambda self: _async_events()

        fake_client = MagicMock()
        fake_client.messages.stream = MagicMock(return_value=fake_stream)

        provider = AnthropicProvider(api_key="test-key")
        provider._client = fake_client

        received_text: list[str] = []
        async def _capture_text(text: str) -> None:
            received_text.append(text)

        resp = await provider.stream_turn(
            model="claude-sonnet-4-20250514",
            system="sys",
            tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000,
            console=MagicMock(),
            stream_thinking=_capture_thinking,
            stream_text=_capture_text,
        )

        # Both thinking chunks must have been forwarded
        assert received_thinking == ["chunk A ", "chunk B"], (
            "Both thinking_delta chunks must be forwarded; "
            f"got {received_thinking!r}"
        )
        # Text response must also be correct
        assert resp.text == "answer"

    @pytest.mark.asyncio
    async def test_thinking_accumulation_produces_full_text(self):
        """If the caller concatenates received thinking chunks, the result
        must equal the full thinking text emitted by the model."""
        from aede.provider import AnthropicProvider

        chunks = ["The answer", " is 42", " because math."]

        def _make_thinking_delta(text: str):
            ev = MagicMock()
            ev.type = "content_block_delta"
            delta = MagicMock()
            delta.type = "thinking_delta"
            delta.thinking = text
            ev.delta = delta
            return ev

        events = [_make_thinking_delta(c) for c in chunks]

        received_thinking: list[str] = []
        async def _capture_thinking(text: str) -> None:
            received_thinking.append(text)

        fake_usage = MagicMock()
        fake_usage.input_tokens = 10
        fake_usage.output_tokens = 5
        fake_usage.cache_read_input_tokens = 0

        fake_final = MagicMock()
        fake_final.content = []
        fake_final.usage = fake_usage

        fake_stream = MagicMock()
        fake_stream.__aenter__ = AsyncMock(return_value=fake_stream)
        fake_stream.__aexit__ = AsyncMock(return_value=False)
        fake_stream.get_final_message = AsyncMock(return_value=fake_final)

        async def _async_events():
            for e in events:
                yield e

        fake_stream.__aiter__ = lambda self: _async_events()

        fake_client = MagicMock()
        fake_client.messages.stream = MagicMock(return_value=fake_stream)

        provider = AnthropicProvider(api_key="test-key")
        provider._client = fake_client

        await provider.stream_turn(
            model="claude-sonnet-4-20250514",
            system="sys",
            tools=[],
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1000,
            console=MagicMock(),
            stream_thinking=_capture_thinking,
        )

        # If accumulation is done by the CALLER by concatenating what it
        # receives from the callback, the full text must be present.
        full = "".join(received_thinking)
        assert full == "The answer is 42 because math."
