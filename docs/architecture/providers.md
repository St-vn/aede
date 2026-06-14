---
type: doc
tags: [docs, architecture]
date_updated: 2026-06-14
---

# LLM Providers

aede abstracts LLM access behind a provider interface, supporting multiple backends.

## Provider Selection

The `get_provider()` function selects the appropriate provider based on configuration:

- **DeepSeek models** (`deepseek-*`) → `OpenAIProvider` with `DEEPSEEK_API_KEY`
- **`api_base_url` set** + non-Anthropic model → `OpenAIProvider` with the configured base URL
- **OpenCode Zen models** (in `ZEN_MODEL_IDS`) → `OpenAIProvider` with `OPENCODE_ZEN_API_KEY`, base URL `https://opencode.ai/zen/v1`
- **OpenCode Go models** (in `GO_MODEL_IDS`) → `OpenAIProvider` with `OPENCODE_GO_API_KEY`, base URL `https://opencode.ai/zen/go`
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

## OpenCode Zen and Go

Both Zen and Go reuse `OpenAIProvider` with no subclass required. Authentication is via Bearer token read from dedicated environment variables.

- **Zen** (`https://opencode.ai/zen/v1`): pay-as-you-go plus free models — 7 free and 8 paid chat-completions models.
- **Go** (`https://opencode.ai/zen/go`): $10/month subscription covering 6 models.

Both tiers use the standard `/v1/chat/completions` endpoint.

The `cfg.providers` block can override `api_key_env` and `base_url` per named provider, allowing per-deployment customization without code changes.

GPT models (which require the Responses API) and Claude models (which require the Messages API) routed through Zen are out of scope — use direct `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for those models instead.

## Provider Protocol

All providers implement a common protocol:

```python
async def stream_turn(
    model, system, tools, messages, max_tokens,
    console, reasoning_effort, thinking_budget
) -> NormalizedResponse
```

This allows the AgentLoop to be provider-agnostic. The `NormalizedResponse` returns text, tool calls, and token counts in a standard format.
