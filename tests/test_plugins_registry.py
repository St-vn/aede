import pytest
from pathlib import Path


def _fake_skill(name: str, description: str = "desc"):
    from unittest.mock import MagicMock
    s = MagicMock()
    s.name = name
    s.description = description
    return s


def test_filter_skills_enabled_only():
    """Only skills in enabled list pass through."""
    from aede.plugins.registry import filter_skills

    skills = {
        "web_search": _fake_skill("web_search"),
        "data_analysis": _fake_skill("data_analysis"),
        "code_review": _fake_skill("code_review"),
    }

    result = filter_skills(skills, enabled=["web_search", "code_review"])

    assert "web_search" in result
    assert "code_review" in result
    assert "data_analysis" not in result


def test_filter_skills_disabled_only():
    """Skills in disabled list are excluded."""
    from aede.plugins.registry import filter_skills

    skills = {
        "web_search": _fake_skill("web_search"),
        "data_analysis": _fake_skill("data_analysis"),
    }

    result = filter_skills(skills, disabled=["web_search"])

    assert "web_search" not in result
    assert "data_analysis" in result


def test_filter_skills_empty_lists():
    """Empty enabled/disabled lists return all skills."""
    from aede.plugins.registry import filter_skills

    skills = {
        "web_search": _fake_skill("web_search"),
        "data_analysis": _fake_skill("data_analysis"),
    }

    result = filter_skills(skills, enabled=None, disabled=None)
    assert result == skills

    result = filter_skills(skills, enabled=[], disabled=[])
    assert result == skills


def test_filter_skills_enabled_takes_precedence():
    """Enabled list takes precedence — disabled is ignored when enabled is set."""
    from aede.plugins.registry import filter_skills

    skills = {
        "web_search": _fake_skill("web_search"),
        "data_analysis": _fake_skill("data_analysis"),
    }

    result = filter_skills(skills, enabled=["web_search"], disabled=["web_search"])

    assert "web_search" in result
    assert "data_analysis" not in result


def test_filter_skills_unknown_in_enabled():
    """Names in enabled list that don't match any skill are silently ignored."""
    from aede.plugins.registry import filter_skills

    skills = {"web_search": _fake_skill("web_search")}

    result = filter_skills(skills, enabled=["web_search", "nonexistent"])

    assert "web_search" in result
    assert "nonexistent" not in result


def test_filter_skills_empty_registry():
    """Empty skill registry returns empty dict regardless of filters."""
    from aede.plugins.registry import filter_skills

    assert filter_skills({}, enabled=["web_search"]) == {}
    assert filter_skills({}, disabled=None) == {}


def test_plugin_config_defaults_in_config():
    """Default config includes plugins block with empty enabled/disabled."""
    from aede.config import DEFAULT_CONFIG

    assert "plugins" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["plugins"] == {}


def test_plugin_integration_from_config(tmp_home):
    """Plugin filter can be driven from a config dict."""
    from aede.plugins.registry import parse_plugin_config

    config = {"enabled": ["skill_a"], "disabled": ["skill_b"]}

    enabled, disabled = parse_plugin_config(config)
    assert enabled == ["skill_a"]
    assert disabled == ["skill_b"]


def test_plugin_integration_from_config_empty():
    """Empty or missing plugins block returns (None, None)."""
    from aede.plugins.registry import parse_plugin_config

    assert parse_plugin_config({}) == (None, None)
    assert parse_plugin_config(None) == (None, None)
