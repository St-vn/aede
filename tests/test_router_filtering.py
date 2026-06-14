import pytest


def test_toolrouter_disallowed_tools():
    """Disallowed tools removed after allowlist filtering.

    When allowed_tools is None, start with all tools, then filter out disallowed.
    """
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=None,
        disallowed_tools=["powershell", "write_file", "create_file"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    tool_names = router.tool_names()
    assert "powershell" not in tool_names
    assert "write_file" not in tool_names
    assert "create_file" not in tool_names
    assert "read_file" in tool_names
    assert "web_search" in tool_names
    assert "fetch_url" in tool_names
    assert "list_dir" in tool_names
    assert "search_files" in tool_names


def test_toolrouter_disallowed_with_allowlist():
    """When both allowed_tools and disallowed_tools provided, disallowed wins."""
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=["read_file", "write_file", "web_search", "powershell"],
        disallowed_tools=["powershell", "write_file"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    tool_names = router.tool_names()
    assert "read_file" in tool_names
    assert "web_search" in tool_names
    assert "powershell" not in tool_names
    assert "write_file" not in tool_names


def test_toolrouter_disallowed_empty():
    """Empty disallowed list removes nothing when allowed_tools is None."""
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=None,
        disallowed_tools=[],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    assert len(router.tool_names()) == 12  # all default tools + spawn_subagent + session_search + write_learning + select_context


def test_toolrouter_disallowed_all_removed():
    """Disallowing all tools results in empty registry."""
    from aede.tools.router import ToolRouter

    router = ToolRouter.from_allowlist(
        names=None,
        disallowed_tools=["powershell", "read_file", "write_file", "create_file",
                          "list_dir", "search_files", "fetch_url", "web_search",
                          "spawn_subagent", "write_learning", "session_search",
                          "select_context"],
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
    )

    assert router.tool_names() == []
