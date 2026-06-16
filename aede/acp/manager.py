from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import json
import logging

from .client import AcpClient, AcpError
from .session import AcpSession
from .registry import AgentRegistry
from .credentials import CredentialProvider

logger = logging.getLogger(__name__)


class AcpConnectionError(Exception):
    pass


@dataclass
class AgentSession:
    name: str
    client: AcpClient
    session: AcpSession
    session_id: str


_SESSIONS_CACHE = "acp-sessions.json"


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

    # ── session persistence helpers ──

    @property
    def _sessions_cache_path(self) -> Path:
        from pathlib import Path
        return self._registry._path.parent / _SESSIONS_CACHE

    def _load_saved_session(self, agent_name: str) -> str | None:
        p = self._sessions_cache_path
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data.get(agent_name)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _save_saved_session(self, agent_name: str, session_id: str) -> None:
        p = self._sessions_cache_path
        data: dict[str, str] = {}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data[agent_name] = session_id
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _remove_saved_session(self, agent_name: str) -> None:
        p = self._sessions_cache_path
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data.pop(agent_name, None)
            if data:
                p.write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                p.unlink(missing_ok=True)
        except (json.JSONDecodeError, OSError):
            pass

    async def connect(self, agent_name: str, _meta: Optional[dict] = None) -> str:
        config = self._registry.get(agent_name)
        if agent_name in self._sessions:
            self._active_name = agent_name
            return self._sessions[agent_name].session_id

        # Session resume: if we have a saved session_id, try to resume it.
        saved_id = self._load_saved_session(agent_name)
        resume_meta: dict | None = None
        if saved_id is not None:
            resume_meta = {
                "claudeCode": {
                    "options": {
                        "resume": saved_id,
                    },
                },
            }
            # Merge with any caller-supplied _meta (caller wins on conflict)
            if _meta is not None:
                merged = dict(resume_meta)
                cc_opts = dict(resume_meta.get("claudeCode", {}).get("options", {}))
                caller_cc = _meta.get("claudeCode", {})
                if isinstance(caller_cc, dict):
                    caller_opts = caller_cc.get("options", {})
                    if isinstance(caller_opts, dict):
                        cc_opts.update(caller_opts)
                merged.setdefault("claudeCode", {})["options"] = cc_opts
                resume_meta = merged

        from .auth import drive_auth, Connected, Failed, NeedsKey, NeedsBrowser, NeedsTerminal

        async def _drive(meta: dict | None) -> str | None:
            """Run one auth/connect attempt. Returns session_id, or raises
            AcpConnectionError on Failed. Returns None if no step connected."""
            client = AcpClient(config)
            try:
                async for step in drive_auth(agent_name, client=client,
                                             vault=self._credential_provider,
                                             registry=self._registry,
                                             _meta=meta):
                    if isinstance(step, Connected):
                        session = AcpSession(client)
                        session.adopt(step.session_id)
                        self._sessions[agent_name] = AgentSession(
                            name=agent_name, client=client, session=session,
                            session_id=step.session_id)
                        self._active_name = agent_name
                        self._save_saved_session(agent_name, step.session_id)
                        return step.session_id
                    if isinstance(step, Failed):
                        await client.aclose()
                        raise AcpConnectionError(step.reason)
            except FileNotFoundError:
                hint = "Install Node.js from https://nodejs.org" if config.command in ("npx", "node") else f"Make sure '{config.command}' is installed and in PATH"
                raise AcpConnectionError(
                    f"Agent '{agent_name}' not found: command '{config.command}' not available. {hint}")
            return None

        try:
            session_id = await _drive(resume_meta if resume_meta else _meta)
        except AcpConnectionError:
            # Resume is best-effort: a saved session can expire or be cleared on
            # the agent side, which surfaces as a non-auth "Resource not found"
            # Failed step.  Drop the stale id and retry once with a fresh
            # session/new rather than propagating a 500.
            if resume_meta is None:
                raise
            logger.info(
                "ACP resume failed for %s; clearing saved session and retrying fresh",
                agent_name)
            self._remove_saved_session(agent_name)
            session_id = await _drive(_meta)

        if session_id is not None:
            return session_id
        raise AcpConnectionError(f"Agent '{agent_name}' did not connect")

    async def new_session(self, agent_name: str, _meta: Optional[dict] = None) -> str:
        """Create a new ACP session on the *existing* subprocess for *agent_name*.

        Unlike ``connect()``, this does NOT kill and re-spawn the agent process.
        It sends a fresh ``session/new`` to the already-running agent, which is
        much lighter — useful for changing thinking budget or session options
        without a full disconnect/reconnect cycle.

        If the agent is not yet connected, falls back to ``connect()``.
        """
        if agent_name not in self._sessions:
            logger.info("ACP new_session: %s not connected, calling connect()", agent_name)
            return await self.connect(agent_name, _meta=_meta)

        existing = self._sessions[agent_name]
        session_id = await existing.client.new_session(
            cwd="",
            mcp_servers=[],
            _meta=_meta,
        )
        session_wrapper = AcpSession(existing.client)
        session_wrapper.adopt(session_id)
        self._sessions[agent_name] = AgentSession(
            name=agent_name,
            client=existing.client,
            session=session_wrapper,
            session_id=session_id,
        )
        self._active_name = agent_name
        self._save_saved_session(agent_name, session_id)
        logger.debug("ACP new_session for %s: %s", agent_name, session_id[:12])
        return session_id

    def switch_to(self, agent_name: str) -> None:
        if agent_name not in self._sessions:
            raise KeyError(
                f"Not connected to agent '{agent_name}'"
            )
        self._active_name = agent_name

    async def disconnect(self, agent_name: str) -> None:
        if agent_name not in self._sessions:
            return
        await self._sessions[agent_name].client.aclose()
        del self._sessions[agent_name]
        self._remove_saved_session(agent_name)
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
