"""Tests for gate REDIRECT/BATCH_DENY message ordering.

DeepSeek (and any OpenAI-compatible provider with strict tool-call
validation) requires that an assistant message containing ``tool_calls``
is followed IMMEDIATELY by ``role: tool`` messages — one for each
``tool_call_id``.  A plain user message between the assistant and the
tool messages causes:

    Error from provider (DeepSeek): An assistant message with
    'tool_calls' must be followed by tool messages responding to each
    'tool_call_id'.

The bug: prior to the fix, when the gate returned REDIRECT or
BATCH_DENY with a non-empty ``redirect_msg``, the agent loop appended
the redirect text as a standalone ``role: user`` message AND appended
the tool_results as a separate ``role: user`` message whose content
was a list of ``tool_result`` blocks.  In the Anthropic → OpenAI
conversion, that produced:

    [assistant(tool_calls), user(redirect_text), tool(tool_call_id), ...]

The fix embeds the redirect text as a ``type: text`` block INSIDE the
same user message that holds the tool_results, so the conversion
produces the correct order:

    [assistant(tool_calls), tool(tool_call_id), user(redirect_text), ...]
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def _make_agent_loop(batch_approval_max: int = 5):
    from aede.agent import AgentLoop
    from aede.config import AedeConfig
    from aede.gate import PermissionMode, PermissionStore, TerminalGateBackend
    from pathlib import Path

    cfg = AedeConfig(
        {
            "model": "deepseek-chat",
            "shell": "powershell",
            "tool_output_max_tokens": 8000,
            "context_window": 200000,
            "compaction_threshold": 0.85,
            "batch_approval_max": batch_approval_max,
        },
        home=Path("/tmp"),
    )
    loop = AgentLoop.__new__(AgentLoop)
    loop._cfg = cfg
    loop._session = MagicMock(id="SID")
    loop._db = MagicMock()
    loop._rollout = MagicMock()
    loop._console = MagicMock()
    loop._project_dir = Path("/tmp")
    loop._messages = []
    loop._turn = 0
    loop._provider = MagicMock()
    loop._system_prompt = ""
    loop._stream_text = None
    loop._stream_thinking = None
    loop._accumulated_thinking = ""
    loop._mode = PermissionMode.NORMAL
    loop._gate_store = PermissionStore(project_dir=loop._project_dir)
    loop._tracker = MagicMock()
    loop._tracker.record = MagicMock()
    loop._gate_backend = TerminalGateBackend(
        store=loop._db,
        project_dir=loop._project_dir,
        global_config_path=loop._cfg.home / "config.yml",
        console=loop._console,
    )
    # Intent-alignment / token-cadence re-injection state (set in __init__,
    # which __new__ bypasses).
    loop._tokens_since_last_reminder = 0
    loop._current_objective = ""
    loop._active_constraints = ""
    loop._open_decisions = ""
    return loop


def _make_response(tool_calls):
    resp = MagicMock()
    resp.text = ""
    resp.tool_calls = tool_calls
    resp.assistant_content_blocks = [
        {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
        for tc in tool_calls
    ]
    resp.input_tokens = 10
    resp.output_tokens = 5
    resp.cached_tokens = 0
    return resp


def _find_index(messages, predicate):
    for i, m in enumerate(messages):
        if predicate(m):
            return i
    return -1


@pytest.mark.asyncio
async def test_redirect_message_does_not_break_tool_order():
    """REDIRECT must not insert a standalone user message between the
    assistant's tool_use and the corresponding tool_result.  DeepSeek
    rejects that order with: 'An assistant message with tool_calls must
    be followed by tool messages responding to each tool_call_id'.
    """
    from aede.gate import GateDecision

    loop = _make_agent_loop(batch_approval_max=5)
    tool_calls = [{"id": "tc1", "name": "write_file", "input": {"path": "/x", "content": "y"}}]
    redirect_msg = "please use a different path"

    resp_tools = _make_response(tool_calls)
    resp_done = _make_response([])
    resp_done.text = "ok"
    n = {"v": 0}

    async def fake_stream(*a, **kw):
        n["v"] += 1
        return resp_tools if n["v"] == 1 else resp_done

    loop._stream_response = fake_stream

    router = MagicMock()
    router.validate_name = MagicMock()
    router.requires_approval = MagicMock(return_value=True)
    router.execute_sync = MagicMock()
    loop._router = router

    gate_store = MagicMock()
    gate_store.is_allowed = MagicMock(return_value=False)
    loop._gate_store = gate_store

    async def no_compact():
        pass
    loop._maybe_compact = no_compact

    async def fake_request(*a, **kw):
        return GateDecision.REDIRECT, redirect_msg

    loop._gate_backend.request = fake_request

    with patch("aede.gate.prompt_gate", new=AsyncMock(return_value=(GateDecision.REDIRECT, redirect_msg))):
        await loop.run_turn("do it")

    messages = loop._messages

    asst_idx = _find_index(
        messages,
        lambda m: m.get("role") == "assistant" and isinstance(m.get("content"), list)
        and any(b.get("type") == "tool_use" for b in m["content"]),
    )
    assert asst_idx >= 0, f"no assistant tool_use message found: {messages!r}"

    user_idx = _find_index(
        messages,
        lambda m: m.get("role") == "user" and isinstance(m.get("content"), list)
        and any(b.get("type") == "tool_result" for b in m["content"]),
    )
    assert user_idx > asst_idx, (
        f"expected user(tool_results) AFTER assistant(tool_use); got "
        f"asst_idx={asst_idx}, user_idx={user_idx}, messages={messages!r}"
    )

    for i in range(asst_idx + 1, user_idx):
        m = messages[i]
        if m.get("role") == "user":
            assert not (isinstance(m.get("content"), str) and m["content"]), (
                f"standalone user message found at index {i} between "
                f"assistant tool_use (idx {asst_idx}) and user tool_results "
                f"(idx {user_idx}); this breaks DeepSeek/OpenAI tool_call "
                f"ordering. messages={messages!r}"
            )


@pytest.mark.asyncio
async def test_redirect_message_embedded_in_tool_results_user_message():
    """The redirect text must end up embedded in the SAME user message
    that holds the tool_result blocks (as a 'text' block), not in a
    separate user message.
    """
    from aede.gate import GateDecision

    loop = _make_agent_loop(batch_approval_max=5)
    tool_calls = [{"id": "tc1", "name": "write_file", "input": {"path": "/x", "content": "y"}}]
    redirect_msg = "use path /tmp instead"

    resp_tools = _make_response(tool_calls)
    resp_done = _make_response([])
    resp_done.text = "ok"
    n = {"v": 0}

    async def fake_stream(*a, **kw):
        n["v"] += 1
        return resp_tools if n["v"] == 1 else resp_done

    loop._stream_response = fake_stream

    router = MagicMock()
    router.validate_name = MagicMock()
    router.requires_approval = MagicMock(return_value=True)
    router.execute_sync = MagicMock()
    loop._router = router

    gate_store = MagicMock()
    gate_store.is_allowed = MagicMock(return_value=False)
    loop._gate_store = gate_store

    async def no_compact():
        pass
    loop._maybe_compact = no_compact

    async def fake_request(*a, **kw):
        return GateDecision.REDIRECT, redirect_msg

    loop._gate_backend.request = fake_request

    with patch("aede.gate.prompt_gate", new=AsyncMock(return_value=(GateDecision.REDIRECT, redirect_msg))):
        await loop.run_turn("do it")

    tool_result_user = next(
        (m for m in loop._messages
         if m.get("role") == "user"
         and isinstance(m.get("content"), list)
         and any(b.get("type") == "tool_result" for b in m["content"])),
        None,
    )
    assert tool_result_user is not None, (
        f"no user(tool_results) message found: {loop._messages!r}"
    )
    text_blocks = [b for b in tool_result_user["content"] if b.get("type") == "text"]
    assert any(redirect_msg in b.get("text", "") for b in text_blocks), (
        f"redirect text not embedded in tool_results user message; "
        f"got content={tool_result_user['content']!r}"
    )

    for m in loop._messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            assert redirect_msg not in m["content"], (
                f"redirect text leaked into a standalone user message: {m!r}"
            )


@pytest.mark.asyncio
async def test_batch_deny_message_does_not_break_tool_order():
    """BATCH_DENY has the same fix as REDIRECT — it must not insert a
    standalone user message between the assistant tool_use and the
    tool_result.
    """
    from aede.gate import GateDecision

    loop = _make_agent_loop(batch_approval_max=5)
    tool_calls = [{"id": "tc1", "name": "write_file", "input": {"path": "/x", "content": "y"}}]
    redirect_msg = "stop doing that"

    resp_tools = _make_response(tool_calls)
    resp_done = _make_response([])
    resp_done.text = "ok"
    n = {"v": 0}

    async def fake_stream(*a, **kw):
        n["v"] += 1
        return resp_tools if n["v"] == 1 else resp_done

    loop._stream_response = fake_stream

    router = MagicMock()
    router.validate_name = MagicMock()
    router.requires_approval = MagicMock(return_value=True)
    router.execute_sync = MagicMock()
    loop._router = router

    gate_store = MagicMock()
    gate_store.is_allowed = MagicMock(return_value=False)
    loop._gate_store = gate_store

    async def no_compact():
        pass
    loop._maybe_compact = no_compact

    async def fake_request(*a, **kw):
        return GateDecision.BATCH_DENY, redirect_msg

    loop._gate_backend.request = fake_request

    with patch("aede.gate.prompt_gate", new=AsyncMock(return_value=(GateDecision.BATCH_DENY, redirect_msg))):
        await loop.run_turn("do it")

    messages = loop._messages
    asst_idx = _find_index(
        messages,
        lambda m: m.get("role") == "assistant" and isinstance(m.get("content"), list)
        and any(b.get("type") == "tool_use" for b in m["content"]),
    )
    user_idx = _find_index(
        messages,
        lambda m: m.get("role") == "user" and isinstance(m.get("content"), list)
        and any(b.get("type") == "tool_result" for b in m["content"]),
    )
    assert asst_idx >= 0
    assert user_idx > asst_idx
    for i in range(asst_idx + 1, user_idx):
        m = messages[i]
        if m.get("role") == "user":
            assert not (isinstance(m.get("content"), str) and m["content"]), (
                f"BATCH_DENY redirect text leaked into standalone user msg: {m!r}"
            )


def test_conversion_produces_correct_order_after_fix():
    """End-to-end: simulate the fixed message list and verify
    _convert_messages_to_openai produces assistant → tool → user order
    (no plain user message between assistant and tool).
    """
    from aede.provider import _convert_messages_to_openai

    messages = [
        {"role": "user", "content": "do it"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tc1", "name": "write_file", "input": {"path": "/x"}}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tc1",
                    "content": "Redirected: use a different path",
                    "is_error": True,
                },
                {"type": "text", "text": "use a different path"},
            ],
        },
    ]
    oai = _convert_messages_to_openai("sys", messages)
    roles = [m["role"] for m in oai]
    assert "system" in roles
    assert "user" in roles
    assert "assistant" in roles
    assert "tool" in roles
    asst_pos = roles.index("assistant")
    tool_pos = roles.index("tool")
    assert asst_pos < tool_pos, f"assistant must precede tool: roles={roles}"
    after_tool = roles[tool_pos + 1:]
    assert "user" in after_tool, f"user must come after tool (redirect text): roles={roles}"
    for i in range(asst_pos + 1, tool_pos):
        assert roles[i] != "user" or not oai[i].get("content"), (
            f"plain user msg between assistant and tool: roles={roles}"
        )
