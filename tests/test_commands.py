import pytest
from unittest.mock import MagicMock
from aede.commands import parse_command, CommandResult, COMMANDS
from aede.db import DB


def test_parse_help():
    result = parse_command("/help")
    assert result.name == "help"
    assert result.args == []


def test_parse_resume_no_args():
    result = parse_command("/resume")
    assert result.name == "resume"
    assert result.args == []


def test_parse_resume_with_id():
    result = parse_command("/resume 01J000ABC")
    assert result.name == "resume"
    assert result.args == ["01J000ABC"]


def test_parse_config_no_args():
    result = parse_command("/config")
    assert result.name == "config"
    assert result.args == []


def test_parse_config_with_scope():
    result = parse_command("/config global model claude-opus-4")
    assert result.name == "config"
    assert result.args == ["global", "model", "claude-opus-4"]


def test_parse_tokens():
    result = parse_command("/tokens")
    assert result.name == "tokens"


def test_parse_exit():
    result = parse_command("/exit")
    assert result.name == "exit"


def test_parse_clear():
    result = parse_command("/clear")
    assert result.name == "clear"


def test_parse_compact():
    result = parse_command("/compact")
    assert result.name == "compact"


def test_parse_sessions():
    result = parse_command("/sessions")
    assert result.name == "sessions"


def test_parse_tools():
    result = parse_command("/tools")
    assert result.name == "tools"


def test_parse_unknown_returns_none():
    result = parse_command("/unknown_command")
    assert result is None


def test_parse_keybinds():
    result = parse_command("/keybinds")
    assert result is not None
    assert result.name == "keybinds"
    assert result.args == []


def test_keybinds_in_commands():
    assert "keybinds" in COMMANDS


def test_all_commands_registered():
    for name in ["help", "keybinds", "resume", "sessions", "tools", "config", "compact", "tokens", "clear", "exit"]:
        assert name in COMMANDS


# ---------------------------------------------------------------------------
# handle_resume tests
# ---------------------------------------------------------------------------

class _FakeConsole:
    """Minimal console stub that captures print calls and returns canned input."""

    def __init__(self, canned_input: str = ""):
        self.printed: list[str] = []
        self._canned_input = canned_input

    def print(self, *args, **kwargs) -> None:
        self.printed.append(" ".join(str(a) for a in args))

    def input(self, prompt: str = "") -> str:
        return self._canned_input


def test_handle_resume_unique_prefix(tmp_home):
    """Unique ULID prefix resolves to the full session id."""
    from aede.commands import handle_resume
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    s = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    prefix = s.id[:6]

    console = _FakeConsole()
    result = handle_resume([prefix], db, console)
    assert result == s.id


def test_handle_resume_ambiguous_prefix(tmp_home):
    """Ambiguous prefix (matches multiple sessions) prints candidates and returns None."""
    from aede.commands import handle_resume
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    # Create two sessions; we'll fake the same prefix by using a shared prefix string
    # that deliberately matches two known IDs by checking db.list_sessions directly.
    s1 = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    s2 = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)

    # Find a prefix that matches both (they share ULID time prefix when created rapidly)
    # Use the longest shared prefix
    shared = ""
    for i in range(min(len(s1.id), len(s2.id))):
        if s1.id[i] == s2.id[i]:
            shared += s1.id[i]
        else:
            break
    # shared prefix must be at least 1 char and match both
    assert s1.id.startswith(shared)
    assert s2.id.startswith(shared)

    console = _FakeConsole()
    result = handle_resume([shared], db, console)
    assert result is None
    # Should print something mentioning the candidates
    combined = " ".join(console.printed)
    assert s1.id in combined or s2.id in combined


def test_handle_resume_no_match(tmp_home):
    """Non-matching prefix prints a not-found message and returns None."""
    from aede.commands import handle_resume

    db = DB(tmp_home / "aede.db")
    console = _FakeConsole()
    result = handle_resume(["ZZZZZZZZZZZZZ"], db, console)
    assert result is None
    combined = " ".join(console.printed).lower()
    assert "no session" in combined or "not found" in combined or "zzzzz" in combined.lower()


def test_handle_resume_interactive_picker(tmp_home):
    """No-arg picker lists sessions and returns a valid session id when '1' is entered."""
    from aede.commands import handle_resume
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    s1 = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)
    s2 = Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)

    valid_ids = {s1.id, s2.id}

    # User picks the first item in the displayed list (index 1)
    console = _FakeConsole(canned_input="1")
    result = handle_resume([], db, console)
    assert result in valid_ids


def test_handle_resume_interactive_blank_cancels(tmp_home):
    """Blank input in the interactive picker returns None (cancel)."""
    from aede.commands import handle_resume
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)

    console = _FakeConsole(canned_input="")
    result = handle_resume([], db, console)
    assert result is None


def test_handle_resume_interactive_out_of_range(tmp_home):
    """Out-of-range number in the interactive picker returns None."""
    from aede.commands import handle_resume
    from aede.session import Session

    db = DB(tmp_home / "aede.db")
    Session.create(db=db, model="claude-sonnet-4-20250514", parent_id=None)

    console = _FakeConsole(canned_input="99")
    result = handle_resume([], db, console)
    assert result is None


# ---------------------------------------------------------------------------
# _load_session_notes helper tests
# ---------------------------------------------------------------------------

def test_load_session_notes_returns_content(tmp_path):
    """_load_session_notes reads the notes file when it exists."""
    from aede.commands import _load_session_notes

    session_id = "01TESTSESSION00000000000AB"
    notes_dir = tmp_path / "sessions"
    notes_dir.mkdir(parents=True)
    notes_file = notes_dir / f"{session_id}-notes.md"
    notes_file.write_text("Important context from prior session.")

    result = _load_session_notes(tmp_path, session_id)
    assert result == "Important context from prior session."


def test_load_session_notes_returns_none_when_missing(tmp_path):
    """_load_session_notes returns None when no notes file exists."""
    from aede.commands import _load_session_notes

    result = _load_session_notes(tmp_path, "NOSUCHSESSION")
    assert result is None


def test_load_session_notes_passed_to_build_system_prompt():
    """Notes loaded by _load_session_notes appear under '## Session Notes' in the system prompt."""
    from aede.agent import build_system_prompt

    notes = "We were debugging the REPL resume flow."
    cfg = MagicMock()
    cfg.model = "claude-sonnet-4-20250514"
    cfg.shell = "powershell"
    cfg.tool_output_max_tokens = 2000
    cfg.context_window = 200000
    cfg.compaction_threshold = 0.8

    prompt = build_system_prompt(
        cfg=cfg,
        session_id="01TEST",
        is_resume=True,
        session_notes=notes,
        compaction_summary=None,
    )
    assert "## Session Notes" in prompt.dynamic
    assert notes in prompt.dynamic


# ---------------------------------------------------------------------------
# config command handler tests
# ---------------------------------------------------------------------------

def test_handle_config_show_output():
    from aede.commands import handle_config_show
    cfg = MagicMock()
    cfg.model = "my-model"
    cfg.compaction_threshold = 0.8
    cfg.tool_output_max_tokens = 500
    cfg.shell = "bash"
    cfg.batch_approval_max = 5
    cfg.gate_mode = "normal"
    cfg.auto_approve = ["read_file"]
    cfg.sources = {
        "model": "global",
        "shell": "project",
        "compaction_threshold": "default",
    }

    console = _FakeConsole()
    handle_config_show(cfg, console)

    output = "\n".join(console.printed)
    assert "[global]" in output
    assert "[project]" in output
    assert "[default]" in output
    assert "my-model" in output
    assert "bash" in output


def test_handle_config_edit_dispatcher(tmp_path):
    from aede.commands import handle_config_edit
    from unittest.mock import patch

    cfg = MagicMock()
    console = _FakeConsole()
    home = tmp_path / "home"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # 1. Test invalid scope
    handle_config_edit(["invalid_scope"], cfg, console, home, project_dir)
    assert "error: scope must be 'global' or 'project'" in "\n".join(console.printed).lower()

    # 2. Test edit_config_file trigger
    with patch("aede.config.edit_config_file") as mock_edit:
        handle_config_edit(["global"], cfg, console, home, project_dir)
        mock_edit.assert_called_once_with("global", home=home, project_dir=project_dir)
        assert "opened global config file in editor" in "\n".join(console.printed).lower()

    # 3. Test write_config_value trigger for key-value scalar
    with patch("aede.config.write_config_value") as mock_write:
        handle_config_edit(["project", "shell", "cmd"], cfg, console, home, project_dir)
        mock_write.assert_called_once_with(scope="project", key="shell", value="cmd", home=home, project_dir=project_dir)
        assert "shell set to 'cmd'" in "\n".join(console.printed).lower()

    # 4. Test write_config_value trigger for list add
    with patch("aede.config.write_config_value") as mock_write_list:
        handle_config_edit(["global", "auto_approve", "add", "web_search"], cfg, console, home, project_dir)
        mock_write_list.assert_called_once_with(scope="global", key="auto_approve", value="web_search", action="add", home=home, project_dir=project_dir)
        assert "auto_approve list updated" in "\n".join(console.printed).lower()

    # 5. Test unknown key
    console = _FakeConsole()
    handle_config_edit(["project", "no_such_key", "val"], cfg, console, home, project_dir)
    assert "unknown config key" in "\n".join(console.printed).lower()

