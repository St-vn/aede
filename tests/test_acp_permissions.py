import pytest
from pathlib import Path
from aede.acp.permissions import AcpPermissionBridge, AcpPermissionOutcome
from aede.gate import PermissionStore


def test_allow_once_maps_to_gate():
    """US-ACP-003 AC-1: allow_once → aede gate allow_once."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_001",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="allow-once",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED
    assert result.option_id == "allow-once"


def test_deny_maps_to_gate():
    """US-ACP-003 AC-3: reject_once → aede gate deny."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_002",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="reject-once",
    )

    assert result.outcome == AcpPermissionOutcome.DENIED
    assert result.option_id == "reject-once"


def test_always_allow_persists_to_store():
    """US-ACP-003 AC-2: always_allow → aede gate session-level allow."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="call_003",
        options=[
            {"optionId": "allow-always", "name": "Always allow", "kind": "allow_always"},
            {"optionId": "reject-once", "name": "Reject", "kind": "reject_once"},
        ],
        choice="allow-always",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED
    assert store.is_allowed("acp__call_003") is True


def test_cancelled():
    """US-ACP-003 AC-4: Cancelled prompt returns cancelled outcome."""
    store = PermissionStore()
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve_cancelled("call_004")

    assert result.outcome == AcpPermissionOutcome.CANCELLED


def test_pre_approved_passes_through():
    """If the tool was already allowed in the store, resolve automatically."""
    store = PermissionStore()
    store.allow_session("acp__read_file")
    bridge = AcpPermissionBridge(store)

    result = bridge.resolve(
        tool_call_id="read_file",
        options=[
            {"optionId": "allow-once", "name": "Allow once", "kind": "allow_once"},
        ],
        choice="allow-once",
    )

    assert result.outcome == AcpPermissionOutcome.ALLOWED
