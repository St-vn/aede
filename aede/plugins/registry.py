from __future__ import annotations
from typing import Any


def filter_skills(
    registry: dict[str, Any],
    enabled: list[str] | None = None,
    disabled: list[str] | None = None,
) -> dict[str, Any]:
    """Filter a skill registry by enabled/disabled lists.

    When *enabled* is non-empty, only skills whose names appear in the list
    are returned (disabled is ignored).  When *enabled* is empty or None and
    *disabled* is non-empty, skills in the disabled list are excluded.
    When neither list is set, the registry is returned unchanged.
    """
    if enabled:
        return {name: s for name, s in registry.items() if name in enabled}

    if disabled:
        return {name: s for name, s in registry.items() if name not in disabled}

    return dict(registry)


def parse_plugin_config(config: dict[str, Any] | None) -> tuple[list[str] | None, list[str] | None]:
    """Extract enabled/disabled lists from a plugins config block.

    Returns (enabled, disabled) — either may be None when absent.
    """
    if not config:
        return (None, None)
    enabled: list[str] | None = config.get("enabled") or None
    disabled: list[str] | None = config.get("disabled") or None
    return (enabled, disabled)
