"""Integration tests for re-injection and compaction working together."""


def test_reinjection_constant_and_tracker_exist():
    """REINJECTION_INTERVAL and _tokens_since_last_reminder must exist."""
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")

    assert "REINJECTION_INTERVAL" in source
    assert "20000" in source
    assert "tokens_since_last_reminder" in source


def test_reinjection_method_exists():
    """_inject_reminder method must exist in AgentLoop."""
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")

    assert "_inject_reminder" in source
    assert "REINJECTION" in source


def test_reinjection_adds_user_message():
    """_inject_reminder must append a user-role message to _messages."""
    from unittest.mock import MagicMock
    from aede.agent import AgentLoop

    loop = AgentLoop.__new__(AgentLoop)
    loop._messages = []
    loop._cfg = MagicMock()
    loop._cfg.project_dir = None
    loop._session = MagicMock(id="test-sid")
    loop._db = MagicMock()
    loop._rollout = MagicMock()
    loop._router = MagicMock()
    loop._gate_store = MagicMock()
    loop._tracker = MagicMock()
    loop._tracker.record = MagicMock()
    loop._console = MagicMock()
    loop._project_dir = None
    loop._current_objective = "Test objective"
    loop._active_constraints = "Test constraints"
    loop._open_decisions = "Test decisions"
    loop._tokens_since_last_reminder = 0
    loop._acp_manager = None
    loop._stream_text = None
    loop._stream_thinking = None
    loop._stream_tool_call = None
    loop._stream_tool_result = None
    loop._accumulated_thinking = ""
    loop._provider = None
    loop._system_prompt = ""
    loop._turn = 0
    loop._mode = MagicMock()
    loop._skills = None
    loop._learnings_suffix = None
    loop._trace_logger = None

    loop._inject_reminder()

    assert len(loop._messages) == 1
    msg = loop._messages[0]
    assert msg["role"] == "user"
    assert "REINJECTION" in msg["content"]
    assert "Test objective" in msg["content"]


def test_compaction_prompt_preserves_structure():
    """COMPACTION_PROMPT must instruct the LLM to preserve goal/plan/todos."""
    import pathlib
    source = pathlib.Path("aede/compaction.py").read_text(encoding="utf-8")

    assert "goal" in source.lower()
    assert "plan" in source.lower() or "todo" in source.lower()
    assert "verbatim" in source.lower() or "exactly" in source.lower() or "preserve" in source.lower()


def test_plan_artifact_tools_registered_for_compaction_recovery():
    """read_plan_artifact exists so agent can recover after compaction."""
    import pathlib
    router_source = pathlib.Path("aede/tools/router.py").read_text(encoding="utf-8")
    assert "read_plan_artifact" in router_source

    agent_source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")
    assert "read_plan_artifact" in agent_source.lower()


def test_reinjection_reminder_mentions_plan_file():
    """_inject_reminder must tell the agent to re-read the plan file."""
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text(encoding="utf-8")
    assert "plan file" in source.lower() or "read_plan_artifact" in source.lower()
