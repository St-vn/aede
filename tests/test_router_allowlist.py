import pytest
from unittest.mock import MagicMock


def test_toolrouter_from_allowlist():
    """from_allowlist returns ToolRouter with only named tools registered."""
    from aede.tools.router import ToolRouter, UnknownToolError

    shell = MagicMock()
    router = ToolRouter.from_allowlist(
        names=["read_file", "web_search"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    tool_names = router.tool_names()
    assert "read_file" in tool_names
    assert "web_search" in tool_names
    assert "powershell" not in tool_names
    assert "fetch_url" not in tool_names


def test_toolrouter_from_allowlist_all_tools():
    """Passing full tool list creates router with all tools."""
    from aede.tools.router import ToolRouter

    full_names = ["powershell", "read_file", "write_file", "create_file",
                  "list_dir", "search_files", "fetch_url", "web_search"]

    router = ToolRouter.from_allowlist(
        names=full_names,
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    assert set(router.tool_names()) == set(full_names)


def test_toolrouter_from_allowlist_unknown_raises():
    """Unknown tool name raises UnknownToolError."""
    from aede.tools.router import ToolRouter, UnknownToolError

    with pytest.raises(UnknownToolError, match="no_such_tool"):
        ToolRouter.from_allowlist(
            names=["read_file", "no_such_tool"],
            shell="powershell",
            wsl_distro="",
            tool_output_max_tokens=8000,
        )


def test_toolrouter_from_allowlist_tool_schemas_match():
    """anthropic_tool_schemas only includes allowed tools."""
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=["read_file"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    schemas = router.anthropic_tool_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "read_file"
