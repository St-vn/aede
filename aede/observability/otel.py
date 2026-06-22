"""
OpenTelemetry adapter for agent turn tracing.

Provides an ``OTelTracer`` that emits one root span per agent turn with
child spans per tool call.  Controlled by the ``otel_endpoint`` config key:
when set, spans are exported via OTLP gRPC; when unset (default), the tracer
is a no-op so personal installs don't phone home.
"""

from __future__ import annotations

from typing import Any


class OTelTracer:
    """Bridges agent turns to OpenTelemetry spans.

    Args:
        endpoint: OTLP gRPC endpoint (e.g. ``http://localhost:4317``).
            When ``None`` the tracer is a no-op.
        service_name: Logical service name for the OTel resource.
    """

    def __init__(
        self, endpoint: str | None = None, service_name: str = "aede"
    ) -> None:
        self._tracer = None
        self._provider = None
        self.enabled = False
        if endpoint:
            self._setup(endpoint, service_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _from_provider(cls, provider: Any) -> OTelTracer:
        """Build an OTelTracer from an already-configured TracerProvider.

        Used in tests that inject a provider wired to an in-memory exporter.
        """
        tracer = cls.__new__(cls)
        tracer._provider = provider
        tracer._tracer = provider.get_tracer(__name__)
        tracer.enabled = True
        return tracer

    def _setup(self, endpoint: str, service_name: str) -> None:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        resource = Resource.create({"service.name": service_name})
        self._provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        self._provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(__name__)
        self.enabled = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_turn(
        self,
        session_id: str,
        turn_number: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        tool_calls: list[dict[str, Any]],
        reasoning_text: str,
        outcome: str,
    ) -> None:
        """Record an agent turn as an OTel span tree.

        Creates one root span for the turn, with a child span for each tool
        call.  Only active when *enabled* is ``True``.
        """
        if not self.enabled:
            return

        from opentelemetry import trace

        with self._tracer.start_as_current_span(
            f"turn.{turn_number}",
            attributes={
                "session_id": session_id,
                "turn_number": turn_number,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_tokens": cached_tokens,
                "outcome": outcome,
            },
        ) as turn_span:
            if reasoning_text:
                turn_span.add_event("reasoning", {"text": reasoning_text[:5000]})

            for tc in tool_calls:
                with self._tracer.start_as_current_span(
                    tc.get("name", "unknown_tool"),
                    attributes={
                        "tool_name": tc.get("name", ""),
                        "duration_ms": tc.get("duration_ms", 0),
                        "passed": tc.get("passed", True),
                    },
                ) as tool_span:
                    args = tc.get("args")
                    if args:
                        tool_span.set_attribute(
                            "tool.args", str(args)[:2000]
                        )

    def shutdown(self) -> None:
        """Flush and shut down the tracer provider (idempotent)."""
        if self._provider:
            self._provider.shutdown()
            self._provider = None
