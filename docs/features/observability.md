---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Observability

## OpenTelemetry (P0.6)

`OTelTracer` emits distributed traces for each agent turn, with child spans per tool call, via OTLP gRPC. Configured through:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `otel_endpoint` | string | `null` | OTLP gRPC endpoint (e.g. `http://localhost:4317`). `null` = no-op |
| `otel_service_name` | string | `"aede"` | Service name in OTel resource attributes |

When `otel_endpoint` is `null` the tracer is a complete no-op — zero overhead, no allocations. Enable by pointing it at any OTLP-compatible collector (Grafana Tempo, Jaeger, Honeycomb, etc.).

## FDE — Fair Data Ethics Capture (P0.7)

`FdeCapture` logs all tool calls with automatic PII/secret redaction. Output goes to local JSONL files in `~/.aede/data/fde/` and optionally forwards to a remote endpoint.

### Redaction

`redact_value()` strips API keys, emails, SSNs, credit card numbers, file paths, and keys matching a denylist before any data leaves the process. The redaction runs before both local write and HTTP POST.

### Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `fde_enabled` | bool | `false` | Enable FDE capture |
| `fde_endpoint` | string | `null` | Remote endpoint for FDE forwarding (optional) |
