# aede

A personal CLI agent harness wrapping Claude (pronounced "aid").

**Phase 1** is implemented (168 tests passing) — an early, single-user personal tool. Supports agentic workflows across coding, planning, research, and general task execution on Windows.

## Features

- **Agent loop** with streaming output
- **Eight tools**: powershell, read_file, write_file, create_file, list_dir, search_files, fetch_url, web_search
- **Approval gate** for dangerous operations (shell, file writes)
- **Session management** with persistence, branching, and resume
- **Context compaction** (85% threshold) with hide-don't-delete audit trail
- **Configuration** system (global `~/.aede/config.yml`, project `./aede.yml`, session-level)
- **Slash commands**: `/help`, `/keybinds`, `/resume`, `/sessions`, `/tools`, `/config`, `/compact`, `/tokens`, `/setkey`, `/clear`, `/exit`
- **Token tracking** with KV-cache hit rate and estimated cost
- **Voice input** — push-to-talk and wake word detection with multi-provider ASR (Groq, OpenAI, OpenRouter, Google) and browser-native fallback
- **Pydantic validation** with retry-once on parameter errors
- **API resilience**: exponential backoff on 429/500 errors

## Install & Run

```bash
uv sync
uv run aede
```

Or pass a task inline:
```bash
uv run aede "read the docs and summarize the architecture"
```

## Configuration

**Required environment variable:**
- `ANTHROPIC_API_KEY` — your Anthropic API key

**Optional:**
- `EDITOR` — for `/config` editing (defaults to `notepad.exe` on Windows)

**Credential vault (optional):**
- `~/.aede/credentials.json` — additional API keys (env vars take precedence)

## Status

Phase 1 complete with 168 tests passing. Active development; Phase 2 (sandboxing, memory, expanded tools) planned.

## License

MIT — see [LICENSE](LICENSE).
