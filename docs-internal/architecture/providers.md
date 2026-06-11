---
type: internal-doc
tags: [docs-internal, architecture]
date_updated: 2026-06-10
---

# Provider Abstraction

**File:** `aede/provider.py` (731 lines)

## Architecture

```
get_provider(cfg) → AnthropicProvider | OpenAIProvider | AcpProvider
```

## NormalizedResponse (`aede/provider.py:19-30`)

Universal response dataclass bridging provider SDKs to the [[agent-loop.md|AgentLoop]]:

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Assistant text response |
| `tool_calls` | `list[dict]` | `[{"id", "name", "input"}]` |
| `input_tokens` | `int` | Prompt tokens |
| `output_tokens` | `int` | Completion tokens |
| `cached_tokens` | `int` | Cache-read tokens |
| `assistant_content_blocks` | `list[Any]` | Anthropic-format blocks for history round-tripping |

## Provider Protocol (`aede/provider.py:33-51`)

```python
@runtime_checkable
class Provider(Protocol):
    async def stream_turn(self, *, model, system, tools, messages, max_tokens,
                          console, reasoning_effort, thinking_budget,
                          stream_text, stream_thinking) -> NormalizedResponse: ...
```

## AnthropicProvider (`aede/provider.py:58-190`)

- Uses `anthropic.AsyncAnthropic` SDK (lazy import at line 67)
- Two-block system prompt with `cache_control: ephemeral` on stable prefix (`aede/provider.py:102-112`)
- Cache injection on last message for KV-cache reuse (`aede/provider.py:119-137`)
- Thinking mode via `stream_kwargs["thinking"]` for both `reasoning_effort` and `thinking_budget` (`aede/provider.py:92-97`)
- Streaming: `client.messages.stream()` context manager, handles `content_block_start`, `content_block_delta` (thinking + text), `get_final_message()` (`aede/provider.py:139-189`)

## OpenAIProvider (`aede/provider.py:328-515`)

- Uses `openai.AsyncOpenAI` SDK (lazy import at line 342)
- Message conversion: `_convert_messages_to_openai()` at line 197 handles Anthropic→OpenAI format (tool_result→"tool", tool_use→tool_calls, text blocks)
- Tool conversion: `_convert_tools_to_openai()` at line 308 (Anthropic `input_schema` → OpenAI `function.parameters`)
- Reasoning effort mapping: DeepSeek (`aede/provider.py:375-386`), Gemini (`aede/provider.py:387-394`), OpenAI passthrough (`aede/provider.py:396-397`)
- Fragmented `tool_call` delta accumulation across streaming chunks (`aede/provider.py:445-459`)
- Usage from `stream_options={"include_usage": True}` (`aede/provider.py:419`)

## AcpProvider (`aede/provider.py:536-646`)

- Routes to ACP agents via `AcpManager` (`aede/provider.py:543-554`)
- Resolves base agent + sub-model override from model id (`aede/provider.py:576-582`)
- Auto-connect/disconnect/switch via manager (`aede/provider.py:587-605`)
- `_build_prompt_text()` converts Anthropic message history to plain text prompt (`aede/provider.py:648-670`)
- Returns `NormalizedResponse` with token counts = 0 (ACP agents don't report usage)

## Selection logic (`aede/provider.py:677-731`)

`get_provider()` rules:
1. Model in `ACP_MODEL_IDS` → `AcpProvider` (requires `acp_manager`)
2. Model starts with `deepseek-` → `OpenAIProvider` with `DEEPSEEK_API_KEY`
3. `api_base_url` set + non-Anthropic model → `OpenAIProvider` (uses `OPENROUTER_API_KEY` or `OPENAI_API_KEY`)
4. Otherwise → `AnthropicProvider` (requires `ANTHROPIC_API_KEY`)
