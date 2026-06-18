---
type: doc
tags: [docs, developer]
date_updated: 2026-06-16
---

# Tests

## Running Tests

```bash
uv run pytest              # run all tests
uv run pytest -xvs         # verbose, stop on first failure
uv run pytest tests/test_file.py  # run a specific test file
```

## Test Configuration

Tests are configured in `pyproject.toml` with `asyncio_mode = "auto"`, so async test functions are detected automatically. The fixture `tmp_home` in `tests/conftest.py` redirects `~/.aede` to a temporary directory via the `AEDE_HOME` environment variable.

## Test Structure

The test suite covers:

| Area | Files |
|------|-------|
| CLI | Argument parsing, header, title, shutdown |
| Agent loop | System prompt, tool dispatch, gate integration |
| Providers | Provider selection, message/tool conversion, streaming |
| Database | SQLite CRUD (all tables), FTS5 search |
| Sessions | Create, load, archive, resume, title generation |
| Commands | Slash-command parsing, config editing, setkey |
| Gate | Approval decisions, PermissionStore, prompt |
| Hooks | Hard-deny pattern matching |
| Tools | File operations, shell, search, web |
| Router | Tool filtering, allowlisting |
| Config | Loading, merging, writing, bootstrap |
| Rollout | JSONL audit trail |
| Tokens | Tracker, cost estimation, price cache |
| Compaction | String pass, LLM summary, memory flush |
| Critic | Evaluation, finding parsing |
| Credentials | Vault read/write/delete |
| Memory | Embeddings, retrieval (FTS + cosine + hybrid), store, injection, verifier |
| Skills | Schema parsing, directory scanning |
| Agents | Schema parsing, directory scanning + validation |
| MCP | Bridge, router, config |
| ACP | Async message-pump, streaming, cancel, manager, session, registry, auth |
| Server | FastAPI endpoints, soul API, project instructions API, gate cancel, gate reconnect |
| Voice / ASR | ASR providers, model registry, fallback chain, transcribe endpoint, trigger endpoint, ClipRecorder, WebSpeechProvider, VoiceButton |
| Import | Claude Code, OpenCode, skills, MCP |
| Project model | CRUD |
| ACP | Async message-pump, streaming, cancel, manager, session, registry, auth, thinking sequencing, tool call persistence |
| Soul | Layouts, edition, scope selector |
| Thinking segments | Server-side storage and retrieval |
| UI | 11 vitest files for React components |
