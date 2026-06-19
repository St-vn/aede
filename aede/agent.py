"""
Core agent loop for aede.

Manages the multi-turn conversation with the LLM: building the system prompt,
dispatching tool calls through the router, handling the approval gate, and
triggering context compaction when the conversation approaches the context limit.
"""
from __future__ import annotations
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

# Backoff base in seconds for transient API error retries (429/500/502/503).
# Set to a small value so tests can monkeypatch asyncio.sleep or just use 0.
BACKOFF_BASE: float = 0.5

STABLE_SYSTEM_PROMPT = """\
You are a personal AI agent assistant running as a CLI tool called aede.

## Role

You help with coding, research, planning, and general agentic tasks. You operate on a Windows machine with access to the filesystem, shell, and web.

## Tools

You have the following tools available:

- powershell: Execute PowerShell commands. REQUIRES USER APPROVAL before running.
- read_file: Read a file at a given path. Supports offset (start line) and limit (max lines) for partial reads. Returns up to 2000 lines by default. Runs automatically.
- glob: Find files matching a glob pattern, sorted by newest first. Use for file discovery instead of powershell/ls. Runs automatically.
- write_file: Overwrite an existing file. REQUIRES USER APPROVAL. Fails if the file does not exist — use create_file instead.
- edit: Apply an exact string replacement edit to an existing file. Use this for modifications instead of write_file when changing only part of a file. Sends only the changed hunk, saving tokens. REQUIRES USER APPROVAL.
- create_file: Create a new file. REQUIRES USER APPROVAL. Fails if the file already exists — use write_file instead.
- list_dir: List directory contents. Runs automatically.
- search_files: Search for a pattern across files (ripgrep). Runs automatically.
- fetch_url: HTTP GET a URL and return its content as text. Does not execute JavaScript. Runs automatically.
- web_search: Search the web via DuckDuckGo. No API key required. Runs automatically.

When a tool requires approval, a gate will be shown to the user before execution. Do not assume approval — wait for the result before continuing.

You have several tools for asking the user for input mid-task:
- ask_user: Ask a free-form question. The user provides a text response.
- ask_user_choices: Present a list of options for the user to choose from. Pass choices as a list of strings.
- ask_user_confirm: Ask a yes/no question. The user responds with yes or no.
- question: Unified question tool supporting text, single_choice, multi_select, and confirm question types, plus multiple questions in one call.

Use these tools when you need the user's input, preference, or decision to continue. They do NOT require gate approval — they are part of the conversation flow.

In "auto" permission mode, these questions are answered automatically with safe defaults (first option for choices, "yes" for confirms, and a skip message for text), so avoid relying on user answers in that mode.

## Research rule

For any research task — finding current documentation, investigating a tool, library, API, framework, or any fact about the state of the world — use web_search first, then fetch_url on specific result URLs. Do NOT use fetch_url as a substitute for web_search by guessing URLs.

## Tool errors

Tool errors are returned to you as results. Read the error, reason about the cause, and decide whether to retry with a corrected call, ask the user, or report failure. Do not hide errors.

## Tool output policy

Never quote or reproduce raw tool output verbatim in your response. Synthesize and summarize. For fetch_url results tagged "[HTML page — visible text extracted]": extract the relevant facts and answer the user's question directly — do not paste the extracted text back at them.

## Session notes

When a compaction summary or session notes are present (injected below), treat them as ground truth for what has already happened. Do not re-derive or contradict them without explicit user input.\
"""


@dataclass
class SystemPrompt:
    """Split system prompt: stable cacheable prefix + dynamic per-session suffix.

    The stable part is identical across all sessions and turns, making it
    eligible for Anthropic prompt caching (cache_control breakpoint goes at
    the end of this block).  The dynamic part contains per-session config,
    session notes, and compaction summaries.
    """
    stable: str
    dynamic: str


def build_system_prompt(
    cfg: Any,
    session_id: str,
    is_resume: bool,
    session_notes: str | None,
    compaction_summary: str | None,
    skills: list[Any] | None = None,
    learnings_suffix: str | None = None,
    instructions_suffix: str | None = None,
) -> SystemPrompt:
    """Assemble the full system prompt from the stable base and per-session context.

    Returns a ``SystemPrompt`` dataclass with ``.stable`` (the cacheable
    STABLE_SYSTEM_PROMPT constant) and ``.dynamic`` (the per-session
    configuration/notes suffix).  Providers use the split to place an Anthropic
    ``cache_control`` breakpoint after the stable block.

    Args:
        cfg: AedeConfig instance with model, shell, and window settings.
        session_id: ULID string for the current session.
        is_resume: Whether this session was loaded from a prior run.
        session_notes: Free-text notes persisted across compaction boundaries.
        compaction_summary: LLM-generated summary from the most recent compaction.
        learnings_suffix: Optional markdown block from build_learnings_suffix.
            When present and non-empty, appended to dynamic_parts AFTER the
            ## Session block (and after session notes/compaction summary).
            Kept in .dynamic, NOT .stable — cache breakpoint stays put.

    Args:
        instructions_suffix: Optional markdown block from
            ``aede.instructions.build_instructions_suffix``.  Injected at the
            top of the dynamic part, right after the stable prefix, so identity
            and project-level rules frame the rest of the prompt.

    Returns:
        SystemPrompt with .stable and .dynamic fields.
    """
    dynamic_parts = [""]

    if instructions_suffix:
        dynamic_parts += [instructions_suffix, ""]

    dynamic_parts += [
        "## Configuration",
        "",
        f"Model: {cfg.model}",
        f"Shell: {cfg.shell}",
        f"Tool output cap: {cfg.tool_output_max_tokens} tokens",
        f"Context window: {cfg.context_window} tokens",
        f"Compaction threshold: {cfg.compaction_threshold}",
        "",
        "## Session",
        "",
        f"Session ID: {session_id}",
        f"Status: {'resumed' if is_resume else 'new session'}",
    ]

    if is_resume and (session_notes or compaction_summary):
        if session_notes:
            dynamic_parts += ["", "## Session Notes", "", session_notes]
        if compaction_summary:
            dynamic_parts += ["", "## Compaction Summary", "", compaction_summary]

    if getattr(cfg, "grounding_enabled", True):
        dynamic_parts += [
            "",
            "## Grounding",
            "",
            "Before generating code that references project symbols (function names, class names, "
            "import paths, types), verify they exist by calling list_dir to explore the directory "
            "structure, search_files with patterns ^def  and ^class  to find real symbol names, "
            "and read_file to confirm signatures. Scope your search to the directory containing "
            "the file you are about to write. If the project directory is empty or no matches are "
            "found, proceed with your best judgment and note the uncertainty.",
        ]

    if skills:
        dynamic_parts += ["", "## Agent Skills"]
        for s in skills:
            dynamic_parts += ["", f"### {s.name}", "", s.description]

    if learnings_suffix:
        dynamic_parts += ["", learnings_suffix]

    return SystemPrompt(
        stable=STABLE_SYSTEM_PROMPT,
        dynamic="\n".join(dynamic_parts),
    )


# Code keywords used by _is_code_content heuristic.
_CODE_KEYWORDS: tuple[str, ...] = (
    "\ndef ", "\nclass ", "\nimport ", "\nfunction ", "\nconst ", "\nvar ", "\nlet ", "\n=> ",
    "\npublic ", "\nprivate ", "\nprotected ", "\nasync def ", "\nreturn ",
)


def _is_code_content(content: str) -> bool:
    """Return True when content looks like source code rather than plain prose.

    Heuristic: must have more than 3 lines AND contain at least one code keyword
    that typically starts a definition or declaration.
    """
    lines = content.splitlines()
    if len(lines) < 3:
        return False
    # Normalise for keyword matching (prepend newline so patterns work on first line too)
    normalised = "\n" + content
    return any(kw in normalised for kw in _CODE_KEYWORDS)


@dataclass
class TokenBucket:
    source: str
    source_id: str | None = None
    tokens: int = 0


@dataclass
class ContextTokenBreakdown:
    buckets: list[TokenBucket]
    total_tokens: int


def count_context_tokens(messages: list[dict]) -> ContextTokenBreakdown:
    """Return a token breakdown by source buckets."""

    buckets = {
        "system": TokenBucket(source="system", tokens=0),
        "instructions": TokenBucket(source="instructions", tokens=0),
        "skills": TokenBucket(source="skills", tokens=0),
        "mcp": TokenBucket(source="mcp", tokens=0),
        "conversation": TokenBucket(source="conversation", tokens=0),
    }

    from aede.compaction import count_tokens_approx

    def _add_to_bucket(bucket: TokenBucket, content: str | list) -> None:
        if isinstance(content, str):
            bucket.tokens += count_tokens_approx(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "") or block.get("content", "") or ""
                    if isinstance(text, str):
                        bucket.tokens += count_tokens_approx(text)
                    elif isinstance(text, list):
                        for tb in text:
                            if isinstance(tb, dict):
                                bucket.tokens += count_tokens_approx(tb.get("text", ""))

    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "")

        if role == "system":
            _add_to_bucket(buckets["system"], content)
            continue

        if isinstance(content, str):
            if content.startswith("## Instructions") or "## Agent Skills" in content:
                _add_to_bucket(buckets["instructions"], content)
                continue
            if "## Skill:" in content or "skill:" in content.lower()[:200]:
                _add_to_bucket(buckets["skills"], content)
                continue

        if isinstance(content, list):
            is_mcp = False
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_use" and block.get("name", "").startswith("mcp__"):
                        is_mcp = True
                    elif block.get("type") == "tool_result" and block.get("is_mcp", False):
                        is_mcp = True
            if is_mcp:
                _add_to_bucket(buckets["mcp"], content)
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    result = block.get("content", "")
                    if isinstance(result, str):
                        if "## Instruction" in result:
                            _add_to_bucket(buckets["instructions"], result)

        _add_to_bucket(buckets["conversation"], content)

    total = sum(b.tokens for b in buckets.values())
    return ContextTokenBreakdown(
        buckets=list(buckets.values()),
        total_tokens=total,
    )


def breakdown_to_dict(breakdown: ContextTokenBreakdown) -> dict:
    return {
        "buckets": [
            {"source": b.source, "source_id": b.source_id, "tokens": b.tokens}
            for b in breakdown.buckets
        ],
        "total_tokens": breakdown.total_tokens,
    }


def _is_html_body(text: str) -> bool:
    """Detect whether an error string contains an HTML page body."""
    lower = text[:500].lower()
    return (
        "<!doctype" in lower
        or "<html" in lower
        or "self.__next_f" in text[:500]
        or text.strip().startswith("<!")
    )


def _normalize_question_payload(tool_name: str, tool_input: dict) -> list[dict]:
    """Normalize legacy ask-user tool inputs into the unified questions format.

    For the ``question`` tool, the input is already in the unified format —
    pass through the ``questions`` array.

    For legacy aliases, construct a single-element question list:
      - ``ask_user`` → type=text
      - ``ask_user_choices`` → type=single with options
      - ``ask_user_confirm`` → type=single with yes/no options

    Returns:
        List of unified question dicts matching the ``question`` tool schema.
    """
    if tool_name == "question":
        return tool_input.get("questions", [])
    if tool_name == "ask_user_choices":
        return [{
            "header": "Question",
            "question": tool_input.get("question", ""),
            "type": "single",
            "options": tool_input.get("choices", []),
            "required": True,
        }]
    if tool_name == "ask_user_confirm":
        return [{
            "header": "Confirm",
            "question": tool_input.get("question", ""),
            "type": "single",
            "options": ["yes", "no"],
            "required": True,
        }]
    # ask_user (default)
    return [{
        "header": "Question",
        "question": tool_input.get("question", ""),
        "type": "text",
        "required": True,
    }]


def _build_auto_answers(questions: list[dict]) -> dict:
    """Build safe-default answers for AUTO permission mode.

    Returns a dict mapping each question's text to its default answer:
      - ``single`` → first option, or ``"[auto mode: skipped]"``
      - ``multi`` → ``[first option]`` or ``[]``
      - ``text`` → ``"[auto mode: skipped]"``
    """
    answers = {}
    for q in questions:
        qtext = q.get("question", "")
        qtype = q.get("type", "single")
        options = q.get("options") or []
        if qtype == "multi":
            answers[qtext] = [options[0]] if options else []
        elif qtype == "single":
            answers[qtext] = options[0] if options else "[auto mode: skipped]"
        else:
            answers[qtext] = "[auto mode: skipped]"
    return answers


class AgentLoop:
    """Stateful multi-turn agent that coordinates provider, tools, gate, and DB.

    Each call to ``run_turn`` appends the user message, streams an LLM
    response, dispatches any tool calls (subject to the approval gate and
    hard-deny hooks), collects tool results, and loops until the model
    stops requesting tools.  Context compaction is triggered automatically
    before each provider call when the conversation approaches the limit.
    """

    def __init__(
        self,
        cfg: Any,
        session: Any,
        db: Any,
        rollout: Any,
        router: Any,
        gate_store: Any,
        tracker: Any,
        console: Any,
        project_dir: Any,
        gate_backend: Any = None,
        ask_user_backend: Any = None,
        acp_manager: Any = None,
        stream_text: Any = None,
        stream_thinking: Any = None,
        stream_tool_call: Any = None,
        stream_tool_result: Any = None,
    ) -> None:
        self._cfg = cfg
        self._session = session
        self._db = db
        self._rollout = rollout
        self._router = router
        self._gate_store = gate_store
        self._tracker = tracker
        self._console = console
        self._project_dir = project_dir
        self._acp_manager = acp_manager
        self._stream_text = stream_text
        self._stream_thinking = stream_thinking
        self._stream_tool_call = stream_tool_call
        self._stream_tool_result = stream_tool_result
        self._accumulated_thinking = ""
        self._current_assist_id: str | None = None

        from aede.gate import TerminalGateBackend, TerminalAskUserBackend, PermissionMode
        self._gate_backend = gate_backend or TerminalGateBackend(
            store=self._gate_store,
            project_dir=self._project_dir,
            global_config_path=self._cfg.home / "config.yml",
            console=self._console,
        )
        self._ask_user_backend = ask_user_backend or TerminalAskUserBackend(
            console=self._console,
        )
        session_mode = getattr(session, "gate_mode", None)
        self._mode = PermissionMode.from_str(session_mode or getattr(cfg, "gate_mode", "normal"))

        self._messages: list[dict] = []
        self._turn = 0
        self._provider: Any = None
        self._stop_requested = asyncio.Event()
        self._stop_after_current_tool = asyncio.Event()
        self._system_prompt: SystemPrompt | None = None
        self._skills: list[Any] | None = None
        self._learnings_suffix: str | None = None
        self._trace_logger: Any = None

    def initialize(
        self,
        is_resume: bool = False,
        session_notes: str | None = None,
        compaction_summary: str | None = None,
        prior_messages: list[dict] | None = None,
        skills: list[Any] | None = None,
        learnings_suffix: str | None = None,
        initial_task: str | None = None,
        instructions_suffix: str | None = None,
    ) -> None:
        """Build the system prompt and optionally restore prior message history.

        When ``initial_task`` is provided, ``build_learnings_suffix`` is called
        to retrieve relevant learnings and append them to the dynamic part of
        the system prompt.  Errors in retrieval are swallowed — a suffix failure
        must never prevent the session from starting.

        Must be called once before the first ``run_turn``.
        """
        self._skills = skills
        if learnings_suffix is None and initial_task:
            try:
                from aede.memory.injection import build_learnings_suffix
                learnings_suffix = build_learnings_suffix(
                    initial_task,
                    db=self._db,
                ) or None
            except Exception:
                learnings_suffix = None
        self._learnings_suffix = learnings_suffix
        self._system_prompt = build_system_prompt(
            cfg=self._cfg,
            skills=skills,
            learnings_suffix=learnings_suffix,
            instructions_suffix=instructions_suffix,
            session_id=self._session.id,
            is_resume=is_resume,
            session_notes=session_notes,
            compaction_summary=compaction_summary,
        )
        if prior_messages:
            self._messages = list(prior_messages)

    def request_stop(self) -> None:
        self._stop_requested.set()

    def request_stop_after_current_tool(self) -> None:
        self._stop_after_current_tool.set()

    def _enrich_edit_args(self, name: str, args: dict) -> dict:
        """For full-content write tools, attach ``old_string``/``new_string`` so
        the UI renders an inline diff identical to ACP "Edit" tool calls.

        Native ``write_file``/``create_file`` only carry ``{path, content}``;
        without an old/new pair the UI falls back to a raw JSON block.  We read
        the file's current contents *before* the write executes (this runs at
        emit time, prior to ``_router.execute_sync``) so the diff shows what
        actually changed.  Best-effort: any failure leaves args untouched.
        """
        if name not in ("write_file", "create_file"):
            return args
        new_content = args.get("content")
        path_str = args.get("path")
        if not isinstance(new_content, str) or not isinstance(path_str, str):
            return args
        from pathlib import Path
        old_content = ""
        if name == "write_file":
            try:
                p = Path(path_str)
                if p.exists():
                    old_content = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return args
        # Don't mutate the caller's dict (it feeds tool execution + trace).
        return {**args, "old_string": old_content, "new_string": new_content}

    def _emit_tool_call(self, call_id: str, name: str, args: dict) -> None:
        """Forward a tool-call start to the UI stream, if a callback is wired.

        Uses ``getattr`` so partially-constructed instances (e.g. tests using
        ``AgentLoop.__new__``) and the terminal CLI path are both safe.
        """
        # Persist to DB
        if self._current_assist_id:
            import json as _json
            self._db.upsert_tool_call(
                id=call_id,
                message_id=self._current_assist_id,
                tool_name=name,
                args=_json.dumps(args),
                status="running",
                provider='aede',
            )
        # Forward to UI
        cb = getattr(self, "_stream_tool_call", None)
        if cb:
            import asyncio as _asyncio
            _asyncio.ensure_future(cb(call_id, name, args))

    def _persist_tool_call(self, call_id: str, name: str, args: dict) -> None:
        """Persist a tool-call to DB without emitting a UI event.

        Used for ask_user tools where the UI is driven by ``ask_user_request``
        WS events instead of ``tool_call`` events.
        """
        if self._current_assist_id:
            import json as _json
            self._db.upsert_tool_call(
                id=call_id,
                message_id=self._current_assist_id,
                tool_name=name,
                args=_json.dumps(args),
                status="running",
                provider='aede',
            )

    def _emit_tool_result(self, call_id: str, status: str, output: str, duration_ms: int) -> None:
        """Forward a tool result to the UI stream, if a callback is wired."""
        # Persist to DB
        if self._current_assist_id:
            self._db.update_tool_call(
                id=call_id,
                result=output,
                status=status,
                duration_ms=duration_ms,
            )
        # Forward to UI
        cb = getattr(self, "_stream_tool_result", None)
        if cb:
            import asyncio as _asyncio
            _asyncio.ensure_future(cb(call_id, status, output, duration_ms))

    def _get_provider(self) -> Any:
        """Lazily instantiate and cache the provider selected by config."""
        if self._provider is None:
            from aede.provider import get_provider
            self._provider = get_provider(self._cfg, acp_manager=self._acp_manager)
            if self._stream_text is not None and hasattr(self._provider, '_stream_text'):
                self._provider._stream_text = self._stream_text
            # ACP agents run tools in-subprocess; surface them to the UI too.
            if hasattr(self._provider, '_stream_tool_call'):
                self._provider._stream_tool_call = getattr(self, '_stream_tool_call', None)
            if hasattr(self._provider, '_stream_tool_result'):
                self._provider._stream_tool_result = getattr(self, '_stream_tool_result', None)
        return self._provider

    def _get_trace_logger(self) -> Any:
        """Lazily instantiate and cache the TraceLogger for this session."""
        if self._trace_logger is None:
            from aede.trace.logger import TraceLogger  # lazy
            self._trace_logger = TraceLogger(self._cfg.data_dir / "traces")
        return self._trace_logger

    async def run_turn(self, user_input: str) -> None:
        """Process one user turn end-to-end.

        Appends the user message to history, persists it in the DB and rollout
        log, calls the provider (streaming), dispatches any tool calls through
        the approval gate and hard-deny hooks, and loops until the model emits
        a response with no pending tool calls.

        Returns early if the agent gets stuck (same tool call fails 3 times in
        a row), printing a warning.
        """
        self._turn += 1
        self._messages.append({"role": "user", "content": user_input})

        from ulid import ULID
        msg_id = str(ULID())
        self._db.insert_message(
            id=msg_id,
            session_id=self._session.id,
            role="user",
            content=user_input,
            token_count=None,
        )
        self._rollout.write({"type": "user_message", "content": user_input})

        await self._maybe_compact()

        retry_count: dict[str, int] = {}
        # validation_retry tracks per-call validation failures; each call may
        # be retried ONCE after injecting the ToolParamError back as a result.
        validation_retry: dict[str, int] = {}

        # T-13x — GEPA trace accumulators (reset per turn)
        _trace_input_tokens: int = 0
        _trace_output_tokens: int = 0
        _trace_cached_tokens: int = 0
        _trace_tool_calls: list[dict] = []
        _trace_reasoning_text: str = ""
        _trace_outcome: str = "completed"

        while True:
            # Pre-allocate the assistant message row BEFORE calling the
            # provider.  ACP agents run tools in their subprocess and report
            # them mid-stream (during stream_turn), so the persist callback
            # needs _current_assist_id set and the message row to exist for the
            # tool_calls FK.  Native providers return tool calls only after the
            # stream completes, so this reordering is harmless for them.
            assist_id = str(ULID())
            self._current_assist_id = assist_id
            self._db.insert_message(
                id=assist_id,
                session_id=self._session.id,
                role="assistant",
                content="",
                token_count=None,
            )

            resp = await self._stream_response()
            if resp is None:
                # Provider failed; drop the empty placeholder (and any tool
                # calls persisted against it) so it doesn't show as a blank
                # assistant message on refetch.
                self._current_assist_id = None
                self._db.delete_message(assist_id)
                break

            self._tracker.record(
                turn=self._turn,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cached_tokens=resp.cached_tokens,
            )

            # T-13x — accumulate token totals across all iterations of this turn
            _trace_input_tokens += resp.input_tokens
            _trace_output_tokens += resp.output_tokens
            _trace_cached_tokens += resp.cached_tokens

            text_response = resp.text
            tool_calls = resp.tool_calls  # list of {"id", "name", "input"}

            # Finalize the pre-allocated assistant row with the streamed text.
            self._db.update_message(
                id=assist_id,
                content=text_response or "",
                token_count=resp.output_tokens,
                thinking=self._accumulated_thinking or None,
            )
            if text_response:
                _trace_reasoning_text = text_response
                self._rollout.write({
                    "type": "assistant_message",
                    "content": text_response,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "cached_tokens": resp.cached_tokens,
                })

            # Append assistant message in Anthropic format (for round-tripping)
            self._messages.append({
                "role": "assistant",
                "content": resp.assistant_content_blocks,
            })

            if not tool_calls:
                break

            tool_results = []
            # batch_approved is scoped to THIS assistant message's tool_calls list.
            # It is only honoured when len(tool_calls) <= batch_approval_max.
            batch_approved: bool = False
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_input = tc["input"]
                tool_use_id = tc["id"]

                from aede.tools.router import UnknownToolError
                try:
                    self._router.validate_name(tool_name)
                except UnknownToolError:
                    self._console.print(f"[red]Unknown tool: {tool_name!r}. Valid: {self._router.tool_names()}[/red]")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Error: Unknown tool {tool_name!r}. Valid tools: {self._router.tool_names()}",
                        "is_error": True,
                    })
                    continue

                from aede.hooks import pre_tool_use, HardDeniedError
                try:
                    pre_tool_use(tool_name, tool_input)
                except HardDeniedError as e:
                    self._console.print(f"[red]⛔ Hard denied: {e.matched}[/red]")
                    self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id, "status": "hard_denied"})
                    self._emit_tool_call(tool_use_id, tool_name, tool_input)
                    self._emit_tool_result(tool_use_id, "denied", f"Hard denied: {e.matched!r}", 0)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Hard denied: command matches dangerous pattern: {e.matched!r}",
                        "is_error": True,
                    })
                    continue

                # Permission mode pre-check: allow or deny before gate
                tool_action = self._gate_store.tool_action(tool_name, tool_input)
                if tool_action == "deny":
                    self._console.print(f"[red]⛔ Denied by permission mode ({self._mode.value}): {tool_name}[/red]")
                    self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id, "status": "mode_denied"})
                    self._emit_tool_call(tool_use_id, tool_name, tool_input)
                    self._emit_tool_result(tool_use_id, "denied", f"Denied by permission mode ({self._mode.value})", 0)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Denied by permission mode ({self._mode.value})",
                        "is_error": True,
                    })
                    continue

                # Ask-user tools: route to ask_user_backend instead of gate
                if tool_name in {"ask_user", "ask_user_choices", "ask_user_confirm", "question"}:
                    import uuid
                    from aede.gate import PermissionMode

                    qid = uuid.uuid4().hex[:8]
                    self._persist_tool_call(tool_use_id, tool_name, tool_input)

                    questions = _normalize_question_payload(tool_name, tool_input)

                    if self._mode is PermissionMode.AUTO:
                        answers = _build_auto_answers(questions)
                    else:
                        try:
                            answers = await self._ask_user_backend.ask(
                                question_id=qid,
                                questions=questions,
                            )
                        except Exception as exc:
                            answers = {"error": str(exc)}

                    result_json = json.dumps({"answers": answers})
                    self._emit_tool_result(tool_use_id, "success", result_json, 0)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_json,
                        "is_error": False,
                    })
                    continue

                # BC-04/05: Run critic before the gate for write_file / create_file
                # with code-like content, when critic is enabled.
                if (
                    tool_name in {"write_file", "create_file"}
                    and getattr(self._cfg, "critic_enabled", False)
                    and _is_code_content(tool_input.get("content", ""))
                ):
                    await self._run_critic_panel(tool_input)

                needs_approval = tool_action != "allow" and self._router.requires_approval(tool_name)
                if not self._gate_store.is_allowed(tool_name) and needs_approval and not batch_approved:
                    import uuid
                    from aede.gate import GateDecision
                    gate_id = uuid.uuid4().hex[:8]
                    decision, redirect_msg = await self._gate_backend.request(
                        gate_id=gate_id,
                        tool_name=tool_name,
                        args=tool_input,
                        batch_count=len(tool_calls),
                        mode=self._mode,
                    )
                    if decision == GateDecision.DENY:
                        self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id, "status": "denied"})
                        self._emit_tool_call(tool_use_id, tool_name, tool_input)
                        self._emit_tool_result(tool_use_id, "denied", "Tool call denied by user.", 0)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": "Tool call denied by user.",
                            "is_error": True,
                        })
                        continue
                    elif decision in (GateDecision.REDIRECT, GateDecision.BATCH_DENY):
                        if redirect_msg:
                            self._messages.append({"role": "user", "content": redirect_msg})
                        continue
                    elif decision == GateDecision.BATCH_APPROVE:
                        batch_approval_max = self._cfg.batch_approval_max
                        if len(tool_calls) <= batch_approval_max:
                            batch_approved = True
                        else:
                            self._console.print(
                                f"[yellow]Batch of {len(tool_calls)} exceeds "
                                f"batch_approval_max={batch_approval_max} — approving individually[/yellow]"
                            )

                # Validate params before execution.  On failure inject an
                # is_error tool_result (re-prompts the model) and allow ONE
                # corrected attempt per unique call key.
                from aede.tools.router import ToolParamError
                try:
                    self._router.validate_args(tool_name, tool_input)
                except ToolParamError as ve:
                    val_key = f"val:{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
                    validation_retry[val_key] = validation_retry.get(val_key, 0) + 1
                    if validation_retry[val_key] > 1:
                        self._console.print("[yellow]⚠ Agent is stuck on an invalid tool call. Intervene or /clear to start over.[/yellow]")
                        _trace_outcome = "stuck"
                        self._write_turn_trace(_trace_input_tokens, _trace_output_tokens, _trace_cached_tokens, _trace_tool_calls, _trace_reasoning_text, _trace_outcome)
                        return
                    self._console.print(f"[yellow]⚠ Param validation failed for {tool_name!r}: {ve}[/yellow]")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Parameter validation error: {ve}",
                        "is_error": True,
                    })
                    continue

                # self._console.print(f"⚡ {tool_name} · running...")
                self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id})
                # Enrich write/create with an old/new pair so the UI shows an
                # inline diff (same shape as ACP edits).  Read happens before
                # the tool executes below, so old content is still on disk.
                self._emit_tool_call(tool_use_id, tool_name, self._enrich_edit_args(tool_name, tool_input))

                call_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
                was_retry = call_key in retry_count

                _tool_stream_cb = None
                if hasattr(self._console, 'stream_tool_output'):
                    _tool_stream_cb = lambda line, _tid=tool_use_id: self._console.stream_tool_output(_tid, line)
                result = self._router.execute_sync(tool_name, tool_input, stream_callback=_tool_stream_cb)

                self._rollout.write({
                    "type": "tool_result",
                    "call_id": tool_use_id,
                    "status": result.status,
                    "result": result.output[:500],
                    "duration_ms": result.duration_ms,
                })
                self._emit_tool_result(tool_use_id, result.status, result.output, result.duration_ms)

                if result.status == "error":
                    score = 0.0
                    passed = False
                elif was_retry:
                    score = 0.5
                    passed = True
                else:
                    score = 1.0
                    passed = True

                # T-13x — record tool call for trace
                _trace_tool_calls.append({
                    "name": tool_name,
                    "args": tool_input,
                    "result": result.output[:200],
                    "duration_ms": result.duration_ms,
                    "score": score,
                    "passed": passed,
                })

                if result.status == "error":
                    retry_count[call_key] = retry_count.get(call_key, 0) + 1
                    if retry_count[call_key] >= 3:
                        self._console.print("[yellow]⚠ Agent is stuck on a failing tool call. Intervene or /clear to start over.[/yellow]")
                        _trace_outcome = "stuck"
                        self._write_turn_trace(_trace_input_tokens, _trace_output_tokens, _trace_cached_tokens, _trace_tool_calls, _trace_reasoning_text, _trace_outcome)
                        return
                else:
                    retry_count.pop(call_key, None)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result.output,
                    "is_error": result.status == "error",
                })

            if tool_results:
                self._messages.append({"role": "user", "content": tool_results})

        # T-13x — write one trace record for the completed turn
        self._write_turn_trace(
            _trace_input_tokens,
            _trace_output_tokens,
            _trace_cached_tokens,
            _trace_tool_calls,
            _trace_reasoning_text,
            _trace_outcome,
        )

    def _write_turn_trace(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        tool_calls: list,
        reasoning_text: str,
        outcome: str,
    ) -> None:
        """Write one GEPA trace record for the current turn.  Defensive — never crashes run_turn."""
        try:
            logger = self._get_trace_logger()
            logger.write_turn_trace(
                session_id=self._session.id,
                turn_number=self._turn,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
                tool_calls=tool_calls,
                reasoning_text=reasoning_text,
                outcome=outcome,
            )
        except Exception:
            self._console.print("[dim]⚠ trace write failed[/dim]")

    # Transient HTTP status codes that warrant a retry.
    _TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503})
    # Maximum total attempts (1 initial + 2 retries = 3 total).
    _MAX_ATTEMPTS: int = 3

    async def _stream_response(self) -> Any:
        """Call the active provider and return a NormalizedResponse, or None on error.

        Retries up to ``_MAX_ATTEMPTS`` times on transient API errors (status
        codes in ``_TRANSIENT_STATUS_CODES``), sleeping ``BACKOFF_BASE * 2**attempt``
        seconds between attempts.  Non-transient errors (e.g. 400, 401) are
        surfaced immediately without retry.
        """
        provider = self._get_provider()
        last_exc: Exception | None = None
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                self._accumulated_thinking = ""

                async def _accumulate_thinking(text: str):
                    self._accumulated_thinking += text
                    if self._stream_thinking:
                        await self._stream_thinking(text)

                return await provider.stream_turn(
                    model=self._cfg.model,
                    system=self._system_prompt,
                    tools=self._router.anthropic_tool_schemas(),
                    messages=self._messages,
                    max_tokens=8096,
                    console=self._console,
                    reasoning_effort=self._cfg.reasoning_effort,
                    thinking_budget=self._cfg.thinking_budget,
                    stream_text=self._stream_text,
                    stream_thinking=_accumulate_thinking,
                )
            except Exception as e:
                status_code: int | None = getattr(e, "status_code", None)
                if status_code in self._TRANSIENT_STATUS_CODES and attempt < self._MAX_ATTEMPTS - 1:
                    # Transient error with attempts remaining — backoff and retry.
                    delay = BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                # Non-transient, or exhausted retries — surface the error.
                self._handle_api_error(e)
                return None
        # Exhausted all retries on a transient error.
        if last_exc is not None:
            self._handle_api_error(last_exc)
        return None

    def _handle_api_error(self, e: Exception) -> None:
        """Print a short, sanitised error message — never dump raw HTML."""
        error_str = str(e)

        # Try to extract status code from SDK error types
        status_code: int | None = None
        try:
            # Both anthropic.APIStatusError and openai.APIStatusError have .status_code
            status_code = getattr(e, "status_code", None)
        except Exception:
            pass

        error_msg: str
        if _is_html_body(error_str):
            code_part = f" {status_code}" if status_code else ""
            error_msg = (
                f"API error{code_part}: endpoint returned an HTML page "
                f"(likely wrong base_url or model not available at this endpoint). "
                f"Check api_base_url and model id in your config."
            )
        elif status_code is not None:
            first_line = error_str.split("\n")[0][:200]
            error_msg = f"API error {status_code}: {first_line}"
        else:
            first_line = error_str.split("\n")[0][:200]
            error_msg = f"API error: {first_line}"

        send_error = getattr(self._console, "error", None)
        if send_error is not None:
            send_error(error_msg)
        else:
            self._console.print(f"[red]{error_msg}[/red]")

    async def _run_critic_panel(self, tool_input: dict) -> None:
        """Call the critic LLM, render a Rich panel of findings, and handle failures.

        This is BC-05: non-fatal — any exception from the critic is caught and
        a warning is printed.  The caller (run_turn) proceeds to prompt_gate
        regardless of outcome.
        """
        from rich.panel import Panel
        from rich.text import Text
        import aede.critic as _critic

        code = tool_input.get("content", "")
        path = tool_input.get("path", "<unknown>")
        task_context = f"Writing file: {path}"

        try:
            findings = await _critic.evaluate(
                self._cfg,
                code=code,
                task_context=task_context,
                tracker=self._tracker,
                turn=self._turn,
            )
        except Exception as exc:
            self._console.print(f"[dim yellow]⚠ Critic unavailable: {exc}[/dim yellow]")
            return

        if not findings:
            self._console.print("[dim]Critic: no issues found.[/dim]")
            return

        # Build a Rich Text with severity-coloured lines.
        _SEVERITY_COLOR: dict[str, str] = {
            "HIGH": "bold red",
            "MEDIUM": "yellow",
            "LOW": "dim",
        }
        lines = Text()
        for f in findings:
            color = _SEVERITY_COLOR.get(f.severity.upper(), "white")
            lines.append(f"[{f.severity}] ", style=color)
            lines.append(f.message + "\n")

        panel = Panel(lines, title="[bold]Critic Findings[/bold]", border_style="yellow")
        self._console.print(panel)

    def _dedup_read_results(self) -> int:
        """Replace older read_file results in message history with stubs.

        Scans tool_result blocks for read_file output (``<file /path ...>``),
        tracks unique paths, and stubs all but the most recent occurrence
        with a placeholder that reports how many tokens were saved.

        Returns:
            The number of tokens saved by deduplication.
        """
        from aede.compaction import count_tokens_approx
        tokens_saved = 0
        path_to_latest: dict[str, int] = {}

        for i, msg in enumerate(self._messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                result_text = block.get("content", "")
                if not isinstance(result_text, str):
                    continue
                if not result_text.startswith("<file "):
                    continue
                try:
                    header_end = result_text.index(">")
                    header = result_text[5:header_end]
                    path = header.split(" lines")[0] if " lines" in header else header
                except ValueError:
                    continue

                if path in path_to_latest:
                    tok_count = count_tokens_approx(result_text)
                    tokens_saved += tok_count
                    block["content"] = f"[dedup: read earlier in session - ~{tok_count} tokens saved]"
                else:
                    path_to_latest[path] = i

        return tokens_saved

    async def _maybe_compact(self) -> None:
        """Run compaction if the current message history exceeds the threshold.

        This is the automatic path called before each provider request.
        It is a no-op when the history is below the compaction threshold.
        See ``compact()`` for the forced manual path.
        """
        saved = self._dedup_read_results()
        if saved > 0:
            self._console.print(f"[dim]\u21a9 Deduped read results: ~{saved} tokens saved[/dim]")

        from aede.compaction import needs_compaction
        breakdown = count_context_tokens(self._messages)
        current_tokens = breakdown.total_tokens
        if not needs_compaction(current_tokens, self._cfg.context_window, self._cfg.compaction_threshold):
            return
        await self._run_compaction_body()

    async def compact(self) -> dict:
        """Manually trigger compaction regardless of the current token count.

        Intended for the ``/compact`` CLI command.  Bypasses the threshold
        check and always invokes the compaction body.

        Returns:
            A dict with at minimum a ``"method"`` key reflecting what
            ``run_compaction`` returned (e.g. ``"string_pass_only"``,
            ``"llm_summary"``, or ``"none"``).
        """
        return await self._run_compaction_body()

    async def _run_compaction_body(self) -> dict:
        """Execute the full compaction sequence and update message history.

        Shared implementation used by both ``_maybe_compact`` (auto) and
        ``compact`` (manual/forced).  Selects the appropriate LLM client,
        calls ``run_compaction``, and persists the result if compaction fired.

        Resolution order:
          1. If ``cfg.compaction_model`` is set, use it and create an
             Anthropic client — compaction always goes through the Messages
             API regardless of the active provider.
          2. If the active provider is Anthropic, use its ``raw_client`` and
             the active model.
          3. Otherwise, fall back to a bare Anthropic client with the default
             model (requires ANTHROPIC_API_KEY).

        Returns:
            The raw ``run_compaction`` result dict.
        """
        self._console.print("[dim]↩ Compacting context...[/dim]")

        import os
        import anthropic

        provider = self._get_provider()
        from aede.provider import AnthropicProvider

        # Explicit compaction model override — user chose a model for compaction.
        if self._cfg.compaction_model:
            compaction_model = self._cfg.compaction_model
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            compaction_client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None
        elif isinstance(provider, AnthropicProvider):
            compaction_client = provider.raw_client
            compaction_model = self._cfg.model
        else:
            # Non-Anthropic provider, no explicit compaction_model.
            # Fall back to default model via bare Anthropic client.
            from aede.config import DEFAULT_CONFIG
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            compaction_client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else None
            compaction_model = DEFAULT_CONFIG["model"]

        if compaction_client is None:
            self._console.print("[yellow]⚠ Skipping compaction — ANTHROPIC_API_KEY not set for non-Anthropic provider.[/yellow]")
            return {"method": "none"}

        from aede.compaction import run_compaction
        result = await run_compaction(
            messages=self._messages,
            context_window=self._cfg.context_window,
            threshold=self._cfg.compaction_threshold,
            session_notes_path=self._cfg.data_dir / "sessions" / f"{self._session.id}-notes.md",
            anthropic_client=compaction_client,
            model=compaction_model,
        )

        if result["method"] != "none":
            self._messages = result["messages"]
            self._rollout.write({
                "type": "compaction",
                "summary": result.get("summary", ""),
                "messages_compacted": result.get("messages_compacted", 0),
                "tokens_reclaimed": result.get("tokens_reclaimed", 0),
            })
            self._console.print(
                f"↩ Context compacted · {result.get('messages_compacted', 0)} messages → summary · method: {result['method']}"
            )

        # Step 4: stamp compacted_at on DB rows for the summarized middle messages.
        # This only applies to the llm_summary path — string_pass_only keeps all
        # messages in-memory (just with stubbed content) so no DB stamp is needed.
        #
        # Alignment assumption: run_compaction preserves head (first 3 rows) and
        # tail (last 15 rows) of the collapsed message list.  We mirror that split
        # here by excluding the first 3 and last 15 DB rows from the stamp set.
        # This couples to the head=3/tail=15 constants in run_compaction; if those
        # change, this exclusion must change too.
        if result["method"] == "llm_summary":
            all_rows = self._db.get_messages(self._session.id, include_compacted=True)
            HEAD = 3
            TAIL = 15
            middle_rows = all_rows[HEAD : max(HEAD, len(all_rows) - TAIL)]
            middle_ids = [row["id"] for row in middle_rows]
            if middle_ids:
                self._db.mark_messages_compacted(middle_ids)

        return result
