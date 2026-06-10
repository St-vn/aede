from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .client import AcpClient, AcpError
from .session import AcpSession
from .registry import AgentRegistry
from .credentials import CredentialProvider


class AcpConnectionError(Exception):
    pass


@dataclass
class AgentSession:
    name: str
    client: AcpClient
    session: AcpSession
    session_id: str


class AcpManager:
    def __init__(
        self,
        registry: AgentRegistry,
        credential_provider: CredentialProvider,
    ) -> None:
        self._registry = registry
        self._credential_provider = credential_provider
        self._sessions: dict[str, AgentSession] = {}
        self._active_name: Optional[str] = None

    def connect(self, agent_name: str) -> str:
        config = self._registry.get(agent_name)
        if agent_name in self._sessions:
            self._active_name = agent_name
            return self._sessions[agent_name].session_id

        from .auth import drive_auth, Connected, Failed, NeedsKey, NeedsBrowser, NeedsTerminal
        client = AcpClient(config)
        try:
            for step in drive_auth(agent_name, client=client,
                                   vault=self._credential_provider, registry=self._registry):
                if isinstance(step, Connected):
                    session = AcpSession(client)
                    # The ACP session was already created during the auth
                    # handshake (drive_auth -> client.new_session). Adopt that
                    # id instead of calling create() again, which would spawn a
                    # redundant second session.
                    session.adopt(step.session_id)
                    self._sessions[agent_name] = AgentSession(
                        name=agent_name, client=client, session=session,
                        session_id=step.session_id)
                    self._active_name = agent_name
                    return step.session_id
                if isinstance(step, Failed):
                    client.close()
                    raise AcpConnectionError(step.reason)
        except FileNotFoundError:
            hint = f"Install Node.js from https://nodejs.org" if config.command in ("npx", "node") else f"Make sure '{config.command}' is installed and in PATH"
            raise AcpConnectionError(
                f"Agent '{agent_name}' not found: command '{config.command}' not available. {hint}")
        raise AcpConnectionError(f"Agent '{agent_name}' did not connect")

    def switch_to(self, agent_name: str) -> None:
        if agent_name not in self._sessions:
            raise KeyError(
                f"Not connected to agent '{agent_name}'"
            )
        self._active_name = agent_name

    def disconnect(self, agent_name: str) -> None:
        if agent_name not in self._sessions:
            return
        self._sessions[agent_name].client.close()
        del self._sessions[agent_name]
        if self._active_name == agent_name:
            self._active_name = next(iter(self._sessions), None)

    def active_session(self) -> Optional[AgentSession]:
        if not self._active_name:
            return None
        return self._sessions.get(self._active_name)

    def active_session_id(self) -> Optional[str]:
        session = self.active_session()
        return session.session_id if session else None

    def list_connected(self) -> list[str]:
        return list(self._sessions.keys())
