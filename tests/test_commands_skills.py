import pytest
from unittest.mock import MagicMock


class _FakeConsole:
    def __init__(self):
        self.printed: list[str] = []

    def print(self, *args, **kwargs) -> None:
        self.printed.append(" ".join(str(a) for a in args))


def _make_skill(name: str, description: str, source: str = "global"):
    skill = MagicMock()
    skill.name = name
    skill.description = description
    skill.body = f"## {name.title()}"
    return skill


def test_handle_skills_table():
    """handle_skills prints a formatted list with skill names and descriptions."""
    from aede.commands import handle_skills

    registry = {
        "web_search": _make_skill("web_search", "Search the web"),
        "data_analysis": _make_skill("data_analysis", "Analyze data and produce insights with great depth and detail"),
    }

    console = _FakeConsole()
    handle_skills(registry, console)

    output = "\n".join(console.printed)
    assert "Skills:" in output
    assert "web_search" in output
    assert "data_analysis" in output
    assert "Search the web" in output


def test_handle_skills_empty():
    """Empty registry prints a message."""
    from aede.commands import handle_skills

    console = _FakeConsole()
    handle_skills({}, console)

    output = "\n".join(console.printed).lower()
    assert "no skills" in output or "none" in output


def test_handle_skills_truncates_long_description():
    """Description longer than 60 chars is truncated with ellipsis."""
    from aede.commands import handle_skills

    long_desc = "A" * 100
    registry = {"toolong": _make_skill("toolong", long_desc)}

    console = _FakeConsole()
    handle_skills(registry, console)

    output = "\n".join(console.printed)
    assert "..." in output
    assert "A" * 60 in output
