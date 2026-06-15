from __future__ import annotations

import copy
import re
from typing import Any


_REDACTED = "<REDACTED>"

_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"sk-[a-zA-Z0-9\-_]{10,}"),
    re.compile(r"api[-_]?key[-_]?[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9+/=]{40,}"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"~[/\\](?:[^/\\]+[/\\])*[^/\\]+"),
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]

_DEFAULT_DENYLIST: set[str] = {
    "api_key", "apikey", "api-key",
    "api_secret", "apisecret", "api-secret",
    "access_token", "accesstoken", "access-token",
    "secret_key", "secretkey", "secret-key",
    "password", "passwd", "pass",
    "authorization", "auth",
    "token",
    "private_key", "privatekey", "private-key",
    "ssh_key", "sshkey", "ssh-key",
}


def _is_secret(value: str) -> bool:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(value):
            return True
    return False


def _redact_string(value: str) -> str:
    if len(value) < 8:
        return value
    if not _is_secret(value):
        return value
    return _REDACTED


def redact_value(
    value: Any,
    allowlist: set[str] | None = None,
    denylist: set[str] | None = None,
    _key: str | None = None,
    _depth: int = 0,
) -> Any:
    if _depth > 100:
        return value

    allowlist = allowlist or set()
    denylist = denylist or _DEFAULT_DENYLIST

    if _key is not None and _key in allowlist:
        return value

    if _key is not None and _key in denylist:
        return _REDACTED

    if isinstance(value, dict):
        return {
            k: redact_value(v, allowlist=allowlist, denylist=denylist, _key=k, _depth=_depth + 1)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            redact_value(v, allowlist=allowlist, denylist=denylist, _key=_key, _depth=_depth + 1)
            for v in value
        ]

    if isinstance(value, str):
        return _redact_string(value)

    return value
