from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from .client import AcpClient


@dataclass
class PromptResult:
    stop_reason: str
    text: str
    raw: dict


class AcpSession:
    def __init__(self, client: AcpClient) -> None:
        self._client = client
        self._session_id: Optional[str] = None

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def create(
        self,
        cwd: str = "",
        mcp_servers: Optional[list] = None,
    ) -> str:
        self._session_id = self._client.new_session(cwd=cwd, mcp_servers=mcp_servers)
        return self._session_id

    def prompt(
        self,
        text: str,
        message_id: str = "msg_1",
        on_update: Optional[callable] = None,
    ) -> PromptResult:
        if not self._session_id:
            raise RuntimeError("Session not created yet. Call create() first.")
        raw = self._client.prompt(
            session_id=self._session_id,
            text=text,
            message_id=message_id,
            on_update=on_update,
        )
        return PromptResult(
            stop_reason=raw.get("stopReason", "end_turn"),
            text=raw.get("text", ""),
            raw=raw,
        )
