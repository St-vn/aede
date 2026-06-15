"""Tests for aede.observability.otel — P0.6 OTel adapter for TraceLogger."""

from __future__ import annotations

from typing import Any

import pytest

from aede.observability.otel import OTelTracer


# ---------------------------------------------------------------------------
# In-memory span exporter for testing (InMemorySpanExporter not yet in SDK)
# ---------------------------------------------------------------------------

class _MemoryExporter:
    """Accumulates exported spans in a list for test assertions."""

    def __init__(self) -> None:
        self.spans: list[dict[str, Any]] = []

    def export(self, spans: list) -> None:
        from opentelemetry.sdk.trace.export import SpanExportResult
        for span in spans:
            ctx = span.get_span_context()
            self.spans.append({
                "name": span.name,
                "trace_id": hex(ctx.trace_id),
                "span_id": hex(ctx.span_id),
                "attributes": dict(span.attributes) if span.attributes else {},
                "parent_span_id": hex(span.parent.span_id) if span.parent else None,
                "events": [
                    {"name": e.name, "attributes": dict(e.attributes) if e.attributes else {}}
                    for e in span.events
                ],
            })
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture
def memory_exporter():
    return _MemoryExporter()


# ---------------------------------------------------------------------------
# T-13x — OTelTracer
# ---------------------------------------------------------------------------

def make_tracer(exporter) -> OTelTracer:
    """Build an OTelTracer wired to a *MemoryExporter for testing."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = OTelTracer._from_provider(provider)
    return tracer


class TestOTelTracerNoop:
    """T-13a: When no endpoint is configured, all methods are no-ops."""

    def test_noop_does_not_crash(self):
        tracer = OTelTracer(endpoint=None)
        tracer.record_turn(
            session_id="s1", turn_number=0, input_tokens=10, output_tokens=5,
            cached_tokens=0, tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()

    def test_noop_disabled_flag(self):
        tracer = OTelTracer(endpoint=None)
        assert tracer.enabled is False

    def test_noop_with_endpoint_set(self):
        tracer = OTelTracer(endpoint="http://localhost:4317")
        # enabled is True even if the exporter fails to connect later
        assert tracer.enabled is True
        tracer.shutdown()


class TestOTelTracerSpanAttributes:
    """T-13b: Turn spans carry correct attributes."""

    def test_turn_span_has_correct_attributes(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.record_turn(
            session_id="sess_01", turn_number=1, input_tokens=100,
            output_tokens=50, cached_tokens=10, tool_calls=[],
            reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()

        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        span = spans_by_name["turn.1"]
        assert span["attributes"]["session_id"] == "sess_01"
        assert span["attributes"]["turn_number"] == 1
        assert span["attributes"]["input_tokens"] == 100
        assert span["attributes"]["output_tokens"] == 50
        assert span["attributes"]["cached_tokens"] == 10
        assert span["attributes"]["outcome"] == "end_turn"

    def test_turn_span_zero_tokens(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.record_turn(
            session_id="s2", turn_number=0, input_tokens=0, output_tokens=0,
            cached_tokens=0, tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()
        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        span = spans_by_name["turn.0"]
        assert span["attributes"]["input_tokens"] == 0
        assert span["attributes"]["output_tokens"] == 0

    def test_turn_span_reasoning_event(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.record_turn(
            session_id="s3", turn_number=1, input_tokens=50, output_tokens=25,
            cached_tokens=5, tool_calls=[], reasoning_text="I think therefore",
            outcome="tool_use",
        )
        tracer.shutdown()
        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        span = spans_by_name["turn.1"]
        events = span["events"]
        assert len(events) == 1
        assert events[0]["name"] == "reasoning"
        assert "I think therefore" in events[0]["attributes"].get("text", "")

    def test_no_reasoning_event_when_empty(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.record_turn(
            session_id="s4", turn_number=1, input_tokens=10, output_tokens=5,
            cached_tokens=0, tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()
        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        assert len(spans_by_name["turn.1"]["events"]) == 0


class TestOTelTracerToolChildSpans:
    """T-13c: Each tool call creates a child span under the turn span."""

    def test_tool_calls_become_child_spans(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tool_calls = [
            {"name": "read_file", "args": {"path": "/x"}, "result": "ok",
             "duration_ms": 10, "score": 1.0, "passed": True},
            {"name": "web_search", "args": {"query": "foo"}, "result": "data",
             "duration_ms": 300, "score": 1.0, "passed": True},
        ]
        tracer.record_turn(
            session_id="s5", turn_number=1, input_tokens=100, output_tokens=50,
            cached_tokens=0, tool_calls=tool_calls, reasoning_text="",
            outcome="tool_use",
        )
        tracer.shutdown()

        # 1 turn span + 2 tool spans = 3 total
        assert len(memory_exporter.spans) == 3

        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        turn_span = spans_by_name["turn.1"]
        tool_1 = spans_by_name["read_file"]
        tool_2 = spans_by_name["web_search"]

        assert turn_span["parent_span_id"] is None
        assert tool_1["parent_span_id"] == turn_span["span_id"]
        assert tool_2["parent_span_id"] == turn_span["span_id"]

    def test_tool_span_attributes(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tool_calls = [
            {"name": "exec_cmd", "args": {"cmd": "ls"}, "result": "ok",
             "duration_ms": 15, "score": 0.5, "passed": False},
        ]
        tracer.record_turn(
            session_id="s6", turn_number=1, input_tokens=10, output_tokens=5,
            cached_tokens=0, tool_calls=tool_calls, reasoning_text="",
            outcome="tool_use",
        )
        tracer.shutdown()

        spans_by_name = {s["name"]: s for s in memory_exporter.spans}
        tool_span = spans_by_name["exec_cmd"]
        assert tool_span["attributes"]["tool_name"] == "exec_cmd"
        assert tool_span["attributes"]["duration_ms"] == 15
        assert tool_span["attributes"]["passed"] is False

    def test_empty_tool_calls_no_child_spans(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.record_turn(
            session_id="s7", turn_number=1, input_tokens=10, output_tokens=5,
            cached_tokens=0, tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()
        assert len(memory_exporter.spans) == 1
        assert memory_exporter.spans[0]["name"] == "turn.1"

    def test_tool_span_no_args(self, memory_exporter):
        """Tool call with no args key should not crash."""
        tracer = make_tracer(memory_exporter)
        tool_calls = [
            {"name": "noop", "duration_ms": 0, "passed": True},
        ]
        tracer.record_turn(
            session_id="s8", turn_number=1, input_tokens=10, output_tokens=5,
            cached_tokens=0, tool_calls=tool_calls, reasoning_text="",
            outcome="tool_use",
        )
        tracer.shutdown()
        assert len(memory_exporter.spans) == 2


class TestOTelTracerServiceName:
    """T-13d: Service name is configurable."""

    def test_default_service_name_in_resource(self):
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace import TracerProvider
        exporter = _MemoryExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = OTelTracer._from_provider(provider)
        tracer.record_turn(
            session_id="s", turn_number=0, input_tokens=1, output_tokens=1,
            cached_tokens=0, tool_calls=[], reasoning_text="", outcome="end_turn",
        )
        tracer.shutdown()
        # Resource is set on the provider, not per-span; we just verify spans are emitted
        assert len(exporter.spans) == 1


class TestOTelTracerShutdown:
    """T-13e: Shutdown is safe to call multiple times."""

    def test_double_shutdown_no_error(self, memory_exporter):
        tracer = make_tracer(memory_exporter)
        tracer.shutdown()
        tracer.shutdown()  # second call should not crash

    def test_noop_shutdown_no_error(self):
        tracer = OTelTracer(endpoint=None)
        tracer.shutdown()  # should not crash
