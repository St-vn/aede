"""RF-2: OpenAI-style providers (e.g. DeepSeek) may stream tool_call deltas
with no id; an empty id collides across calls and breaks React keys in the UI.
The finalize step must synthesize a non-empty, index-stable id."""


def test_finalize_synthesizes_id_when_provider_omits_it():
    from aede.provider import _finalize_tool_call_id
    assert _finalize_tool_call_id("", 0) == "call_0"
    assert _finalize_tool_call_id("", 1) == "call_1"


def test_finalize_keeps_real_provider_id():
    from aede.provider import _finalize_tool_call_id
    assert _finalize_tool_call_id("call_real", 0) == "call_real"


def test_finalize_handles_none_id():
    from aede.provider import _finalize_tool_call_id
    assert _finalize_tool_call_id(None, 3) == "call_3"
