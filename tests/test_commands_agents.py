import pytest
from unittest.mock import MagicMock


class _FakeConsole:
    def __init__(self):
        self.printed: list[str] = []

    def print(self, *args, **kwargs) -> None:
        self.printed.append(" ".join(str(a) for a in args))


def _make_agent(name: str, description: str, model: str = "inherit"):
    agent = MagicMock()
    agent.name = name
    agent.description = description
    agent.model = model
    agent.body = f"## {name.title()}"
    return agent


def test_handle_agents_table():
    """handle_agents prints a formatted list with agent names, descriptions, and models."""
    from aede.commands import handle_agents

    registry = {
        "researcher": _make_agent("researcher", "Research specialist", "claude-haiku-4"),
        "writer": _make_agent("writer", "Writing assistant"),
    }

    console = _FakeConsole()
    handle_agents(registry, console)

    output = "\n".join(console.printed)
    assert "Agents:" in output
    assert "researcher" in output
    assert "writer" in output
    assert "claude-haiku-4" in output


def test_handle_agents_empty():
    """Empty registry prints a message."""
    from aede.commands import handle_agents

    console = _FakeConsole()
    handle_agents({}, console)

    output = "\n".join(console.printed).lower()
    assert "no agents" in output


def test_handle_agents_truncates_long_description():
    """Description longer than 60 chars is truncated with ellipsis."""
    from aede.commands import handle_agents

    long_desc = "B" * 100
    registry = {"toolong": _make_agent("toolong", long_desc)}

    console = _FakeConsole()
    handle_agents(registry, console)

    output = "\n".join(console.printed)
    assert "..." in output
