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
- read_file: Read a file at a given path. Runs automatically.
- write_file: Overwrite an existing file. REQUIRES USER APPROVAL. Fails if the file does not exist — use create_file instead.
- create_file: Create a new file. REQUIRES USER APPROVAL. Fails if the file already exists — use write_file instead.
- list_dir: List directory contents. Runs automatically.
- search_files: Search for a pattern across files (ripgrep). Runs automatically.
- fetch_url: HTTP GET a URL and return its content as text. Does not execute JavaScript. Runs automatically.
- web_search: Search the web via DuckDuckGo. No API key required. Runs automatically.

When a tool requires approval, a gate will be shown to the user before execution. Do not assume approval — wait for the result before continuing.

## Research rule

For any research task — finding current documentation, investigating a tool, library, API, framework, or any fact about the state of the world — use web_search first, then fetch_url on specific result URLs. Do NOT use fetch_url as a substitute for web_search by guessing URLs.

## Tool errors

Tool errors are returned to you as results. Read the error, reason about the cause, and decide whether to retry with a corrected call, ask the user, or report failure. Do not hide errors.

## Tool output policy

Never quote or reproduce raw tool output verbatim in your response. Synthesize and summarize. For fetch_url results tagged "[HTML page — visible text extracted]": extract the relevant facts and answer the user's question directly — do not paste the extracted text back at them.

## Session notes

When a compaction summary or session notes are present (injected below), treat them as ground truth for what has already happened. Do not re-derive or contradict them without explicit user input.\
"""


def build_system_prompt(
    cfg: Any,
    session_id: str,
    is_resume: bool,
    session_notes: str | None,
    compaction_summary: str | None,
) -> str:
    """Assemble the full system prompt from the stable base and per-session context.

    Appends configuration values and, for resumed sessions, injects any
    persisted session notes and compaction summaries so the model can
    reconstruct prior context.

    Args:
        cfg: AedeConfig instance with model, shell, and window settings.
        session_id: ULID string for the current session.
        is_resume: Whether this session was loaded from a prior run.
        session_notes: Free-text notes persisted across compaction boundaries.
        compaction_summary: LLM-generated summary from the most recent compaction.

    Returns:
        The complete system prompt string to pass to the provider.
    """
    suffix_parts = [
        STABLE_SYSTEM_PROMPT,
        "",
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
            suffix_parts += ["", "## Session Notes", "", session_notes]
        if compaction_summary:
            suffix_parts += ["", "## Compaction Summary", "", compaction_summary]

    return "\n".join(suffix_parts)


def count_context_tokens(messages: list[dict]) -> int:
    """Return a rough token count for a list of message dicts."""
    from aede.compaction import count_tokens_approx
    return sum(count_tokens_approx(m.get("content", "")) for m in messages)


def _is_html_body(text: str) -> bool:
    """Detect whether an error string contains an HTML page body."""
    lower = text[:500].lower()
    return (
        "<!doctype" in lower
        or "<html" in lower
        or "self.__next_f" in text[:500]
        or text.strip().startswith("<!")
    )


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
        self._messages: list[dict] = []
        self._turn = 0
        self._provider: Any = None
        self._system_prompt: str = ""

    def initialize(
        self,
        is_resume: bool = False,
        session_notes: str | None = None,
        compaction_summary: str | None = None,
        prior_messages: list[dict] | None = None,
    ) -> None:
        """Build the system prompt and optionally restore prior message history.

        Must be called once before the first ``run_turn``.
        """
        self._system_prompt = build_system_prompt(
            cfg=self._cfg,
            session_id=self._session.id,
            is_resume=is_resume,
            session_notes=session_notes,
            compaction_summary=compaction_summary,
        )
        if prior_messages:
            self._messages = list(prior_messages)

    def _get_provider(self) -> Any:
        """Lazily instantiate and cache the provider selected by config."""
        if self._provider is None:
            from aede.provider import get_provider
            self._provider = get_provider(self._cfg)
        return self._provider

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

        while True:
            resp = await self._stream_response()
            if resp is None:
                break

            self._tracker.record(
                turn=self._turn,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cached_tokens=resp.cached_tokens,
            )

            text_response = resp.text
            tool_calls = resp.tool_calls  # list of {"id", "name", "input"}

            if text_response:
                assist_id = str(ULID())
                self._db.insert_message(
                    id=assist_id,
                    session_id=self._session.id,
                    role="assistant",
                    content=text_response,
                    token_count=resp.output_tokens,
                )
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
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Hard denied: command matches dangerous pattern: {e.matched!r}",
                        "is_error": True,
                    })
                    continue

                needs_approval = self._router.requires_approval(tool_name)
                if not self._gate_store.is_allowed(tool_name) and needs_approval and not batch_approved:
                    from aede.gate import prompt_gate, GateDecision
                    decision, redirect_msg = prompt_gate(
                        tool_name=tool_name,
                        args=tool_input,
                        store=self._gate_store,
                        project_dir=self._project_dir,
                        global_config_path=self._cfg.home / "config.yml",
                        console=self._console,
                    )
                    if decision == GateDecision.DENY:
                        self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id, "status": "denied"})
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
                        return
                    self._console.print(f"[yellow]⚠ Param validation failed for {tool_name!r}: {ve}[/yellow]")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Parameter validation error: {ve}",
                        "is_error": True,
                    })
                    continue

                self._console.print(f"⚡ {tool_name} · running...")
                self._rollout.write({"type": "tool_call", "name": tool_name, "args": tool_input, "call_id": tool_use_id})

                result = self._router.execute_sync(tool_name, tool_input)

                self._rollout.write({
                    "type": "tool_result",
                    "call_id": tool_use_id,
                    "status": result.status,
                    "result": result.output[:500],
                    "duration_ms": result.duration_ms,
                })

                call_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
                if result.status == "error":
                    retry_count[call_key] = retry_count.get(call_key, 0) + 1
                    if retry_count[call_key] >= 3:
                        self._console.print("[yellow]⚠ Agent is stuck on a failing tool call. Intervene or /clear to start over.[/yellow]")
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
        self._console.print("[dim]thinking...[/dim]", end="\r")
        provider = self._get_provider()
        last_exc: Exception | None = None
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                return await provider.stream_turn(
                    model=self._cfg.model,
                    system=self._system_prompt,
                    tools=self._router.anthropic_tool_schemas(),
                    messages=self._messages,
                    max_tokens=8096,
                    console=self._console,
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

        if _is_html_body(error_str):
            code_part = f" {status_code}" if status_code else ""
            self._console.print(
                f"[red]API error{code_part}: endpoint returned an HTML page "
                f"(likely wrong base_url or model not available at this endpoint). "
                f"Check api_base_url and model id in your config.[/red]"
            )
            return

        if status_code is not None:
            # Extract a brief reason — first line of the error message
            first_line = error_str.split("\n")[0][:200]
            self._console.print(f"[red]API error {status_code}: {first_line}[/red]")
        else:
            first_line = error_str.split("\n")[0][:200]
            self._console.print(f"[red]API error: {first_line}[/red]")

    async def _maybe_compact(self) -> None:
        """Run compaction if the current message history exceeds the threshold.

        This is the automatic path called before each provider request.
        It is a no-op when the history is below the compaction threshold.
        See ``compact()`` for the forced manual path.
        """
        from aede.compaction import needs_compaction, count_tokens_approx
        current_tokens = sum(
            count_tokens_approx(m.get("content", "") if isinstance(m.get("content"), str) else "")
            for m in self._messages
        )
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
        ``compact`` (manual/forced).  Selects the appropriate Anthropic client,
        calls ``run_compaction``, and persists the result if compaction fired.

        For non-Anthropic providers, falls back to a bare Anthropic client
        using the default model, because the compaction call goes directly to
        api.anthropic.com and cannot use an OpenRouter model id.

        Returns:
            The raw ``run_compaction`` result dict.
        """
        self._console.print("[dim]↩ Compacting context...[/dim]")

        # Compaction always uses the active provider's raw client.
        # For Anthropic this is the AsyncAnthropic client.
        # For OpenAI-compatible providers we pass the raw client too;
        # run_compaction uses client.messages.create which only works with
        # the Anthropic client — so for non-Anthropic providers we fall back
        # to creating an Anthropic client directly.
        # TODO: make compaction provider-aware so it works with OpenAI providers.
        provider = self._get_provider()
        from aede.provider import AnthropicProvider
        if isinstance(provider, AnthropicProvider):
            compaction_client = provider.raw_client
            # Active model is already an Anthropic id — safe to reuse.
            compaction_model = self._cfg.model
        else:
            # Fall back: create a bare Anthropic client for compaction.
            # The active model (e.g. google/gemini-2.5-flash) is NOT an Anthropic
            # id, so it cannot be sent to api.anthropic.com — use a default
            # Anthropic model for the compaction call instead.
            import os
            import anthropic
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
