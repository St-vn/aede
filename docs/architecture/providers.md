---
type: doc
tags: [docs, architecture]
date_updated: 2026-06-10
---

# LLM Providers

aede abstracts LLM access behind a provider interface, supporting multiple backends.

## Provider Selection

The `get_provider()` function selects the appropriate provider based on configuration:

- **DeepSeek models** (`deepseek-*`) → `OpenAIProvider` with `DEEPSEEK_API_KEY`
- **`api_base_url` set** + non-Anthropic model → `OpenAIProvider` with the configured base URL
- **All others** → `AnthropicProvider` with `ANTHROPIC_API_KEY`

ACP agents (e.g., `claude-code`, `codex`, `goose`) are intercepted before provider selection and routed to the ACP manager instead.

## AnthropicProvider

Uses the `anthropic.AsyncAnthropic` SDK with:

- Streaming via `client.messages.stream()`
- Two-block system prompt with `cache_control: ephemeral` on the stable prefix
- Cache injection on the last message for KV-cache reuse
- Thinking mode support with configurable `reasoning_effort` and `thinking_budget`

## OpenAIProvider

Uses the `openai.AsyncOpenAI` SDK with:

- Message format conversion from Anthropic to OpenAI schema
- Tool schema conversion
- Reasoning effort mapping for DeepSeek, Gemini, and OpenAI models
- Fragmented tool_call delta accumulation across streaming chunks

## Provider Protocol

All providers implement a common protocol:

```python
async def stream_turn(
    model, system, tools, messages, max_tokens,
    console, reasoning_effort, thinking_budget
) -> NormalizedResponse
```

This allows the AgentLoop to be provider-agnostic. The `NormalizedResponse` returns text, tool calls, and token counts in a standard format.
