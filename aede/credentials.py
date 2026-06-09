"""
Credentials vault for aede.

Stores API keys and other secrets in ``~/.aede/credentials.json`` so they
are loaded automatically on every launch without requiring OS-level environment
variables.  Real environment variables always take precedence over vault values.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import os


class CredentialsError(ValueError):
    """Raised when the credentials file exists but cannot be parsed."""


def credentials_path(home: Path) -> Path:
    """Return the canonical path to the credentials vault file."""
    return home / "credentials.json"


def load_credentials_into_env(home: Path) -> list[str]:
    """
    Load credentials from the vault file into os.environ.

    Real environment variables take precedence: a name already present in
    os.environ is NOT overwritten. Returns the list of names that were loaded
    from the vault (i.e. names that were not already in the environment).

    Raises CredentialsError if the file exists but contains malformed JSON.
    Returns [] if the file does not exist.
    """
    path = credentials_path(home)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise CredentialsError(
            f"Credentials file at {path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise CredentialsError(
            f"Credentials file at {path} must contain a JSON object, "
            f"got {type(data).__name__}."
        )

    loaded: list[str] = []
    for name, entry in data.items():
        if name in os.environ:
            continue
        if isinstance(entry, dict):
            actual_value = entry.get("value", "")
        else:
            actual_value = entry
        os.environ[name] = str(actual_value)
        loaded.append(name)
    return loaded


def set_credential(
    home: Path, name: str, value: str, provider: str | None = None
) -> None:
    """
    Write a credential into the vault file, creating it if necessary.

    Existing keys are preserved. After writing, restricts file permissions to
    owner-only (best-effort; a no-op or harmless failure on Windows).
    """
    path = credentials_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                data = existing
        except (json.JSONDecodeError, ValueError):
            data = {}

    entry: dict[str, Any] = {"value": value}
    if provider:
        entry["provider"] = provider
    data[name] = entry
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    try:
        os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass


def list_credentials(home: Path) -> list[dict[str, Any]]:
    """Return all credentials from the vault file.

    Each entry has keys ``name``, ``value``, and optionally ``provider``.
    Returns an empty list if the file does not exist or is unparseable.
    """
    path = credentials_path(home)
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(data, dict):
        return []

    result: list[dict[str, Any]] = []
    for name, entry in data.items():
        if isinstance(entry, dict):
            result.append({
                "name": name,
                "value": entry.get("value", ""),
                "provider": entry.get("provider"),
            })
        else:
            # Backward compat: flat ``{name: value}`` format.
            result.append({
                "name": name,
                "value": entry,
                "provider": None,
            })
    return result


def delete_credential(home: Path, name: str) -> None:
    """Remove a single credential from the vault file.

    No-op if the key does not exist or the file is missing.
    """
    path = credentials_path(home)
    if not path.exists():
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return

    if not isinstance(data, dict):
        return

    data.pop(name, None)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
