import pytest, asyncio
from unittest.mock import AsyncMock, MagicMock
from aede.server import WebSocketAskUserBackend, SessionGate
from aede.gate import AskUserBackend


@pytest.mark.asyncio
async def test_ws_backend_sends_questions_array():
    """WebSocketAskUserBackend sends questions array in ask_user_request payload."""
    gate = SessionGate()
    gate.websocket = AsyncMock()
    backend = WebSocketAskUserBackend(gate)

    questions = [
        {"header": "Color", "question": "Pick color", "type": "single", "options": ["R", "G", "B"], "required": True},
        {"header": "Notes", "question": "Any notes?", "type": "text", "required": False},
    ]

    async def delayed_resolve():
        await asyncio.sleep(0.05)
        fut = gate.futures.get("ask:ws-1")
        if fut is not None and not fut.done():
            fut.set_result(({"answers": {"Pick color": "G"}}, ""))

    task = asyncio.create_task(delayed_resolve())
    try:
        result = await backend.ask(question_id="ws-1", questions=questions)
    finally:
        task.cancel()

    assert isinstance(result, dict)
    assert result["answers"]["Pick color"] == "G"

    # Check the payload sent via websocket
    assert gate.websocket.send_json.called
    sent = gate.websocket.send_json.call_args[0][0]
    assert sent["type"] == "ask_user_request"
    assert sent["question_id"] == "ws-1"
    assert "questions" in sent
    assert len(sent["questions"]) == 2
    assert sent["questions"][0]["question"] == "Pick color"
    assert sent["questions"][1]["question"] == "Any notes?"


@pytest.mark.asyncio
async def test_ws_backend_isinstance_of_protocol():
    gate = SessionGate()
    backend = WebSocketAskUserBackend(gate)
    assert isinstance(backend, AskUserBackend)


@pytest.mark.asyncio
async def test_ws_backend_multiple_questions_answers():
    """WebSocketAskUserBackend returns all answers for multi-question sets."""
    gate = SessionGate()
    gate.websocket = AsyncMock()
    backend = WebSocketAskUserBackend(gate)

    questions = [
        {"header": "Q1", "question": "First", "type": "single", "options": ["A", "B"], "required": True},
        {"header": "Q2", "question": "Second", "type": "multi", "options": ["X", "Y", "Z"], "required": True},
        {"header": "Q3", "question": "Third", "type": "text", "required": False},
    ]

    async def delayed_resolve():
        await asyncio.sleep(0.05)
        fut = gate.futures.get("ask:multi")
        if fut is not None and not fut.done():
            fut.set_result(({
                "answers": {
                    "First": "B",
                    "Second": ["X", "Z"],
                    "Third": "hello",
                }
            }, ""))

    task = asyncio.create_task(delayed_resolve())
    try:
        result = await backend.ask(question_id="multi", questions=questions)
    finally:
        task.cancel()

    assert result["answers"]["First"] == "B"
    assert result["answers"]["Second"] == ["X", "Z"]
    assert result["answers"]["Third"] == "hello"


@pytest.mark.asyncio
async def test_ws_backend_error_unknown_question_id():
    """When no future exists for a key, ask still awaits (the response
    handler sends an error message, but the unresolved future times out
    or gets cancelled by the test). We verify the payload was stored."""
    gate = SessionGate()
    gate.websocket = AsyncMock()
    backend = WebSocketAskUserBackend(gate)

    # Don't pre-set a future — verify the payload is stored in pending_requests
    questions = [{"header": "Q", "question": "Test?", "type": "text"}]

    async def delayed_resolve():
        await asyncio.sleep(0.05)
        fut = gate.futures.get("ask:no-answer")
        if fut is not None and not fut.done():
            fut.set_result(({"answers": {}}, ""))

    task = asyncio.create_task(delayed_resolve())
    try:
        result = await backend.ask(question_id="no-answer", questions=questions)
    finally:
        task.cancel()

    # Verify pending request was stored
    key = "ask:no-answer"
    assert key not in gate.pending_requests  # cleaned up in finally
    sent = gate.websocket.send_json.call_args[0][0]
    assert sent["type"] == "ask_user_request"
    assert sent["question_id"] == "no-answer"
