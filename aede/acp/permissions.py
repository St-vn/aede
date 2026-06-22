from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

from aede.gate import PermissionStore


class AcpPermissionOutcome(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    CANCELLED = "cancelled"


@dataclass
class PermissionResult:
    outcome: AcpPermissionOutcome
    option_id: str = ""


class AcpPermissionBridge:
    def __init__(self, store: PermissionStore) -> None:
        self._store = store

    def resolve(
        self,
        tool_call_id: str,
        options: list[dict],
        choice: str,
    ) -> PermissionResult:
        if self._store.is_allowed(f"acp__{tool_call_id}"):
            # already auto-approved — treat as allow
            for opt in options:
                if opt["optionId"] == choice:
                    return PermissionResult(
                        outcome=AcpPermissionOutcome.ALLOWED,
                        option_id=choice,
                    )

        kind_map = {
            "allow_once": AcpPermissionOutcome.ALLOWED,
            "allow_always": AcpPermissionOutcome.ALLOWED,
            "reject_once": AcpPermissionOutcome.DENIED,
            "reject_always": AcpPermissionOutcome.DENIED,
        }

        selected_kind = None
        for opt in options:
            if opt["optionId"] == choice:
                selected_kind = opt["kind"]
                break

        if selected_kind is None:
            return PermissionResult(
                outcome=AcpPermissionOutcome.DENIED,
                option_id=choice,
            )

        outcome = kind_map.get(selected_kind, AcpPermissionOutcome.DENIED)

        if selected_kind == "allow_always":
            self._store.allow_session(f"acp__{tool_call_id}")

        return PermissionResult(
            outcome=outcome,
            option_id=choice,
        )

    def resolve_cancelled(self, tool_call_id: str) -> PermissionResult:
        return PermissionResult(
            outcome=AcpPermissionOutcome.CANCELLED,
        )
