import pytest
from unittest.mock import patch, MagicMock
from aede.tools.router import ToolRouter, ToolResult, UnknownToolError


def make_router() -> ToolRouter:
    return ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )


def test_router_known_tools(tmp_path):
    r = make_router()
    assert "powershell" in r.tool_names()
    assert "read_file" in r.tool_names()
    assert "write_file" in r.tool_names()
    assert "create_file" in r.tool_names()
    assert "list_dir" in r.tool_names()
    assert "search_files" in r.tool_names()
    assert "fetch_url" in r.tool_names()
    assert "web_search" in r.tool_names()
    assert "ask_user" in r.tool_names()
    assert "ask_user_choices" in r.tool_names()
    assert "ask_user_confirm" in r.tool_names()
    assert "question" in r.tool_names()


def test_router_question_tool_schema():
    r = make_router()
    schemas = {s["name"]: s for s in r.anthropic_tool_schemas()}
    assert "question" in schemas
    schema = schemas["question"]["input_schema"]
    assert "questions" in schema["required"]
    items = schema["properties"]["questions"]["items"]
    item_props = items["properties"]
    assert "allow_custom" in item_props
    assert "allow_notes" in item_props
    assert "header" in items["required"]
    assert "question" in items["required"]


def test_router_web_search_always_available():
    r = make_router()
    assert "web_search" in r.tool_names()


def test_router_unknown_tool_raises():
    r = make_router()
    with pytest.raises(UnknownToolError):
        r.validate_name("nonexistent_tool")


def test_router_requires_approval_for_gate_tools():
    r = make_router()
    assert r.requires_approval("powershell") is True
    assert r.requires_approval("write_file") is True
    assert r.requires_approval("create_file") is True
    assert r.requires_approval("read_file") is False
    assert r.requires_approval("list_dir") is False
    assert r.requires_approval("search_files") is False
    assert r.requires_approval("fetch_url") is False
    assert r.requires_approval("web_search") is False


def test_router_auto_approve_override():
    r = make_router()
    r.set_auto_approved(["powershell"])
    assert r.requires_approval("powershell") is False


def test_read_file_success(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    r = make_router()
    result = r.execute_sync("read_file", {"path": str(f)})
    assert result.status == "success"
    assert "hello world" in result.output


def test_read_file_not_found(tmp_path):
    r = make_router()
    result = r.execute_sync("read_file", {"path": str(tmp_path / "nope.txt")})
    assert result.status == "error"
    assert "not found" in result.output.lower() or "no such" in result.output.lower()


def test_write_file_success(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("original")
    r = make_router()
    result = r.execute_sync("write_file", {"path": str(f), "content": "updated"})
    assert result.status == "success"
    assert f.read_text() == "updated"


def test_write_file_fails_if_not_exists(tmp_path):
    r = make_router()
    result = r.execute_sync("write_file", {"path": str(tmp_path / "new.txt"), "content": "x"})
    assert result.status == "error"
    assert "does not exist" in result.output


def test_create_file_success(tmp_path):
    r = make_router()
    result = r.execute_sync("create_file", {"path": str(tmp_path / "new.txt"), "content": "hello"})
    assert result.status == "success"
    assert (tmp_path / "new.txt").read_text() == "hello"


def test_create_file_fails_if_exists(tmp_path):
    f = tmp_path / "exists.txt"
    f.write_text("already here")
    r = make_router()
    result = r.execute_sync("create_file", {"path": str(f), "content": "x"})
    assert result.status == "error"
    assert "already exists" in result.output


def test_list_dir(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    r = make_router()
    result = r.execute_sync("list_dir", {"path": str(tmp_path)})
    assert result.status == "success"
    assert "a.txt" in result.output
    assert "b.txt" in result.output


# ---------------------------------------------------------------------------
# Task 6 — ToolRouter.validate_args (Pydantic param validation)
# ---------------------------------------------------------------------------

def test_validate_args_missing_required_raises():
    """write_file requires path + content; missing content must raise ToolParamError."""
    from aede.tools.router import ToolParamError
    r = make_router()
    with pytest.raises(ToolParamError):
        r.validate_args("write_file", {"path": "x"})


def test_validate_args_valid_args_passes():
    """write_file with path + content must not raise."""
    r = make_router()
    r.validate_args("write_file", {"path": "x", "content": "y"})  # no exception


def test_validate_args_wrong_type_raises():
    """list_dir requires path as a string; passing an int must raise ToolParamError."""
    from aede.tools.router import ToolParamError
    r = make_router()
    with pytest.raises(ToolParamError):
        r.validate_args("list_dir", {"path": 123})


def test_validate_args_valid_list_dir_passes():
    """list_dir with a string path must not raise."""
    r = make_router()
    r.validate_args("list_dir", {"path": "/some/dir"})  # no exception


def test_validate_args_powershell_missing_cmd():
    """powershell requires cmd; missing it must raise ToolParamError."""
    from aede.tools.router import ToolParamError
    r = make_router()
    with pytest.raises(ToolParamError):
        r.validate_args("powershell", {})


def test_validate_args_powershell_valid():
    """powershell with cmd string must not raise."""
    r = make_router()
    r.validate_args("powershell", {"cmd": "echo hello"})  # no exception
