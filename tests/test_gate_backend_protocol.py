# tests/test_gate_backend_protocol.py
import pytest, inspect
from aede.gate import GateBackend, TerminalGateBackend, GateDecision

def test_gate_backend_is_runtime_checkable_protocol():        
    assert getattr(GateBackend, '_is_protocol', False), \
        "GateBackend must be @runtime_checkable typing.Protocol"

def test_terminal_gate_backend_has_async_request():
    backend = TerminalGateBackend()
    assert callable(getattr(backend, 'request', None))        
    assert inspect.iscoroutinefunction(backend.request), "request must be async def"

def test_terminal_gate_backend_signature():
    backend = TerminalGateBackend()
    sig = inspect.signature(backend.request)
    for param in ('gate_id', 'tool_name', 'args', 'batch_count'):
        assert param in sig.parameters, f"Missing parameter: {param}"

def test_terminal_gate_backend_satisfies_protocol():
    backend = TerminalGateBackend()
    assert isinstance(backend, GateBackend)
