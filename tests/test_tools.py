import pytest
from unittest.mock import patch, MagicMock
from jarvis.tools.router import ToolRouter, ToolResult, UnknownToolError


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
