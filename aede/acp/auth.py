from __future__ import annotations
import asyncio
from dataclasses import dataclass, field


class AuthStep:
    """Base for events the auth engine yields to an adapter."""


@dataclass(frozen=True)
class NeedsBrowser(AuthStep):
    method_id: str


@dataclass(frozen=True)
class NeedsTerminal(AuthStep):
    command: str
    args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NeedsKey(AuthStep):
    env_var: str


@dataclass(frozen=True)
class Progress(AuthStep):
    message: str


@dataclass(frozen=True)
class Connected(AuthStep):
    session_id: str


@dataclass(frozen=True)
class Failed(AuthStep):
    reason: str


from typing import Optional
from .client import AcpError

AUTH_REQUIRED_CODE = -32000

_TERMINAL_AUTH = {
    "claude-code": ("claude", ["auth", "login"]),
}


def is_auth_required(err: AcpError) -> bool:
    return err.code == AUTH_REQUIRED_CODE


def terminal_auth_for(agent_name: str) -> Optional[tuple[str, list[str]]]:
    for prefix, spec in _TERMINAL_AUTH.items():
        if agent_name == prefix or agent_name.startswith(prefix + "/") \
                or agent_name.startswith(prefix + "\\"):
            return spec
    return None


def _client_auth_methods(client):
    return client._init_result.auth_methods if hasattr(client, '_init_result') else []


def _first_method_of_type(methods, type_):
    for m in methods:
        if isinstance(m, dict) and m.get("type") == type_:
            return m.get("id")
    return None


async def drive_auth(agent_name, client, vault, registry, _meta=None):
    try:
        client._init_result = await client.initialize(credential_provider=vault)
    except FileNotFoundError:
        raise
    except (AcpError, OSError, TimeoutError, asyncio.TimeoutError) as exc:
        if isinstance(exc, AcpError):
            yield Failed(reason=exc.message)
        else:
            yield Failed(reason=str(exc))
        return
    try:
        session_id = await client.new_session(cwd="", _meta=_meta)
        yield Connected(session_id=session_id)
        return
    except (AcpError, OSError, TimeoutError, asyncio.TimeoutError) as exc:
        if isinstance(exc, AcpError):
            if not is_auth_required(exc):
                yield Failed(reason=exc.message)
                return
            err = exc
        else:
            yield Failed(reason=str(exc))
            return

        config = registry.get(agent_name) if registry else None
        key = None
        if vault and config is not None:
            try:
                key = vault.get_for_agent(config)
            except KeyError:
                key = None
        if key:
            yield Progress(message=f"Using stored key for {agent_name}")
            try:
                yield Connected(session_id=await client.new_session(cwd="", _meta=_meta))
                return
            except (AcpError, OSError, TimeoutError, asyncio.TimeoutError) as e2:
                if isinstance(e2, AcpError):
                    err = e2
                else:
                    yield Failed(reason=str(e2))
                    return

        agent_method = _first_method_of_type(_client_auth_methods(client), "agent")
        if agent_method:
            yield NeedsBrowser(method_id=agent_method)
            yield Progress(message="Opening browser to log in...")
            try:
                await asyncio.wait_for(client.authenticate(agent_method), timeout=30)
            except (TimeoutError, asyncio.TimeoutError, OSError) as e:
                yield Failed(reason=f"Authentication timeout or error: {e}")
                return
            try:
                yield Connected(session_id=await client.new_session(cwd="", _meta=_meta))
                return
            except (AcpError, OSError, TimeoutError, asyncio.TimeoutError) as e3:
                reason = e3.message if isinstance(e3, AcpError) else str(e3)
                yield Failed(reason=reason)
                return

        term = terminal_auth_for(agent_name)
        if term:
            yield NeedsTerminal(command=term[0], args=term[1])
            yield Failed(
                reason=(
                    f"Terminal auth required — "
                    f"run '{term[0]} {' '.join(term[1])}' then re-drive"
                )
            )
            return

        yield Failed(reason=err.message if isinstance(err, AcpError) else str(err))
