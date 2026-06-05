from __future__ import annotations
import asyncio
import json
import time
from typing import Any

STABLE_SYSTEM_PROMPT = """\
You are a personal AI agent assistant running as a CLI tool called Jarvis.

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
- web_search: Search the web via Brave Search. Runs automatically.

When a tool requires approval, a gate will be shown to the user before execution. Do not assume approval — wait for the result before continuing.

## Research rule

For any research task — finding current documentation, investigating a tool, library, API, framework, or any fact about the state of the world — you MUST use web_search and fetch_url. Do not answer research questions from training knowledge. Training data has a cutoff and produces stale or hallucinated results for fast-moving technical topics.

## Tool errors

Tool errors are returned to you as results. Read the error, reason about the cause, and decide whether to retry with a corrected call, ask the user, or report failure. Do not hide errors.

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
    from jarvis.compaction import count_tokens_approx
    return sum(count_tokens_approx(m.get("content", "")) for m in messages)


class AgentLoop:
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
        self._client: Any = None
        self._system_prompt: str = ""

    def initialize(
        self,
        is_resume: bool = False,
        session_notes: str | None = None,
        compaction_summary: str | None = None,
        prior_messages: list[dict] | None = None,
    ) -> None:
        import anthropic
        import os
        base_url = self._cfg.api_base_url
        if base_url:
            api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("OPENROUTER_API_KEY (or ANTHROPIC_API_KEY) not set in environment.")
            self._client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set in environment.")
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._system_prompt = build_system_prompt(
            cfg=self._cfg,
            session_id=self._session.id,
            is_resume=is_resume,
            session_notes=session_notes,
            compaction_summary=compaction_summary,
        )
        if prior_messages:
            self._messages = list(prior_messages)

    async def run_turn(self, user_input: str) -> None:
        import anthropic

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

        while True:
            response = await self._stream_response()
            if response is None:
                break

            usage = response.usage
            self._tracker.record(
                turn=self._turn,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
            )

            content = response.content
            text_parts = [b.text for b in content if hasattr(b, "text")]
            text_response = "".join(text_parts)

            tool_use_blocks = [b for b in content if b.type == "tool_use"]

            if text_response:
                assist_id = str(ULID())
                self._db.insert_message(
                    id=assist_id,
                    session_id=self._session.id,
                    role="assistant",
                    content=text_response,
                    token_count=usage.output_tokens,
                )
                self._rollout.write({
                    "type": "assistant_message",
                    "content": text_response,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cached_tokens": getattr(usage, "cache_read_input_tokens", 0),
                })

            if not tool_use_blocks:
                self._messages.append({"role": "assistant", "content": content})
                break

            self._messages.append({"role": "assistant", "content": content})

            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                from jarvis.tools.router import UnknownToolError
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

                from jarvis.hooks import pre_tool_use, HardDeniedError
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
                if not self._gate_store.is_allowed(tool_name) and needs_approval:
                    from jarvis.gate import prompt_gate, GateDecision
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

    async def _stream_response(self) -> Any:
        self._console.print("[dim]thinking...[/dim]", end="\r")
        try:
            async with self._client.messages.stream(
                model=self._cfg.model,
                max_tokens=8096,
                system=self._system_prompt,
                tools=self._router.anthropic_tool_schemas(),
                messages=self._messages,
            ) as stream:
                async for text in stream.text_stream:
                    self._console.print(text, end="", highlight=False)
                self._console.print()
                return await stream.get_final_message()
        except Exception as e:
            self._console.print(f"[red]API error: {e}[/red]")
            return None

    async def _maybe_compact(self) -> None:
        from jarvis.compaction import needs_compaction, count_tokens_approx
        current_tokens = sum(
            count_tokens_approx(m.get("content", "") if isinstance(m.get("content"), str) else "")
            for m in self._messages
        )
        if not needs_compaction(current_tokens, self._cfg.context_window, self._cfg.compaction_threshold):
            return

        self._console.print("[dim]↩ Compacting context...[/dim]")

        from jarvis.compaction import run_compaction
        result = await run_compaction(
            messages=self._messages,
            context_window=self._cfg.context_window,
            threshold=self._cfg.compaction_threshold,
            session_notes_path=self._cfg.data_dir / "sessions" / f"{self._session.id}-notes.md",
            anthropic_client=self._client,
            model=self._cfg.model,
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
