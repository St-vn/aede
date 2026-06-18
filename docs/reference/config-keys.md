---
type: doc
tags: [docs, reference]
date_updated: 2026-06-16
---

# Config Keys

## General

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model` | string | `claude-sonnet-4-20250514` | Active model ID |
| `context_window` | integer | 200000 | Token limit before compaction triggers |
| `compaction_threshold` | float | 0.85 | Fraction of window that triggers auto-compaction |
| `tool_output_max_tokens` | integer | 8000 | Max tokens per tool output before truncation |
| `batch_approval_max` | integer | 20 | Max tools in a batch approval group |
| `auto_approve` | list | `[]` | Tool names that skip the approval gate |

## Shell

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `shell` | string | `powershell` | Shell backend: `powershell`, `cmd`, or `wsl` |
| `wsl_distro` | string | `""` | WSL distro name (only used when `shell: wsl`) |

## API Provider

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_base_url` | string | `null` | OpenAI-compatible base URL (e.g., `https://openrouter.ai/api/v1`) |
| `model_prices` | object | `{}` | Price overrides per model (input/output/cache_read per million tokens) |

## Providers

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `providers` | object | `{}` | Named provider configs with `api_key_env` and `base_url` |
| `compaction_model` | string | `null` | Model ID for compaction summarization (null = use active model) |

## Reasoning

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `reasoning_effort` | string | `auto` | `auto`, `none`, `low`, `medium`, `high`, `xhigh`, `max` |
| `thinking_budget` | integer | 0 | Token budget for thinking (0 = auto, min 1024) |

## Critic

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `critic_enabled` | boolean | `false` | Enable asymmetric critic pass on code writes |
| `critic_model` | string | `null` | Separate model for critic (null = same as main) |
| `critic_api_base_url` | string | `null` | Base URL for critic model |

## Grounding

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `grounding_enabled` | boolean | `true` | Inject grounding instruction into system prompt |

## Voice

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `voice_input_enabled` | boolean | `false` | Enable push-to-talk mic button in the web UI |
| `voice_wake_word_enabled` | boolean | `false` | Enable continuous wake word listening |
| `voice_asr_model` | string | `whisper-large-v3-turbo` | ASR model for transcription (see [Voice](features/voice.md) for options) |
| `voice_wake_model` | string | `hey_jarvis` | Wake word model to detect (`hey_jarvis`, `alexa`, `hey_mycroft`, `hey_rhasspy`) |

## Sandbox

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sandbox` | object | `{}` | Sandbox config with `enabled`, `image`, `workspace_mount`, `memory_limit`, `cpu_limit`, `env` |

## Plugins

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `plugins` | object | `{}` | Plugin toggle config with `enabled` and `disabled` lists |

## Observability

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `otel_endpoint` | string | `null` | OTLP gRPC endpoint (null = no-op) |
| `otel_service_name` | string | `"aede"` | Service name in OTel resource attributes |
| `fde_enabled` | boolean | `false` | Enable fair-data-ethics capture |
| `fde_endpoint` | string | `null` | Remote FDE forwarding endpoint (optional) |

## Memory (Embeddings)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ollama_base_url` | string | `http://localhost:11434` | Ollama API endpoint |
| `ollama_embed_model` | string | `nomic-embed-text` | Embedding model name |
| `ollama_timeout_s` | integer | 5 | Ollama request timeout in seconds |
| `learnings_top_k` | integer | 5 | Top-k learnings to retrieve per turn |
| `learnings_max_tokens` | integer | 2000 | Max tokens for learnings suffix in system prompt |

## MCP

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mcp_servers` | object | `{}` | MCP server configurations (also accepts `mcpServers`) |
