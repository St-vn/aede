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

        client = AcpClient(config)
        try:
            client.initialize(credential_provider=self._credential_provider)
        except FileNotFoundError:
            raise AcpConnectionError(
                f"Agent '{agent_name}' not found: "
                f"command '{config.command}' not available"
            )
        except AcpError as e:
            raise AcpConnectionError(
                f"Agent '{agent_name}' protocol error (code {e.code}): {e.message}"
            ) from e
        except Exception as e:
            raise AcpConnectionError(
                f"Failed to connect to agent '{agent_name}': {e}"
            ) from e

        session = AcpSession(client)
        session_id = session.create(cwd="")
        self._sessions[agent_name] = AgentSession(
            name=agent_name,
            client=client,
            session=session,
            session_id=session_id,
        )
        self._active_name = agent_name
        return session_id

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
