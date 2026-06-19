import pytest, json, inspect, asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aede.gate import AskUserBackend, TerminalAskUserBackend, PermissionMode
from aede.tools.router import ToolRouter


def make_router() -> ToolRouter:
    return ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )


class TestT1_Schemas:
    def test_question_schema_has_unified_fields(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        assert "question" in schemas
        props = schemas["question"]["input_schema"]["properties"]
        item_props = props["questions"]["items"]["properties"]
        for field in ("header", "question", "type", "options", "allow_custom", "allow_notes", "required"):
            assert field in item_props, f"Missing field: {field}"
        assert "single" in item_props["type"]["enum"]
        assert "multi" in item_props["type"]["enum"]
        assert "text" in item_props["type"]["enum"]

    def test_legacy_ask_user_schemas_still_registered(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        for name in ("ask_user", "ask_user_choices", "ask_user_confirm", "question"):
            assert name in schemas, f"Missing schema for {name!r}"

    def test_question_schema_requires_questions(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        assert "questions" in schemas["question"]["input_schema"]["required"]

    def test_question_schema_requires_header_and_question_in_items(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        item_required = schemas["question"]["input_schema"]["properties"]["questions"]["items"]["required"]
        assert "header" in item_required
        assert "question" in item_required

    def test_question_schema_type_defaults_to_single(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        item_props = schemas["question"]["input_schema"]["properties"]["questions"]["items"]["properties"]
        assert item_props["type"]["default"] == "single"

    def test_allow_custom_default_is_true(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        item_props = schemas["question"]["input_schema"]["properties"]["questions"]["items"]["properties"]
        assert item_props["allow_custom"]["default"] is True, "allow_custom should default to True"

    def test_allow_notes_default_is_true(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        item_props = schemas["question"]["input_schema"]["properties"]["questions"]["items"]["properties"]
        assert item_props["allow_notes"]["default"] is True, "allow_notes should default to True"

    def test_description_contains_preset_templates(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        desc = schemas["question"]["description"]
        assert "PRESET TEMPLATES" in desc, "description should contain preset template guidance"
        assert "allow_custom" in desc, "description should reference allow_custom flag guidance"
        assert "allow_notes" in desc, "description should reference allow_notes flag guidance"

    def test_unified_schema_has_no_legacy_allow_custom_answer_at_top(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        props = schemas["question"]["input_schema"]["properties"]
        assert "allow_custom_answer" not in props, "allow_custom_answer moved to per-question"

    def test_unified_schema_has_no_id_item(self):
        r = make_router()
        schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
        item_props = schemas["question"]["input_schema"]["properties"]["questions"]["items"]["properties"]
        assert "id" not in item_props, "id removed from unified schema"


class TestT2_NormalizePayload:
    def test_normalize_ask_user(self):
        from aede.agent import _normalize_question_payload
        result = _normalize_question_payload("ask_user", {"question": "What color?"})
        assert len(result) == 1
        q = result[0]
        assert q["header"] == "Question"
        assert q["question"] == "What color?"
        assert q["type"] == "text"
        assert q["required"] is True

    def test_normalize_ask_user_choices(self):
        from aede.agent import _normalize_question_payload
        result = _normalize_question_payload(
            "ask_user_choices",
            {"question": "Pick one", "choices": ["A", "B"]},
        )
        assert len(result) == 1
        q = result[0]
        assert q["header"] == "Question"
        assert q["question"] == "Pick one"
        assert q["type"] == "single"
        assert q["options"] == ["A", "B"]
        assert q["required"] is True

    def test_normalize_ask_user_confirm(self):
        from aede.agent import _normalize_question_payload
        result = _normalize_question_payload("ask_user_confirm", {"question": "Proceed?"})
        assert len(result) == 1
        q = result[0]
        assert q["header"] == "Confirm"
        assert q["question"] == "Proceed?"
        assert q["type"] == "single"
        assert q["options"] == ["yes", "no"]
        assert q["required"] is True

    def test_normalize_question_passthrough(self):
        from aede.agent import _normalize_question_payload
        questions = [
            {"header": "Format", "question": "How?", "type": "single", "options": ["A", "B"]},
        ]
        result = _normalize_question_payload("question", {"questions": questions})
        # Passthrough preserves the model-supplied fields...
        assert result[0]["header"] == "Format"
        assert result[0]["question"] == "How?"
        assert result[0]["options"] == ["A", "B"]

    def test_normalize_question_injects_custom_and_notes_defaults(self):
        from aede.agent import _normalize_question_payload
        qs = _normalize_question_payload(
            "question",
            {"questions": [{"header": "H", "question": "Q?", "type": "single", "options": ["a", "b"]}]},
        )
        assert qs[0]["allow_custom"] is True
        assert qs[0]["allow_notes"] is True

    def test_normalize_question_respects_explicit_false(self):
        from aede.agent import _normalize_question_payload
        qs = _normalize_question_payload(
            "question",
            {"questions": [{"header": "H", "question": "Yes/no?", "type": "single",
                            "options": ["yes", "no"], "allow_custom": False, "allow_notes": False}]},
        )
        assert qs[0]["allow_custom"] is False
        assert qs[0]["allow_notes"] is False

    def test_normalized_question_drives_cli_custom_option(self):
        # gate.py reads q.get("allow_custom", False); after normalize it must see True.
        from aede.agent import _normalize_question_payload
        q = _normalize_question_payload(
            "question", {"questions": [{"header": "H", "question": "Q?", "type": "single", "options": ["a"]}]}
        )[0]
        assert q.get("allow_custom", False) is True
        assert q.get("allow_notes", False) is True


class TestT3_AutoMode:
    def test_auto_mode_single(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "Pick", "question": "Choose one", "type": "single", "options": ["X", "Y"]},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Choose one": "X"}

    def test_auto_mode_multi(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "Pick", "question": "Choose many", "type": "multi", "options": ["A", "B", "C"]},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Choose many": ["A"]}

    def test_auto_mode_text(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "Input", "question": "Your thoughts?", "type": "text"},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Your thoughts?": "[auto mode: skipped]"}

    def test_auto_mode_single_no_options(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "Pick", "question": "Choose", "type": "single"},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Choose": "[auto mode: skipped]"}

    def test_auto_mode_multi_no_options(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "Pick", "question": "Choose", "type": "multi"},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Choose": []}

    def test_auto_mode_mixed_questions(self):
        from aede.agent import _build_auto_answers
        questions = [
            {"header": "A", "question": "Single", "type": "single", "options": ["X"]},
            {"header": "B", "question": "Multi", "type": "multi", "options": ["Y", "Z"]},
            {"header": "C", "question": "Text", "type": "text"},
        ]
        answers = _build_auto_answers(questions)
        assert answers == {"Single": "X", "Multi": ["Y"], "Text": "[auto mode: skipped]"}


class TestT4_AskUserBackendProtocol:
    def test_protocol_has_questions_param(self):
        sig = inspect.signature(AskUserBackend.ask)
        assert "questions" in sig.parameters
        assert "question_id" in sig.parameters

    def test_terminal_backend_accepts_questions_list(self):
        backend = TerminalAskUserBackend(console=MagicMock())
        sig = inspect.signature(backend.ask)
        assert "questions" in sig.parameters
        assert inspect.iscoroutinefunction(backend.ask)

    @pytest.mark.asyncio
    async def test_terminal_backend_returns_answers_dict(self):
        mock_console = MagicMock()
        backend = TerminalAskUserBackend(console=mock_console)
        with patch("aede.gate._prompt_question_item", return_value="my answer"):
            result = await backend.ask(
                question_id="q1",
                questions=[{"header": "Q", "question": "Test?", "type": "text", "required": True}],
            )
        assert isinstance(result, dict)
        assert "answers" in result
        assert result["answers"]["Test?"] == "my answer"

    def test_terminal_backend_isinstance_of_protocol(self):
        backend = TerminalAskUserBackend(console=MagicMock())
        assert isinstance(backend, AskUserBackend)


class TestT5_WebSocketBackend:
    @pytest.mark.asyncio
    async def test_websocket_backend_accepts_questions(self):
        from aede.server import WebSocketAskUserBackend
        gate = MagicMock()
        gate.futures = {}
        gate.pending_requests = {}
        backend = WebSocketAskUserBackend(gate)
        sig = inspect.signature(backend.ask)
        assert "questions" in sig.parameters

    @pytest.mark.asyncio
    async def test_websocket_ask_user_payload_shape(self):
        from aede.server import WebSocketAskUserBackend
        import asyncio

        sent_payloads = []

        async def capture_send_json(payload):
            sent_payloads.append(payload)
            return

        gate = MagicMock()
        gate.futures = {}
        gate.pending_requests = {}
        gate.websocket = AsyncMock()
        gate.websocket.send_json = capture_send_json
        backend = WebSocketAskUserBackend(gate)

        async def delayed_resolve():
            await asyncio.sleep(0.01)
            fut = gate.futures.get("ask:q1")
            if fut is not None and not fut.done():
                fut.set_result(({"answers": {"Test?": "yes"}}, ""))

        async def run():
            task = asyncio.create_task(delayed_resolve())
            try:
                result = await backend.ask(
                    question_id="q1",
                    questions=[{"header": "Q", "question": "Test?", "type": "text", "required": True}],
                )
                return result
            finally:
                task.cancel()

        result = await run()
        assert isinstance(result, dict)
        assert result["answers"]["Test?"] == "yes"

        assert len(sent_payloads) == 1
        sent = sent_payloads[0]
        assert sent.get("type") == "ask_user_request"
        assert "questions" in sent
        assert isinstance(sent["questions"], list)
        assert sent["questions"][0]["question"] == "Test?"

    def test_websocket_backend_isinstance_of_protocol(self):
        from aede.server import WebSocketAskUserBackend
        gate = MagicMock()
        backend = WebSocketAskUserBackend(gate)
        assert isinstance(backend, AskUserBackend)
