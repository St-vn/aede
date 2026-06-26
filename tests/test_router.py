import pytest


def test_validate_args_choices_valid():
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.validate_args("ask_user_choices", {"question": "Pick one", "choices": ["a", "b"]})


def test_validate_args_choices_invalid_type():
    from aede.tools.router import ToolRouter, ToolParamError

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    with pytest.raises(ToolParamError):
        router.validate_args("ask_user_choices", {"question": "?", "choices": "not-a-list"})


def test_validate_args_choices_invalid_element():
    from aede.tools.router import ToolRouter, ToolParamError

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    with pytest.raises(ToolParamError):
        router.validate_args("ask_user_choices", {"question": "?", "choices": [1, 2]})


def test_truncate_cjk():
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=10)
    cjk = "\u4f60\u597d" * 1000
    result = router._truncate(cjk)
    assert "[...output truncated" in result


def test_truncate_ascii_below_limit():
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=10)
    short = "hello"
    assert router._truncate(short) == short


def test_validate_args_array_field_passes():
    from aede.tools.router import ToolRouter

    router = ToolRouter(shell="powershell", wsl_distro="", tool_output_max_tokens=8000)
    router.validate_args("question", {"questions": [{"header": "H", "question": "Q"}]})
