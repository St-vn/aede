# aede — Source of Truth

**Version:** 0.1.0  
**Last updated:** 2026-06-09  
**Status:** Phase 1 complete (168+ tests) · Phase 2 partial (memory, MCP, ACP, critic, web server)

---

## 1. Project Overview

aede is a personal CLI agent harness wrapping LLMs (Anthropic primary, OpenAI-compatible secondary). It is an early-stage, single-user tool for agentic workflows across coding, research, planning, and general task execution on Windows.

**Entry point:** `aede.cli:main` (`src/aede/cli.py:198`)  
**Package name (PyPI):** `aedeai` (base `aede` claimed by 2017 dormant package)  
**Python:** >=3.12  
**Build system:** Hatchling  
**Deps managed by:** uv  

**Directory layout:**

```
aede/                    # Main Python package
├── cli.py               # Entry point, REPL loop, bootstrap
├── config.py            # YAML merge (defaults > global > project)
├── models.py            # Model presets (Anthropic/OpenAI/DeepSeek/etc)
├── agent.py             # Core AgentLoop (multi-turn conversation)
├── provider.py          # LLM provider abstraction (Anthropic + OpenAI)
├── db.py                # SQLite persistence (WAL + FTS5)
├── session.py           # Session model (ULID, create/load/archive/branch)
├── commands.py          # Slash-command handlers
├── gate.py              # Approval gate (permission prompts)
├── hooks.py             # Pre-execution safety hooks (hard-deny patterns)
├── rollout.py           # Append-only JSONL audit log
├── compaction.py        # Context compaction (string pass + LLM summary)
├── tokens.py            # Token tracking + cost estimation
├── critic.py            # Asymmetric code critic
├── credentials.py       # JSON credentials vault
├── project.py           # Project model (persistent directories)
├── server.py            # FastAPI backend server
├── tools/               # Tool implementations
│   ├── router.py        # Tool registry + dispatcher
│   ├── files.py         # read_file, write_file, create_file, list_dir
│   ├── powershell.py    # Shell execution
│   ├── search.py        # search_files (ripgrep) + session_search (FTS5)
│   └── web.py           # fetch_url + web_search (DuckDuckGo)
├── skills/              # Skills system
│   ├── schema.py        # SkillDef dataclass + from_file parser
│   └── loader.py        # Skill loader
├── agents/              # Subagent system
│   ├── schema.py        # AgentDef dataclass + from_file parser
│   ├── loader.py        # Agent loader with validation
│   └── orchestration.py # Subagent runner (isolated AgentLoop)
├── memory/              # Memory system (Phase 2)
│   ├── store.py         # LearningsStore (JSONL + DB mirror)
│   ├── embeddings.py    # OllamaClient for local embeddings
│   ├── retrieval.py     # top_k_cosine + FTS + hybrid retrieval
│   ├── injection.py     # build_learnings_suffix (system prompt)
│   └── verifier.py      # Code + LLM coherence verifier
├── mcp/
│   └── client.py        # MCPBridge (MCP server subprocess manager)
├── acp/
│   ├── client.py        # ACP JSON-RPC client
│   ├── registry.py      # ACP AgentConfig registry
│   ├── manager.py       # AcpManager (connect/disconnect/switch)
│   ├── session.py       # AcpSession wrapper
│   ├── permissions.py   # ACP permission bridge
│   └── credentials.py   # ACP credential provider
├── trace/
│   └── logger.py        # GEPA-compatible turn trace logger
└── import_/
    ├── claude_code.py   # Claude Code .md → aede import
    └── opencode.py      # OpenCode .md → aede (delegates to claude_code)
tests/                   # 62 test files, pytest + pytest-asyncio
ui/                      # Next.js web frontend (React, shadcn/ui)
docs/                    # ADRs, plans, documentation
```

---

## 2. CLI Entry Point & REPL Loop

**File:** `aede/cli.py:main()` (line 198)

### Invocation modes

| Command | Mode | Description |
|---------|------|-------------|
| `aede` | REPL | Interactive prompt loop (new session) |
| `aede "<task>"` | REPL + initial task | Same, with first message injected |
| `aede memory list\|show\|delete\|edit` | Memory CLI | Synchronous memory management |
| `aede --import claude-code\|opencode --src <file> [--dest <dir>]` | Import | Import agent definitions |
| `aede --serve [--host] [--port]` | Server | FastAPI backend |

### Bootstrap sequence (`cli.py:_run()` line 266)

1. Load credentials vault into `os.environ` (`cli.py:293-297`)
2. Load merged config (`cli.py:299`)
3. Open SQLite DB (`cli.py:301`)
4. Create or resume session (`cli.py:303-345`)
5. Initialize rollout (JSONL audit log) (`cli.py:347-348`)
6. Load permission store from config (`cli.py:350-351`)
7. Load skills from `~/.aede/skills/` and `./skills/` (`cli.py:353-356`)
8. Load agents from `~/.aede/agents/` and `./agents/` (`cli.py:358-371`)
9. Initialize ACP registry + manager (`cli.py:378-383`)
10. Build ToolRouter with gated tools (`cli.py:386-397`)
11. Spawn MCP servers if configured (`cli.py:400-415`)
12. Initialize agent loop (`cli.py:421-444`)
13. Enter REPL loop (`cli.py:463-547`)

### Session branching (`cli.py:303-345`)

`/resume` creates a new branch session with `parent_id` pointing at the original. Parent messages reconstructed as simple role+content dicts (tool round-trips collapsed). Original session remains intact and independently resumable.

### Shutdown (`cli.py:_shutdown()` line 569)

- `/exit` or EOF → status `archived`
- Ctrl+C → status `active` (resumable)
- Empty sessions (no messages) → deleted entirely

### Slash-commands

Defined in `aede/commands.py:COMMANDS` (line 15-19):

| Command | Handler | Description |
|---------|---------|-------------|
| `/help` | `handle_help` | Print command list |
| `/keybinds` | `handle_keybinds` | Show keyboard shortcuts |
| `/resume [id]` | `handle_resume` | Resume a session (branch) |
| `/sessions` | `handle_sessions` | List recent 20 sessions |
| `/delete-session\|/rm [id]` | `handle_delete_session` | Delete session + rollout + notes |
| `/tools` | `handle_tools` | List tools + approval status |
| `/skills` | `handle_skills` | List loaded skills |
| `/agents` | `handle_agents` | List loaded agents |
| `/config [scope] [key] [value]` | `handle_config_edit` | View/set config |
| `/compact` | `agent.compact()` | Manual context compaction |
| `/tokens` | `handle_tokens` | Token usage + cost estimate |
| `/setkey <NAME> <value>` | `handle_setkey` | Save credential to vault |
| `/acp ...` | `handle_acp` | ACP agent lifecycle |
| `/clear` | — | Start new session (prompts confirm) |
| `/exit` | — | End session cleanly |

---

## 3. Configuration System

**File:** `aede/config.py` (294 lines)

### Three-layer merge

1. **Defaults** — `DEFAULT_CONFIG` dict (`aede/config.py:14-42`)
2. **Global** — `~/.aede/config.yml`
3. **Project** — `./aede.yml` (overrides global)

Source tracking: `AedeConfig.sources` dict tracks origin per key (`"default"`, `"global"`, `"project"`).

### `AedeConfig` class (`aede/config.py:103-147`)

Key attributes:

| Attribute | Default | Description |
|-----------|---------|-------------|
| `model` | `claude-sonnet-4-20250514` | Active model |
| `context_window` | 200000 | Token limit before compaction |
| `compaction_threshold` | 0.85 | Fraction of window that triggers compaction |
| `tool_output_max_tokens` | 8000 | Max tokens per tool output |
| `shell` | `powershell` | `powershell` \| `cmd` \| `wsl` |
| `wsl_distro` | `""` | WSL distro name |
| `batch_approval_max` | 20 | Max tool batch before forced split |
| `auto_approve` | `[]` | Pre-approved tool names |
| `model_prices` | `{}` | Price overrides per model |
| `api_base_url` | `None` | OpenAI-compatible base URL |
| `reasoning_effort` | `auto` | `auto` \| `none` \| `low` \| `medium` \| `high` \| `xhigh` \| `max` |
| `thinking_budget` | 0 | Token budget for thinking (min 1024) |
| `grounding_enabled` | `True` | Inject grounding instruction into system prompt |
| `critic_enabled` | `False` | Enable asymmetric critic pass |
| `critic_model` | `None` | Separate model for critic |
| `critic_api_base_url` | `None` | Base URL for critic model |
| `ollama_base_url` | `http://localhost:11434` | Ollama endpoint |
| `ollama_embed_model` | `nomic-embed-text` | Embedding model |
| `ollama_timeout_s` | 5 | Ollama request timeout |
| `learnings_top_k` | 5 | Top-k learnings to retrieve |
| `learnings_max_tokens` | 2000 | Max tokens for learnings suffix |
| `mcp_servers` | `{}` | MCP server configs |

### Bootstrap (`aede/config.py:bootstrap()` line 86)

Creates `~/.aede/` tree with `data/`, `data/sessions/`, `skills/`, `agents/` and default `config.yml`. Idempotent.

### Config editing (`aede/config.py:write_config_value()` line 197)

- Supports type coercion (int, float, bool, str) based on default type
- List operations (add/remove) on `auto_approve` key
- `edit_config_file()` opens `$EDITOR` (falls back to notepad.exe on Win, vi on POSIX)

### Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `AEDE_HOME` | No | Override home directory (default: `~/.aede`) |
| `ANTHROPIC_API_KEY` | Yes (Anthropic) | Anthropic API key |
| `OPENROUTER_API_KEY` | Yes (OpenRouter) | OpenRouter API key |
| `OPENAI_API_KEY` | Yes (OpenAI) | OpenAI API key |
| `DEEPSEEK_API_KEY` | Yes (DeepSeek) | DeepSeek API key |
| `EDITOR` | No | Text editor (default: notepad.exe/vi) |

---

## 4. Provider Abstraction

**File:** `aede/provider.py` (530 lines)

### Architecture

```
get_provider(cfg) → AnthropicProvider | OpenAIProvider
```

### Selection logic (`aede/provider.py:488-530`)

- DeepSeek models (`deepseek-*`) → `OpenAIProvider` with `DEEPSEEK_API_KEY`
- `api_base_url` + non-Anthropic model → `OpenAIProvider`
- Otherwise → `AnthropicProvider`

### `NormalizedResponse` dataclass (`aede/provider.py:19-29`)

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Assistant text response |
| `tool_calls` | `list[dict]` | `[{"id", "name", "input"}]` |
| `input_tokens` | `int` | Prompt tokens |
| `output_tokens` | `int` | Completion tokens |
| `cached_tokens` | `int` | Cache-read tokens |
| `assistant_content_blocks` | `list[Any]` | Anthropic-format blocks for history |

### `AnthropicProvider` (`aede/provider.py:55-167`)

- Uses `anthropic.AsyncAnthropic` SDK
- Streaming via `client.messages.stream()`
- **Two-block system prompt** with `cache_control: ephemeral` on the stable prefix (`aede/provider.py:97-107`)
- **Cache injection** on last message for KV-cache reuse (`aede/provider.py:114-132`)
- Supports thinking mode with `reasoning_effort` and `thinking_budget`

### `OpenAIProvider` (`aede/provider.py:305-481`)

- Uses `openai.AsyncOpenAI` SDK
- Message format conversion: `_convert_messages_to_openai()` (`aede/provider.py:174-282`)
- Tool schema conversion: `_convert_tools_to_openai()` (`aede/provider.py:285-302`)
- Reasoning effort mapping for DeepSeek, Gemini, and OpenAI providers
- Fragmented tool_call delta accumulation across streaming chunks

### Provider Protocol (`aede/provider.py:32-48`)

```python
@runtime_checkable
class Provider(Protocol):
    async def stream_turn(self, *, model, system, tools, messages, max_tokens, console, reasoning_effort, thinking_budget) -> NormalizedResponse: ...
```

---

## 5. Agent Loop

**File:** `aede/agent.py` (793 lines)

### `AgentLoop` class (`aede/agent.py:189-793`)

Stateful multi-turn agent: coordinates provider, tools, gate, and DB.

### `run_turn(user_input)` (`aede/agent.py:294-533`)

**Flow:**
1. Increment turn counter, append user message to history
2. Persist to DB + rollout
3. Auto-compact if near context limit (`_maybe_compact()`)
4. **Inner loop** (while model requests tools):
   a. `_stream_response()` — call provider, stream text to console
   b. Record token usage in tracker
   c. Persist assistant message to DB + rollout
   d. For each tool call:
      - Validate name (reject unknown without retry)
      - Run hard-deny hooks (`pre_tool_use`)
      - Run critic (if enabled + write_file/create_file with code)
      - Gate approval (allow/deny/redirect/batch)
      - Validate params via Pydantic (one retry on failure)
      - Execute synchronously
      - Collect result, detect stuck (3 consecutive failures → break)
   e. Append tool results as user content block
5. Write GEPA trace record

### System prompt (`aede/agent.py:19-56`)

Two-part structure:
- **Stable** (`STABLE_SYSTEM_PROMPT`): Role, tools, rules — cacheable across sessions
- **Dynamic** (`build_system_prompt()` line 72): Config, session notes, compaction summary, grounding, skills, learnings

### API error handling (`aede/agent.py:_stream_response()` line 565)

- Transient (429/500/502/503): retry up to 3× with exponential backoff (`BACKOFF_BASE * 2^attempt`)
- Non-transient: surface immediately
- HTML body detection prevents dumping rendered error pages

### Stuck detection (`aede/agent.py:506-513`)

- Same tool call fails 3× consecutively → print warning and return
- Param validation failure 2× on same call key → stuck, return early

### Batch approval (`aede/agent.py:451-458`)

Scoped to one assistant message's `tool_calls` list. Only honored when `len(tool_calls) <= batch_approval_max`.

### GEPA trace (`aede/agent.py:535-558`)

`_write_turn_trace()` accumulates per-turn: input/output/cached tokens, tool calls (name/args/result/duration_ms), reasoning text, outcome. Written to TraceLogger after each turn.

---

## 6. Tool System

**File:** `aede/tools/router.py` (509 lines)

### ToolRouter (`aede/tools/router.py:38`)

Central registry mapping `name → Callable`. Built at construction time via `_build_registry()`.

### Gated tools (`aede/tools/router.py:18`)

```python
GATE_TOOLS = {"powershell", "write_file", "create_file", "write_learning"}
```

### Core tools

| Tool | File | Gate | Description |
|------|------|------|-------------|
| `powershell` | `tools/powershell.py:run_powershell()` | Yes | Execute shell command (powershell/cmd/wsl) |
| `read_file` | `tools/files.py:read_file()` | No | UTF-8 file read |
| `write_file` | `tools/files.py:write_file()` | Yes | Overwrite existing file |
| `create_file` | `tools/files.py:create_file()` | Yes | Create new file (fails if exists) |
| `list_dir` | `tools/files.py:list_dir()` | No | Directory listing with configurable depth |
| `search_files` | `tools/search.py:search_files()` | No | ripgrep wrapper |
| `fetch_url` | `tools/web.py:fetch_url()` | No | HTTP GET (rejects HTML/SPA responses) |
| `web_search` | `tools/web.py:web_search()` | No | DuckDuckGo search |

### Extended tools

| Tool | File | Gate | Description |
|------|------|------|-------------|
| `spawn_subagent` | `router.py:_build_registry()` | No | Delegates task to loaded agent |
| `session_search` | `tools/search.py:session_search()` | No | FTS5 search over past session messages |
| `write_learning` | `router.py:_write_learning_tool()` | Yes | Persist learning with verifier integration |

### MCP tools

Auto-discovered as `mcp__<server>__<name>` prefix. Gate status depends on server's `trusted` flag (`aede/tools/router.py:257-261`).

### Tool validation (`aede/tools/router.py:208-247`)

- `validate_name()` — raises `UnknownToolError` if name not in registry
- `validate_args()` — checks required fields + JSON schema types using lazy Pydantic
- Errors return to model as `ToolResult(status="error")` — never hidden

### ToolResult (`aede/tools/router.py:29-35`)

```python
@dataclass
class ToolResult:
    status: str       # "success" | "error"
    output: str
    duration_ms: int
```

### Tool schemas (`aede/tools/router.py:346-508`)

`_TOOL_SCHEMAS` dict — Anthropic-format JSON schemas for all tools. Single source of truth for both LLM function-calling and Pydantic validation.

### Output truncation (`aede/tools/router.py:293-299`)

Tool outputs capped at `tool_output_max_tokens * 4` characters (~ token estimate). Truncated output includes token count note.

---

## 7. Approval Gate

**File:** `aede/gate.py` (232 lines)

### `GateDecision` enum (`aede/gate.py:16-27`)

| Decision | Meaning |
|----------|---------|
| `ALLOW_ONCE` | Run once |
| `ALLOW_SESSION` | Allow for this session |
| `ALLOW_PROJECT` | Persist to `aede.yml` |
| `ALLOW_GLOBAL` | Persist to `~/.aede/config.yml` |
| `DENY` | Reject |
| `REDIRECT` | Send user message to agent |
| `BATCH_APPROVE` | Approve all in batch |
| `BATCH_DENY` | Deny all in batch |

### `PermissionStore` (`aede/gate.py:29-87`)

Three scope layers:
- **Session** (in-memory, lost on exit)
- **Project** (persisted to `./aede.yml`)
- **Global** (persisted to `~/.aede/config.yml`)

Session > Project > Global precedence.

### `TerminalGateBackend` (`aede/gate.py:109-147`)

CLI implementation of `GateBackend` protocol. Runs `prompt_gate()` in a thread executor.

### `prompt_gate()` (`aede/gate.py:167-211`)

Single-keypress approval (A/W/D/R/B) via `_read_key()` which uses `msvcrt.getch()` on Windows, raw-mode `tty` on POSIX.

### WebSocketGateBackend (`aede/server.py:26-55`)

Server-side gate backend: sends gate request via WebSocket JSON, waits for response via `asyncio.Future`.

### `GateBackend` Protocol (`aede/gate.py:94-106`)

```python
@runtime_checkable
class GateBackend(Protocol):
    async def request(self, gate_id, tool_name, args, batch_count) -> tuple[GateDecision, str]: ...
```

---

## 8. Safety Hooks

**File:** `aede/hooks.py` (52 lines)

### `pre_tool_use()` (`aede/hooks.py:44`)

Pre-execution safety gate that hard-denies dangerous shell patterns BEFORE the approval gate renders. Only checks `SHELL_TOOLS = {"powershell", "cmd"}`.

### Dangerous patterns (`aede/hooks.py:18-31`)

- `rm -rf /` and variants
- `format C:` and variants
- `mkfs.*` commands
- `dd if=... of=/dev/...`
- `shutdown` / `reboot`
- Fork bombs (`:(){ :\|:& };:`)

Raises `HardDeniedError` with the matched pattern. Patterns compiled with `re.IGNORECASE`.

---

## 9. Context Compaction

**File:** `aede/compaction.py` (169 lines)

### Five-step sequence

1. **Memory flush** — LLM writes session notes before compaction (`aede/compaction.py:121-136`)
2. **O(n) string pass** — `collapse_old_tool_outputs()` stubs old tool results with `[tool output — ~N tokens — compacted]` placeholder (`aede/compaction.py:43-74`)
3. **Re-check** — if below threshold, stop (string pass only)
4. **LLM summary** — preserves head (3) + tail (15) messages; middle collapsed via structured handoff template (`aede/compaction.py:107-166`)
5. **Stamp** — `compacted_at` timestamp on DB rows (hide-don't-delete) (`aede/agent.py:784-791`)

### `COMPACTION_PROMPT` (`aede/compaction.py:13-26`)

Structured template: Goal / Constraints / Progress / Key Decisions / Critical Context / Next Steps

### `run_compaction()` (`aede/compaction.py:77-169`)

Returns `{"method": "string_pass_only" | "llm_summary" | "none", "messages", "summary", "tokens_reclaimed", "messages_compacted"}`

### Trigger

Automatic: fires when `current_tokens >= context_window * compaction_threshold` (default 85%). Manual via `/compact`.

### Provider fallback (`aede/agent.py:733-751`)

Non-Anthropic providers fall back to a bare Anthropic client for compaction. Skipped if `ANTHROPIC_API_KEY` is not set.

---

## 10. Database & Persistence

**File:** `aede/db.py` (525 lines)

### SQLite

**Path:** `~/.aede/data/aede.db`  
**Journal:** WAL (`PRAGMA journal_mode=WAL`)  
**Foreign keys:** ON (`PRAGMA foreign_keys=ON`)  
**Row factory:** Custom dict factory (`_row_factory` line 112)

### Tables

#### sessions
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `parent_id` | TEXT → sessions(id) | For branching/resume |
| `title` | TEXT | Derived from first message |
| `created_at` | INTEGER | Unix ms |
| `updated_at` | INTEGER | Unix ms |
| `model` | TEXT | Model name |
| `status` | TEXT | `active` \| `archived` |
| `project_dir` | TEXT | Optional project association |

#### messages
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `session_id` | TEXT FK → sessions | |
| `role` | TEXT | `user` \| `assistant` |
| `content` | TEXT | Message body |
| `created_at` | INTEGER | Unix ms |
| `token_count` | INTEGER | Optional token count |
| `compacted_at` | INTEGER | Unix ms (hide-don't-delete) |

#### tool_calls
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `message_id` | TEXT FK → messages | |
| `tool_name` | TEXT | |
| `args` | TEXT | JSON |
| `result` | TEXT | Tool output |
| `status` | TEXT | `success` \| `error` |
| `duration_ms` | INTEGER | |
| `created_at` | INTEGER | Unix ms |

#### token_usage
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `session_id` | TEXT FK → sessions | |
| `turn_number` | INTEGER | |
| `input_tokens` | INTEGER | |
| `output_tokens` | INTEGER | |
| `cached_tokens` | INTEGER | |
| `created_at` | INTEGER | Unix ms |
| `role` | TEXT | `agent` \| `critic` |

#### projects
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `project_dir` | TEXT UNIQUE | |
| `display_name` | TEXT | |
| `created_at` | INTEGER | |
| `updated_at` | INTEGER | |

#### learnings
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | ULID |
| `type` | TEXT | anti-pattern, failed-approach, root-cause, config-correction |
| `content` | TEXT | |
| `source` | TEXT | user, auto_learned, test_failure, tool_error |
| `created_at` | INTEGER | |
| `trusted` | INTEGER | 0/1 |
| `lower_trust` | INTEGER | 0/1 |
| `verifier_outcome` | TEXT | |
| `embedding` | BLOB | Packed float array |

### FTS5 virtual tables

- `messages_fts` — full-text search on messages content
- `learnings_fts` — full-text search on learnings content
- Sync triggers: `AFTER INSERT`, `AFTER DELETE`, `AFTER UPDATE` on both tables

### Migration handling (`aede/db.py:141-169`)

Graceful ALTER TABLE for schema additions using try/except:
- `role` column on `token_usage` (BC-06)
- `project_dir` column on `sessions` (WS-01)
- `projects` table creation (PJ-01)

### JSONL Rollout (`aede/rollout.py`)

**Path:** `~/.aede/data/sessions/YYYY/MM/DD/rollout-<session_id>.jsonl`  
**Purpose:** Crash-safe append-only audit trail  
**Schema:** Versioned JSON (`"v":1`) with UTC millisecond timestamps  
**Events:** `session_start`, `session_end`, `user_message`, `assistant_message`, `tool_call`, `tool_result`, `compaction`, `subagent_start`, `subagent_end`

---

## 11. Session Management

**File:** `aede/session.py` (120 lines)

### `Session` class

- **ID:** ULID via `generate_session_id()` (`aede/session.py:15`)
- **Factory methods:** `Session.create()`, `Session.load()`, `Session.list_recent()` — no direct constructor
- **Branching:** `parent_id` links branch sessions to origin

### Lifecycle methods

| Method | Description |
|--------|-------------|
| `archive(db)` | Status → `archived` |
| `delete(db)` | Remove from DB entirely |
| `set_active(db)` | Status → `active` |
| `set_title(db, title)` | One-time title set (no-op if already set) |
| `set_project_dir(db, path)` | Associate project |

### `make_title(text)` (`aede/session.py:95-105`)

- Messages <10 chars: text + UTC timestamp for disambiguation
- Longer: truncated to 60 characters

---

## 12. Token Tracking & Cost Estimation

**File:** `aede/tokens.py` (188 lines)

### `TokenTracker` class

Accumulates per-turn token usage in memory, persists each row to DB. Methods:
- `record(turn, input_tokens, output_tokens, cached_tokens)` — append usage row
- `totals()` — `{input_tokens, output_tokens, cached_tokens}`
- `totals_by_role()` — separate "agent" vs "critic" roles
- `cache_hit_rate()` — `cached_tokens / (input_tokens + cached_tokens)`

### `PriceCache` class

24-hour TTL disk cache for OpenRouter pricing. `fetch_openrouter()` makes async HTTPX call to `openrouter.ai/api/v1/models`. Converts per-token prices to per-million-token values.

### `estimate_cost()` (`aede/tokens.py:152`)

Computes USD cost using price table. Cached vs uncached input billing handled separately. `FALLBACK_PRICES` dict for Claude models when OpenRouter data unavailable.

---

## 13. Credentials Vault

**File:** `aede/credentials.py` (152 lines)

**Path:** `~/.aede/credentials.json`  
**File permissions:** Best-effort `0o600`

### Functions

| Function | Description |
|----------|-------------|
| `load_credentials_into_env(home)` | Read vault → `os.environ` (real env vars take precedence) |
| `set_credential(home, name, value, provider)` | Write to vault |
| `list_credentials(home)` | List stored key names |
| `delete_credential(home, name)` | Remove from vault |

### Format

Backward-compatible:
```json
{"ANTHROPIC_API_KEY": "sk-ant-..."}
```
Structured:
```json
{"DEEPSEEK_API_KEY": {"value": "sk-...", "provider": "deepseek"}}
```

---

## 14. Skills System

**Files:** `aede/skills/schema.py` (63 lines), `aede/skills/loader.py` (35 lines)

### Skill definition (`SKILL.md`)

YAML frontmatter + body in markdown:
```yaml
---
name: test-writer
description: Writes tests for Python code
trigger_phrases: ["test", "pytest"]
allowed_tools: ["read_file", "write_file", "search_files"]
model: claude-sonnet-4-20250514
---
Skill instruction text body...
```

### `SkillDef` dataclass (`aede/skills/schema.py:27-50`)

### `SkillDef.from_file(path)` (`aede/skills/schema.py:52-63`)

Parses YAML frontmatter (delimited by `---`) from `.md` files. Falls back gracefully if frontmatter is absent.

### `load_skills()` (`aede/skills/loader.py:12-35`)

Scans `~/.aede/skills/` (global) and `./skills/` (project). Project skills shadow globals with same name. Loads `*.md` files and `SKILL.md` inside subdirectories.

### Injection

Skills injected into dynamic system prompt under `## Agent Skills` section (`aede/agent.py:137-140`). Passed to `AgentLoop.initialize()`.

---

## 15. Agents & Subagent Orchestration

**Files:** `aede/agents/schema.py` (72 lines), `loader.py` (56 lines), `orchestration.py` (130 lines)

### Agent definition (`AGENT.md`)

YAML frontmatter:
```yaml
---
name: researcher
description: Web research specialist
model: claude-sonnet-4-20250514
skills: [web-research]
tools: [web_search, fetch_url]
disallowedTools: [powershell]
maxTurns: 5
systemPrompt: "custom system prompt override"
---
```

### `AgentDef` dataclass (`aede/agents/schema.py:23-54`)

Validated at load time: all referenced skills must exist in the skill registry, all referenced tools must exist in the tool set.

### `load_agents()` (`aede/agents/loader.py:12-56`)

Scans `~/.aede/agents/` and `./agents/`. Validates tool references against `all_tool_names` list. Validates skill references against `skill_registry`.

### `run_subagent()` (`aede/agents/orchestration.py:30-117`)

Creates isolated AgentLoop:
- Fresh session linked via `parent_id`
- Filtered ToolRouter (from allowlist/denylist)
- Per-agent model override
- `MAX_SPAWN_DEPTH=1` guard against runaway recursion
- Iterates up to `agent_def.max_turns`
- Subagent session archived on completion
- Rollout logs `subagent_start`/`subagent_end`
- Returns final text or error string

### `spawn_subagent` tool (`aede/tools/router.py:104-133`)

Registered dynamically in ToolRouter if config + agent_registry are available. Calls `run_subagent()` with depth=1.

---

## 16. Memory System (Phase 2)

### LearningsStore

**File:** `aede/memory/store.py` (196 lines)  
**Path:** `~/.aede/data/learnings.jsonl`

**Schema:**
- `type`: `anti-pattern` | `failed-approach` | `root-cause` | `config-correction`
- `source`: `user` | `auto_learned` | `test_failure` | `tool_error`
- `trusted` / `lower_trust` / `verifier_outcome` — lifecycle fields
- `embedding` — optional packed BLOB

**Methods:** `write_learning()`, `list_all()`, `get()`, `delete()`, `update()`. Optionally mirrors to DB learnings table.

### Ollama Embeddings

**File:** `aede/memory/embeddings.py` (63 lines)  
**Client:** `OllamaClient.embed_text()` → POST `{base_url}/api/embeddings`  
**Default model:** `nomic-embed-text` (768 dims)  
**Timeout:** 5 seconds  
**Error:** Raises `OllamaUnavailable` on connection errors (graceful degradation)

### Retrieval

**File:** `aede/memory/retrieval.py` (208 lines)

**Three strategies:**
1. `top_k_cosine()` — unpack BLOB embeddings via `struct`, compute cosine similarity with numpy
2. `fts_retrieve()` — SQLite FTS5 with BM25 ranking (double-quotes terms, skips single-char tokens)
3. `hybrid_retrieve()` — rank-based merge (default 0.5/0.5 weights), dedup by ID, degrades to FTS-only when Ollama unavailable (one-time warning)

### System prompt injection

**File:** `aede/memory/injection.py` (72 lines)  
**Function:** `build_learnings_suffix()`  
Calls `hybrid_retrieve()` → formats as `## Lessons from Prior Runs` → truncates to fit token budget. Each entry includes provenance: "verified by test" vs "verified by LLM coherence (may be imperfect)".

### Verifier

**File:** `aede/memory/verifier.py` (161 lines)

**Two paths (never write to store — return update dicts):**
1. `run_code_verify()` — runs `uv run pytest` via subprocess → `trusted=True` on pass
2. `run_llm_verify()` — separate Anthropic coherence check → always sets `lower_trust=True`

---

## 17. MCP Bridge

**File:** `aede/mcp/client.py` (256 lines)

### `MCPBridge` class

Manages multiple MCP server subprocesses, each in its own background daemon thread with `asyncio` event loop.

### Key methods

| Method | Description |
|--------|-------------|
| `spawn_all()` | Spawn all configured servers, returns list of failed names |
| `discovered_tools()` | Return `[(full_name, server_name, config, schema)]` |
| `call_sync(server, tool, args)` | Thread-safe synchronous call via `run_coroutine_threadsafe` |
| `shutdown_all()` | Graceful close + force-kill residual processes |

### Tool naming

MCP tools prefixed with `mcp__<server>__<name>` to avoid collisions.

### Config parsing (`_parse_mcp_servers()`)

Supports both `mcp_servers` and `mcpServers` keys. Each server has: `command`, `args`, `env`, `trusted` (bool — determines gate behavior).

### Timeouts

- `MCP_TIMEOUT = 10s` — initialization timeout
- `CALL_TIMEOUT = 60s` — tool call timeout

---

## 18. ACP (Agent Client Protocol)

### ACP Client

**File:** `aede/acp/client.py` (175 lines)

JSON-RPC 2.0 client over stdio subprocess.

**Key methods:**
- `initialize()` — protocol version negotiation, client capabilities (fs, terminal)
- `new_session()` — create session with optional MCP servers
- `prompt(text)` — send prompt, stream updates via `on_update` callback
- `destroy_session()` — cleanup

**Dataclasses:** `InitializeResult`, `AgentInfo`, `AcpError`

**Note:** Custom JSON-RPC implementation (pre-official-SDK prototype). Migration to official SDK deferred to Phase 3.

### ACP Registry

**File:** `aede/acp/registry.py` (70 lines)  
**Path:** `~/.aede/agents.json`  
**Config:** `AgentConfig(name, transport, command, args, env, credentials_ref)`

### ACP Manager

**File:** `aede/acp/manager.py` (94 lines)

| Method | Description |
|--------|-------------|
| `connect(name)` | Spawn AcpClient, init, create session |
| `disconnect(name)` | Cleanup with auto-fallback |
| `switch_to(name)` | Activate different connected agent |
| `active_session()` | Currently focused agent |
| `list_connected()` | All connected agent names |

### ACP Session

**File:** `aede/acp/session.py` (48 lines)  
Lightweight wrapper: `create(directory, mcp_servers)` → session ID, `prompt(text)` → `PromptResult(stop_reason, raw)`

### ACP Permissions Bridge

**File:** `aede/acp/permissions.py` (71 lines)  
Maps ACP permission requests to aede's approval gate.

### ACP Credential Provider

**File:** `aede/acp/credentials.py` (37 lines)  
Injects credentials from vault into agent subprocess environment.

### Known Gap: ACP Chat Routing

The model selector → ACP agent chat routing is **not wired**. Selecting an ACP agent (Claude Code, Gemini, etc.) from the model selector saves `cfg.model` but the chat loop has no routing logic to detect "this model is an ACP agent" and send messages to the ACP subprocess. Deferred to Phase 3.

---

## 19. Code Critic

**File:** `aede/critic.py` (162 lines)

### `evaluate()` function

Creates a separate LLM provider (or falls back to the main agent's model), sends code with task context, parses JSON response into `CriticFinding` objects.

### Critic persona

```python
CRITIC_SYSTEM_PROMPT = "You are a ruthless code reviewer. ..."
```
Correctness bugs only — no style/formatting feedback.

### Severity levels

`HIGH` (bold red), `MEDIUM` (yellow), `LOW` (dim)

### Non-fatal design

All exceptions return empty list. Critic runs before the gate for `write_file`/`create_file` with code-like content (`aede/agent.py:419-424`). Uses `role="critic"` for separate token tracking.

---

## 20. Trace Logger

**File:** `aede/trace/logger.py` (83 lines)

### `TraceLogger` class

Writes per-turn agent traces to `<data_dir>/traces/<session_id>.jsonl`.

### Trace record fields

- `session_id`, `turn_number`
- `input_tokens`, `output_tokens`, `cached_tokens`
- `tool_calls` — `[{name, args, result, duration_ms}]`
- `reasoning_text`
- `outcome`
- `schema_version`: `"phase2-draft"`

Crash-safe: open + flush per write. Directory created lazily on first write.

---

## 21. Import Converters

### Claude Code → aede

**File:** `aede/import_/claude_code.py` (75 lines)

Converts Claude Code agent `.md` (YAML frontmatter + body) to aede `AGENT.md` format. Maps supported fields 1:1, comments out unsupported ones (permissionMode, mcpServers, memory, isolation, effort, color, hooks). Returns `ImportReport(name, path, was_skipped)`.

### OpenCode → aede

**File:** `aede/import_/opencode.py` (24 lines)

Thin shim that delegates to `import_claude_code_agent()` and tags result format as `"OpenCode"`.

---

## 22. Web Server

**File:** `aede/server.py` (1065 lines)

### FastAPI application

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ws/sessions/{session_id}` | WebSocket | Interactive agent turns |
| `/api/sessions` | GET | List sessions |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/api/config` | GET | Get effective config |
| `/api/config` | PUT | Update config |
| `/api/gate/respond` | POST | Gate response from UI |
| `/api/acp/configs` | GET/POST | ACP agent config management |
| `/api/acp/connect` | POST | Connect ACP agent |
| `/api/acp/disconnect` | POST | Disconnect ACP agent |

### WebSocket Gate Backend (`aede/server.py:26-55`)

Sends gate requests via WebSocket JSON, waits for response via `asyncio.Future`.

### WebSocket Console (`aede/server.py:58-77`)

Redirects `console.print()` output to Web UI via JSON messages.

---

## 23. Model Presets

**File:** `aede/models.py` (62 lines)

### `MODEL_PRESETS` dictionary

Hardcoded mappings covering:
- **Anthropic:** Claude Opus 4.8, Sonnet 4.6, Haiku 3.5
- **OpenAI:** GPT-5.5, o3, o4-mini
- **DeepSeek:** v3-0324, r1-0528
- **OpenRouter:** Gemini 2.5 Flash/Pro
- **Codex CLI:** codex
- **ACP agents:** claude-code, gemini, agy

### `load_models()` / `save_models()` / `reset_models()`

Reads from `~/.aede/models.json` (user-customizable). Falls back to `default_models()` on missing/corrupt file.

---

## 24. Project Model

**File:** `aede/project.py` (56 lines)

### `Project` class

Persistent workspace directories with independent lifecycle (survives session deletion). ULID-based IDs.

| Method | Description |
|--------|-------------|
| `create(db, project_dir, display_name)` | Create + DB insert |
| `load(db, id)` | Load from DB |
| `list_all(db)` | All projects |
| `delete(db)` | Remove from DB only (no filesystem) |

---

## 25. Tests

**Directory:** `tests/` (62 files)  
**Runner:** `uv run pytest` (or `uv run pytest -xvs` for verbose)  
**Config:** `pyproject.toml` → `[tool.pytest.ini_options] asyncio_mode = "auto"`  
**Fixture:** `tests/conftest.py:tmp_home` — redirects `~/.aede` to temp dir via `AEDE_HOME`

### Test file summary

| File | What it tests |
|------|---------------|
| `test_cli.py` | Arg parsing, header, title setting, shutdown/pruning |
| `test_agent.py` | AgentLoop, system prompt, tool dispatch, gate |
| `test_provider.py` | Provider selection, message/tool conversion, streaming |
| `test_provider_cache.py` | Provider response caching |
| `test_db.py` | SQLite CRUD (all tables) |
| `test_db_fts.py` | FTS5 full-text search |
| `test_session.py` | Create/load/archive/resume/make_title |
| `test_session_search.py` | FTS5 session search tool |
| `test_commands.py` | Slash-command parsing, /config, /setkey, /resume, /sessions |
| `test_commands_skills.py` | /skills command |
| `test_commands_agents.py` | /agents command |
| `test_gate.py` | Approval gate, PermissionStore, prompt_gate |
| `test_gate_backend_protocol.py` | GateBackend protocol |
| `test_gate_backend_injection.py` | Gate backend wire-up |
| `test_hooks.py` | Hard-deny patterns |
| `test_tools.py` | Tool implementations (files, powershell, etc.) |
| `test_router_filtering.py` | ToolRouter filtering/allowlisting |
| `test_router_allowlist.py` | ToolRouter.from_allowlist |
| `test_config.py` | Config loading, merging, write_config_value |
| `test_config_bootstrap.py` | Bootstrap directory creation |
| `test_rollout.py` | JSONL rollout logging |
| `test_tokens.py` | Token tracker, estimate_cost, PriceCache |
| `test_compaction.py` | Context compaction (string pass, LLM summary, memory flush) |
| `test_critic.py` | Critic evaluation, finding parsing |
| `test_credentials.py` | Credentials vault |
| `test_embeddings.py` | OllamaClient |
| `test_retrieval.py` | FTS5 + cosine + hybrid retrieval |
| `test_learnings_store.py` | LearningsStore CRUD |
| `test_injection.py` | Learnings system prompt injection |
| `test_memory_cli.py` | Memory CLI subcommands |
| `test_verifier.py` | Code + LLM coherence verifier |
| `test_skills_schema.py` | SkillDef parsing/validation |
| `test_skills_loader.py` | Skill directory scanning |
| `test_agents_schema.py` | AgentDef parsing/validation |
| `test_agents_loader.py` | Agent directory scanning + validation |
| `test_agent_skills_inject.py` | Skill injection into agent |
| `test_agent_integration.py` | Agent end-to-end integration |
| `test_subagent_*.py` (8) | Subagent orchestration |
| `test_acp_*.py` (6) | ACP client, manager, session, registry, permissions, credentials |
| `test_mcp_*.py` (3) | MCP bridge, router, config |
| `test_server_*.py` (5) | FastAPI server |
| `test_import_claude_code.py` | Claude Code agent import |
| `test_opencode.py` | OpenCode agent import |
| `test_trace.py` | GEPA trace logger |
| `test_system_prompt_split.py` | System prompt splitting |
| `test_project_model.py` | Project model |

**UI tests:** `ui/__tests__/` — 10 vitest files for React components

---

## 26. Key Architecture Decisions (Locked)

| Decision | Rationale |
|----------|-----------|
| SQLite + WAL + FTS5 as default session store | Migrate-to pattern across Codex, OpenCode, Hermes, OpenClaw |
| Hide-don't-delete compaction | Audit trail preserved; `compacted_at` in schema |
| Two-phase compaction (O(n) pass first, LLM second) | O(n) pass reclaims 30-50% for free |
| Dual storage: JSONL rollouts + SQLite state | JSONL for crash-safe append/replay; SQLite for query/search |
| Asymmetric critic over multi-agent debate | Debate costs 3-5× without reliable advantage |
| Graph memory deferred to Phase 3+ | LOCOMO: graph adds ~2% accuracy at 2× tokens, 3× latency |
| GEPA over GRPO for skill evolution | +6pp average, up to 35× fewer rollouts |
| Self-improvement read step is load-bearing | Reflexion's +8% comes from the read step |
| Stable prompt prefix for KV-cache | 10× cost difference cached vs uncached |
| No LLM retry on hallucinated tool names | Unknown name cannot become valid by retrying |
| Pydantic validation on every tool call | Typed gate; retry once on param errors |
| Tool errors return to model as results | Never hide errors; model decides retry vs report |
| Heavy imports are lazy | anthropic, pydantic, rich — loaded inside functions |

---

## 27. Quick Reference

### Common commands

```bash
uv run aede                            # Start REPL
uv run aede "refactor this file"       # REPL with initial task
uv run aede --serve                    # Start FastAPI backend
uv run aede memory list                # List learnings
uv run aede --import claude-code --src <file>  # Import agent
uv run pytest                          # Run all tests
uv run pytest -xvs tests/test_file.py  # Run specific test
uv sync                                # Install dependencies
```

### Configuration files

| File | Purpose |
|------|---------|
| `~/.aede/config.yml` | Global user config |
| `./aede.yml` | Project-local config (overrides global) |
| `~/.aede/credentials.json` | Credentials vault (API keys, etc.) |
| `~/.aede/agents.json` | ACP agent registry |
| `~/.aede/models.json` | User-customized model list |
| `~/.aede/data/aede.db` | SQLite database (sessions, messages, etc.) |
| `~/.aede/data/learnings.jsonl` | Learnings store |
| `~/.aede/data/traces/<session>.jsonl` | GEPA trace logs |
| `~/.aede/data/sessions/.../rollout-<session>.jsonl` | Per-session audit trail |

### Agent definition files

| Directory | Type | Format |
|-----------|------|--------|
| `~/.aede/skills/*.md` | Skills | YAML frontmatter + instructions |
| `~/.aede/agents/*.md` | Agents | YAML frontmatter + system prompt |
| `./skills/*.md` | Project skills | Same format (shadows global) |
| `./agents/*.md` | Project agents | Same format (shadows global) |
