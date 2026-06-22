# tests/test_acp_thinking_seq.py
"""The ACP on_update handler must assign interleaved seq values across thinking
runs and tool calls so the UI can reconstruct the execution timeline.

A continuous run of thinking chunks shares one seq; a tool call ends the run and
bumps the counter; the next thinking run gets a fresh, higher seq. This is what
splits an ACP turn's reasoning into multiple ordered blocks instead of one.
"""
import asyncio

from aede.provider import AcpProvider


def _drive(updates: list[dict]) -> tuple[list, list]:
    """Feed ACP session updates through a provider's on_update and collect the
    (text, seq) thinking calls and (call_id, seq) tool calls."""
    thinking: list[tuple[str, int]] = []
    tools: list[tuple[str, int]] = []

    async def stream_thinking(text: str, seq: int = 0):
        thinking.append((text, seq))

    async def stream_tool_call(call_id: str, name: str, args: dict, seq: int = 0):
        tools.append((call_id, seq))

    prov = AcpProvider(model="claude-code", acp_manager=None)
    prov._stream_thinking = stream_thinking
    prov._stream_tool_call = stream_tool_call

    on_update = prov._make_on_update()

    async def run():
        for u in updates:
            on_update(u)
        # on_update schedules via asyncio.ensure_future — let them run.
        await asyncio.sleep(0)

    asyncio.run(run())
    return thinking, tools


def _thought(text: str) -> dict:
    return {"sessionUpdate": "agent_thought_chunk", "content": {"text": text}}


def _tool(call_id: str) -> dict:
    return {"sessionUpdate": "tool_call", "toolCallId": call_id, "rawInput": {}}


def test_thinking_runs_get_distinct_seqs_across_tool_calls():
    thinking, tools = _drive([
        _thought("think A1"),
        _thought("think A2"),   # same run as A1 → same seq
        _tool("tc1"),           # ends run, bumps counter
        _thought("think B1"),   # new run → higher seq
        _tool("tc2"),
        _thought("think C1"),
    ])

    # Two chunks of the first run share one seq.
    assert thinking[0] == ("think A1", 0)
    assert thinking[1] == ("think A2", 0)
    # Tool call after the first run.
    assert tools[0][0] == "tc1"
    assert tools[0][1] == 1
    # Second thinking run gets a fresh, higher seq.
    assert thinking[2][0] == "think B1"
    assert thinking[2][1] == 2
    assert tools[1] == ("tc2", 3)
    # Third run, higher still.
    assert thinking[3][0] == "think C1"
    assert thinking[3][1] == 4


def test_seqs_are_strictly_increasing_per_block():
    thinking, tools = _drive([
        _thought("a"), _tool("t1"), _thought("b"), _tool("t2"),
    ])
    seqs = [s for _, s in thinking] + [s for _, s in tools]
    # Every block boundary advances the counter; no two blocks share a seq.
    block_seqs = sorted(set([thinking[0][1], tools[0][1], thinking[1][1], tools[1][1]]))
    assert block_seqs == [0, 1, 2, 3]
