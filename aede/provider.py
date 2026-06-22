"""
Provider abstraction for aede agent.

Supports Anthropic (native SDK) and OpenAI-compatible endpoints (e.g. OpenRouter).
Heavy imports (anthropic, openai) are lazy — loaded inside methods, not at module level.
"""
from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from aede.agent import SystemPrompt as _SystemPrompt


@dataclass
class NormalizedResponse:
    """Normalized LLM response, independent of provider SDK."""

    text: str
    tool_calls: list[dict]  # each: {"id": str, "name": str, "input": dict}
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    # Anthropic-format content blocks so agent.py can append assistant messages
    # in Anthropic wire format regardless of which provider generated the response.
    assistant_content_blocks: list[Any] = field(default_factory=list)


@runtime_checkable
class Provider(Protocol):
    """Duck-type interface that both provider implementations satisfy."""

    model_id: str

    def has_vision(self) -> bool: ...

    async def stream_turn(
        self,
        *,
        model: str,
        system: Any,  # SystemPrompt dataclass or str for backwards compat
        tools: list[dict],
        messages: list[dict],
        max_tokens: int,
        console: Any,
        reasoning_effort: str = "auto",
        thinking_budget: int = 0,
        stream_text: Any = None,  # async Callable[[str], None] — per-token callback
        stream_thinking: Any = None,  # async Callable[[str], None] — per-thinking-delta callback
    ) -> NormalizedResponse:
        ...


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicProvider:
    """Wraps AsyncAnthropic and streams a turn, returning a NormalizedResponse."""

    def __init__(self, api_key: str, base_url: str | None = None, model_id: str = "") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None
        self.model_id = model_id

    def has_vision(self) -> bool:
        from aede.models import VISION_MODELS
        return self.model_id in VISION_MODELS

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    @property
    def raw_client(self) -> Any:
        return self._get_client()

    async def stream_turn(
        self,
        *,
        model: str,
        system: Any,
        tools: list[dict],
        messages: list[dict],
        max_tokens: int,
        console: Any,
        reasoning_effort: str = "auto",
        thinking_budget: int = 0,
        stream_text: Any = None,
        stream_thinking: Any = None,
    ) -> NormalizedResponse:
        client = self._get_client()

        # Build thinking/effort params for Anthropic SDK
        stream_kwargs: dict[str, Any] = {}
        if reasoning_effort not in ("auto", "none"):
            stream_kwargs["thinking"] = {"type": "adaptive"}
            stream_kwargs["output_config"] = {"output_type": "text", "effort": reasoning_effort}
        elif thinking_budget > 0:
            stream_kwargs["thinking"] = {"type": "enabled", "budget_tokens": max(1024, thinking_budget)}

        # Build two-block system param with cache_control on the stable prefix.
        # This lets Anthropic KV-cache the stable part across all turns.
        if hasattr(system, "stable") and hasattr(system, "dynamic"):
            system_param: Any = [
                {
                    "type": "text",
                    "text": system.stable,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": system.dynamic,
                },
            ]
        else:
            # Fallback: plain string (backwards compat / tests that set a str)
            system_param = system

        # Inject cache_control on a shallow copy of the last message so stored
        # history is not mutated (compaction must see clean messages).
        if messages:
            last_msg = messages[-1]
            last_content = last_msg["content"]
            # Convert string content to a block list so we can attach cache_control
            if isinstance(last_content, str):
                last_content_blocks = [
                    {"type": "text", "text": last_content, "cache_control": {"type": "ephemeral"}}
                ]
            else:
                # Content is already a list; copy all blocks as-is.
                # Anthropic format is already canonical — image blocks pass through.
                last_content_blocks = list(last_content)
                if last_content_blocks:
                    # Shallow-copy last block and attach cache_control at block level
                    # (never inside source — image blocks keep their source intact)
                    last_block = dict(last_content_blocks[-1])
                    last_block["cache_control"] = {"type": "ephemeral"}
                    last_content_blocks[-1] = last_block
            # Build a modified copy of the messages list — only the last message differs
            api_messages = messages[:-1] + [dict(last_msg, content=last_content_blocks)]
        else:
            api_messages = messages

        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            tools=tools,
            messages=api_messages,
            **stream_kwargs,
        ) as stream:
            thinking_content = ""
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block and getattr(event.content_block, "type", None) == "thinking":
                        thinking_content = getattr(event.content_block, "thinking", "") or ""
                        if stream_thinking:
                            await stream_thinking(thinking_content)
                elif event.type == "content_block_delta":
                    delta = event.delta
                    if getattr(delta, "type", None) == "thinking_delta":
                        thinking_content = getattr(delta, "thinking", "") or ""
                        if stream_thinking:
                            await stream_thinking(thinking_content)
                    elif getattr(delta, "type", None) == "text_delta":
                        text = getattr(delta, "text", "") or ""
                        if stream_text:
                            await stream_text(text)
                        else:
                            console.print(text, end="", highlight=False)
            if stream_text is None:
                console.print()
            final = await stream.get_final_message()

        usage = final.usage
        text_parts = [b.text for b in final.content if getattr(b, "type", None) == "text"]
        text_response = "".join(text_parts)

        tool_calls = []
        for block in final.content:
            if getattr(block, "type", None) == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        return NormalizedResponse(
            text=text_response,
            tool_calls=tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
            assistant_content_blocks=list(final.content),
        )


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (OpenRouter, etc.)
# ---------------------------------------------------------------------------

def _convert_messages_to_openai(
    system: str,
    messages: list[dict],
) -> list[dict]:
    """
    Convert Anthropic-format message history + a system string into OpenAI
    chat-completion message format.

    Anthropic format:
      - role "user" content may be a plain string OR a list of content blocks.
        Content blocks with type "tool_result" become role "tool" messages.
        Plain text blocks in user messages become role "user" messages.
      - role "assistant" content may be a plain string OR a list of content
        blocks.  Blocks with type "tool_use" surface as tool_calls on the
        OpenAI assistant message.  Text blocks become the assistant content.

    We emit:
      [{"role": "system", "content": system}, ...converted messages...]
    """
    result: list[dict] = [{"role": "system", "content": system}]

    # Coalesce consecutive same-role plain-string messages. aede sometimes
    # persists more than one row for a single logical turn (e.g. a multi-step
    # assistant turn split across rows, or two user messages sent in a row).
    # On resume these replay as adjacent same-role messages, which OpenAI-style
    # providers (DeepSeek via opencode-go) reject:
    #   "An assistant message ... must be followed by ..." / role-alternation
    #   errors surfacing as 400. Merge only plain strings — list-content
    #   messages carry tool_use/tool_result blocks whose ordering must be
    #   preserved and are handled block-by-block below.
    coalesced: list[dict] = []
    for msg in messages:
        if (
            coalesced
            and coalesced[-1]["role"] == msg["role"]
            and isinstance(coalesced[-1].get("content"), str)
            and isinstance(msg.get("content"), str)
        ):
            joined = (coalesced[-1]["content"] + "\n\n" + msg["content"]).strip()
            coalesced[-1] = {"role": msg["role"], "content": joined}
        else:
            coalesced.append(msg)
    messages = coalesced

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            # An assistant message with empty content and no tool_calls is
            # rejected by OpenAI-style providers (DeepSeek via opencode-go:
            # "content or tool_calls must be set"). This happens when a
            # tool-only assistant turn is replayed from history as a bare
            # string. Skip it — it carries no usable content.
            if role == "assistant" and not content.strip():
                continue
            result.append({"role": role, "content": content})
            continue

        # content is a list of blocks
        if role == "user":
            # May be a mix of tool_result blocks and text blocks.
            # Group consecutive non-tool-result blocks into user messages.
            pending_text_parts: list[str] = []

            def _flush_text() -> None:
                nonlocal pending_text_parts
                if pending_text_parts:
                    result.append({"role": "user", "content": "".join(pending_text_parts)})
                    pending_text_parts = []

            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type")
                else:
                    btype = getattr(block, "type", None)

                if btype == "tool_result":
                    _flush_text()
                    tool_use_id = block.get("tool_use_id") if isinstance(block, dict) else getattr(block, "tool_use_id", "")
                    tool_content = block.get("content") if isinstance(block, dict) else getattr(block, "content", "")
                    if isinstance(tool_content, list):
                        # content may itself be a list of text blocks
                        tool_content = "".join(
                            (b.get("text", "") if isinstance(b, dict) else getattr(b, "text", ""))
                            for b in tool_content
                        )
                    result.append({
                        "role": "tool",
                        "tool_call_id": tool_use_id,
                        "content": tool_content or "",
                    })
                elif btype == "text":
                    text = block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
                    pending_text_parts.append(text)
                elif btype == "image":
                    _flush_text()
                    source = block.get("source", {})
                    media_type = source.get("media_type", "image/png")
                    b64 = source.get("data", "")
                    result.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64}",
                                    "detail": "auto",
                                },
                            }
                        ],
                    })
                else:
                    # Unknown block type — convert to string
                    _flush_text()
                    result.append({"role": "user", "content": str(block)})

            _flush_text()

        elif role == "assistant":
            # May be a mix of text blocks and tool_use blocks.
            text_parts: list[str] = []
            tool_calls_oai: list[dict] = []

            for idx, block in enumerate(content):
                if isinstance(block, dict):
                    btype = block.get("type")
                else:
                    btype = getattr(block, "type", None)

                if btype == "text":
                    text = block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
                    text_parts.append(text)
                elif btype == "tool_use":
                    bid = block.get("id") if isinstance(block, dict) else getattr(block, "id", "")
                    bname = block.get("name") if isinstance(block, dict) else getattr(block, "name", "")
                    binput = block.get("input", {}) if isinstance(block, dict) else getattr(block, "input", {})
                    tool_calls_oai.append({
                        "id": bid,
                        "type": "function",
                        "function": {
                            "name": bname,
                            "arguments": json.dumps(binput),
                        },
                    })

            oai_msg: dict[str, Any] = {"role": "assistant"}
            joined_text = "".join(text_parts)
            oai_msg["content"] = joined_text or None
            if tool_calls_oai:
                oai_msg["tool_calls"] = tool_calls_oai
            # OpenAI-style providers (DeepSeek / MiMo via opencode-go, etc.)
            # reject an assistant message with neither content nor tool_calls
            # ("content or tool_calls must be set"). This happens for
            # reasoning-only turns — the model emits reasoning_content but no
            # text or tool calls, leaving an empty content-block list in
            # history. Emit empty-string content instead of null to keep the
            # message valid.
            if not tool_calls_oai and not joined_text:
                oai_msg["content"] = ""
            result.append(oai_msg)
        else:
            # Passthrough for any other role
            result.append({"role": role, "content": str(content)})

    return result


def _finalize_tool_call_id(provider_id: str | None, idx: int) -> str:
    """Guarantee a non-empty, index-stable tool-call id.

    OpenAI-style providers (e.g. DeepSeek) may stream tool_call deltas with no
    id; an empty id collides across calls and breaks React keys in the UI
    ("two children with the same key").  Fall back to a stable per-index id.
    """
    return provider_id or f"call_{idx}"


def _convert_tools_to_openai(tools: list[dict]) -> list[dict]:
    """
    Convert Anthropic tool schemas to OpenAI tool format.

    Anthropic: {"name": ..., "description": ..., "input_schema": {...}}
    OpenAI:    {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
    """
    result = []
    for tool in tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {}),
            },
        })
    return result


class OpenAIProvider:
    """
    Wraps AsyncOpenAI pointed at an OpenAI-compatible base URL (e.g. OpenRouter).
    Converts Anthropic message/tool format on the way out and normalizes the
    response on the way back.
    """

    def __init__(self, api_key: str, base_url: str, model_id: str = "") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None
        self.model_id = model_id

    def has_vision(self) -> bool:
        from aede.models import VISION_MODELS
        return self.model_id in VISION_MODELS

    def _get_client(self) -> Any:
        if self._client is None:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    @property
    def raw_client(self) -> Any:
        return self._get_client()

    async def stream_turn(
        self,
        *,
        model: str,
        system: Any,
        tools: list[dict],
        messages: list[dict],
        max_tokens: int,
        console: Any,
        reasoning_effort: str = "auto",
        thinking_budget: int = 0,
        stream_text: Any = None,
        stream_thinking: Any = None,
    ) -> NormalizedResponse:
        client = self._get_client()

        # Build provider-aware reasoning/thinking params
        stream_kwargs: dict[str, Any] = {}
        is_deepseek_inner = model.startswith("deepseek-")
        is_gemini = self._base_url and "googleapis.com" in self._base_url

        # thinking_budget > 0 implies user wants reasoning enabled even when
        # reasoning_effort is "auto" — derive a sensible default.
        effective_effort = reasoning_effort
        if reasoning_effort == "auto" and thinking_budget > 0:
            effective_effort = "high"

        if effective_effort != "auto":
            if is_deepseek_inner:
                # DeepSeek only accepts "high" and "max"
                deepseek_map: dict[str, str] = {
                    "low": "high", "medium": "high", "high": "high",
                    "xhigh": "max", "max": "max",
                }
                if effective_effort == "none":
                    stream_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                else:
                    mapped = deepseek_map.get(effective_effort, "high")
                    stream_kwargs["reasoning_effort"] = mapped
                    stream_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            elif is_gemini:
                # Gemini via Google AI OpenAI-compatible endpoint
                level_map: dict[str, str] = {
                    "none": "minimal", "low": "low", "medium": "medium",
                    "high": "high", "xhigh": "high", "max": "high",
                }
                level = level_map.get(effective_effort, "medium")
                stream_kwargs["extra_body"] = {"thinking_config": {"thinking_level": level}}
            else:
                # OpenAI / OpenRouter — pass through
                stream_kwargs["reasoning_effort"] = effective_effort

        # Flatten SystemPrompt to a plain string — OpenAI does not support cache_control.
        if hasattr(system, "stable") and hasattr(system, "dynamic"):
            system_str = system.stable + system.dynamic
        else:
            system_str = system
        oai_messages = _convert_messages_to_openai(system_str, messages)
        oai_tools = _convert_tools_to_openai(tools)

        # Accumulate streamed response
        full_text_parts: list[str] = []
        # tool_calls_acc: dict[index -> {"id","name","arguments_parts":[...]}]
        tool_calls_acc: dict[int, dict] = {}
        usage_data: dict[str, Any] = {}

        stream = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=oai_messages,
            tools=oai_tools if oai_tools else None,
            stream=True,
            stream_options={"include_usage": True},
            **stream_kwargs,
        )

        async for chunk in stream:
            # Accumulate usage if present
            if hasattr(chunk, "usage") and chunk.usage is not None:
                usage_data = chunk.usage

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content and stream_thinking:
                await stream_thinking(str(delta.reasoning_content))
            elif hasattr(delta, 'reasoning') and delta.reasoning and stream_thinking:
                await stream_thinking(str(delta.reasoning))

            if delta.content:
                full_text_parts.append(delta.content)
                if stream_text is not None:
                    await stream_text(delta.content)
                else:
                    console.print(delta.content, end="", highlight=False)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": "",
                            "name": "",
                            "arguments_parts": [],
                        }
                    if tc_delta.id:
                        tool_calls_acc[idx]["id"] = tc_delta.id
                    if tc_delta.function and tc_delta.function.name:
                        tool_calls_acc[idx]["name"] = tc_delta.function.name
                    if tc_delta.function and tc_delta.function.arguments:
                        tool_calls_acc[idx]["arguments_parts"].append(tc_delta.function.arguments)

        if stream_text is None:
            console.print()

        text_response = "".join(full_text_parts)

        # Finalize tool calls
        tool_calls: list[dict] = []
        assistant_tool_use_blocks: list[dict] = []
        for idx in sorted(tool_calls_acc.keys()):
            tc = tool_calls_acc[idx]
            call_id = _finalize_tool_call_id(tc["id"], idx)
            raw_args = "".join(tc["arguments_parts"])
            try:
                parsed_input = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                parsed_input = {"_raw": raw_args}
            tool_calls.append({
                "id": call_id,
                "name": tc["name"],
                "input": parsed_input,
            })
            # Synthesize Anthropic-format tool_use block (as dict) for message history
            assistant_tool_use_blocks.append({
                "type": "tool_use",
                "id": call_id,
                "name": tc["name"],
                "input": parsed_input,
            })

        # Build Anthropic-format assistant content blocks for history
        anthropic_content_blocks: list[Any] = []
        if text_response:
            anthropic_content_blocks.append({"type": "text", "text": text_response})
        anthropic_content_blocks.extend(assistant_tool_use_blocks)

        # Map usage
        if usage_data:
            input_tokens = getattr(usage_data, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage_data, "completion_tokens", 0) or 0
            cached_tokens = 0
            pt_details = getattr(usage_data, "prompt_tokens_details", None)
            if pt_details is not None:
                cached_tokens = getattr(pt_details, "cached_tokens", 0) or 0
        else:
            input_tokens = 0
            output_tokens = 0
            cached_tokens = 0

        return NormalizedResponse(
            text=text_response,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            assistant_content_blocks=anthropic_content_blocks,
        )


# ---------------------------------------------------------------------------
# ACP provider (routes to local/remote ACP agents)
# ---------------------------------------------------------------------------

# Models that should be routed through ACP rather than LLM API
ACP_MODEL_IDS: frozenset[str] = frozenset({
    "codex", "claude-code", "gemini",
    "cline", "cursor", "goose",
    # Sub-model entries
    "codex/gpt-5.5", "codex/gpt-5.3-codex", "codex/o3", "codex/o4-mini",
    "claude-code/fable-5", "claude-code/opus-4-8",
    # "claude-code/opus-4-7",
    "claude-code/sonnet-4-6", "claude-code/haiku-4-5",

    "goose/anthropic-claude-sonnet-4-6", "goose/openai-gpt-4o",
})

# Models that route through OpenCode Zen (free + paid, OpenAI-compatible)
# All use /v1/chat/completions via OpenAIProvider.
ZEN_MODEL_IDS: frozenset[str] = frozenset({
    # Free models
    "deepseek-v4-flash-free", "nemotron-3-ultra-free", "big-pickle",
    "mimo-v2.5-free", "north-mini-code-free",
    # Paid chat-completions models (exclusive to Zen — no Go overlap)
    "grok-build-0.1", "kimi-k2.5",
})

# Go models using OpenAI-compatible /v1/chat/completions endpoint
GO_OPENAI_MODEL_IDS: frozenset[str] = frozenset({
    "deepseek-v4-pro", "deepseek-v4-flash", "glm-5.1", "glm-5",
    "kimi-k2.7", "kimi-k2.6", "mimo-v2.5", "mimo-v2.5-pro",
})

# Go models using Anthropic-compatible /v1/messages endpoint
GO_ANTHROPIC_MODEL_IDS: frozenset[str] = frozenset({
    "minimax-m3", "minimax-m2.7", "minimax-m2.5",
    "qwen3.7-max", "qwen3.7-plus", "qwen3.6-plus",
})


class AcpProvider:
    """Routes chat turns through ACP subprocess agents.

    Handles auto-connect, model-switch disconnect/reconnect, and
    cloud auth (OAuth) for future remote ACP agents.
    """

    def __init__(
        self,
        model: str,
        acp_manager: Any,
        credential_provider: Any = None,
        stream_text: Any = None,
    ) -> None:
        self._model = model
        self.model_id = model
        self._acp_manager = acp_manager
        self._credential_provider = credential_provider
        self._current_agent: str | None = None
        self._stream_text = stream_text
        self._stream_thinking = None
        # Optional callbacks for surfacing the ACP agent's own tool calls to the UI.
        # Set by AgentLoop after construction (mirrors _stream_text wiring).
        self._stream_tool_call = None
        self._stream_tool_result = None

    def has_vision(self) -> bool:
        return True

    async def stream_turn(
        self,
        *,
        model: str,
        system: Any,
        tools: list[dict],
        messages: list[dict],
        max_tokens: int,
        console: Any,
        reasoning_effort: str = "auto",
        thinking_budget: int = 0,
        stream_text: Any = None,
        stream_thinking: Any = None,
    ) -> NormalizedResponse:
        if stream_text is not None:
            self._stream_text = stream_text
        if stream_thinking is not None:
            self._stream_thinking = stream_thinking
        manager = self._acp_manager

        # Resolve base agent and optional sub-model override.
        # e.g. "claude-code/opus-4-8" -> base="claude-code", override="claude-opus-4-8"
        if "/" in model:
            base_agent = model.split("/", 1)[0]
            from aede.commands import get_acp_model_override
            model_override = get_acp_model_override(model)
        else:
            base_agent = model
            model_override = None

        agent = base_agent
        prev_agent = self._current_agent

        async def _ensure_connected() -> Any:
            if model_override is not None:
                try:
                    config = manager._registry.get(base_agent)
                    if config.model_override != model_override:
                        if base_agent in manager.list_connected():
                            await manager.disconnect(base_agent)
                        config.model_override = model_override
                        manager._registry.upsert(config)
                except KeyError:
                    pass

            if thinking_budget > 0:
                try:
                    config = manager._registry.get(base_agent)
                    if config.thinking_budget != thinking_budget:
                        config.thinking_budget = thinking_budget
                        manager._registry.upsert(config)
                        _meta = {
                            "claudeCode": {
                                "options": {
                                    "thinking": {"budget_tokens": thinking_budget},
                                },
                            },
                        }
                        if agent in manager.list_connected():
                            await manager.new_session(agent, _meta=_meta)
                            return manager.active_session()
                except KeyError:
                    pass

            if prev_agent and prev_agent != agent:
                await manager.disconnect(prev_agent)

            if agent not in manager.list_connected():
                await manager.connect(agent)
            else:
                manager.switch_to(agent)

            return manager.active_session()

        session_wrapper = await _ensure_connected()
        self._current_agent = agent

        if session_wrapper is None:
            raise RuntimeError(f"ACP session for '{agent}' is not active")

        prompt_text = _build_prompt_text(messages)

        result = await session_wrapper.session.prompt(prompt_text, on_update=self._make_on_update())

        if result.text and not self._stream_text:
            console.print(result.text, highlight=False)

        # Build assistant content blocks for history
        anthropic_content_blocks: list[Any] = []
        if result.text:
            anthropic_content_blocks.append({"type": "text", "text": result.text})

        return NormalizedResponse(
            text=result.text,
            tool_calls=[],
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
            assistant_content_blocks=anthropic_content_blocks,
        )

    def _make_on_update(self):
        stream_text = self._stream_text
        stream_thinking = self._stream_thinking
        stream_tool_call = self._stream_tool_call
        stream_tool_result = self._stream_tool_result
        if not (stream_text or stream_thinking or stream_tool_call or stream_tool_result):
            return None

        # Cache populated args from middle tool_call_update so the terminal
        # update can re-emit a tool_call with _start_line injected.
        _pending_args: dict[str, dict] = {}
        # seq_counter tracks execution order across thinking chunks and tool calls
        # so the UI can reconstruct the interleaved timeline.  Thinking chunks
        # within the SAME block (consecutive agent_thought_chunk events) share a
        # seq; a new tool_call bumps the counter, and the next thinking block gets
        # a higher seq.  We use a mutable list as a nonlocal-friendly counter.
        _seq = [0]
        _current_thinking_seq: list[int | None] = [None]

        def on_update(update: dict):
            update_type = update.get("sessionUpdate")
            content = update.get("content", {})
            if update_type == "agent_thought_chunk":
                text = content.get("text", "") if isinstance(content, dict) else ""
                if text and stream_thinking:
                    # All chunks of a continuous thinking run share one seq value;
                    # a new thinking run (after a tool call) gets a fresh seq.
                    if _current_thinking_seq[0] is None:
                        _current_thinking_seq[0] = _seq[0]
                        _seq[0] += 1
                    asyncio.ensure_future(stream_thinking(text, _current_thinking_seq[0]))
            elif update_type == "agent_message_chunk":
                if isinstance(content, dict) and content.get("type") == "text":
                    text = content.get("text", "")
                    if text and stream_text:
                        asyncio.ensure_future(stream_text(text))
            elif update_type == "tool_call" and stream_tool_call:
                # Start-of-tool-call. rawInput is usually {} here; the populated
                # args arrive in a later tool_call_update for the same id.
                # A new tool call ends any current thinking run — reset seq slot.
                _current_thinking_seq[0] = None
                call_id = update.get("toolCallId", "") or f"acp_{_seq[0]}"
                name = _acp_tool_name(update)
                args = update.get("rawInput") or {}
                tc_seq = _seq[0]
                _seq[0] += 1
                asyncio.ensure_future(stream_tool_call(call_id, name, args, tc_seq))
            elif update_type == "tool_call_update":
                call_id = update.get("toolCallId", "")
                # Middle update: carry real args (old_string/new_string/file_path).
                raw_input = update.get("rawInput")
                if raw_input and stream_tool_call:
                    name = _acp_tool_name(update)
                    args = dict(raw_input)
                    _pending_args[call_id] = args
                    asyncio.ensure_future(stream_tool_call(call_id, name, args))
                # Terminal update: emit result + re-emit args with real line numbers
                # from structuredPatch (only available here, not in middle update).
                status = update.get("status", "")
                if status in ("completed", "failed") and stream_tool_result:
                    if stream_tool_call and call_id in _pending_args:
                        start_line = _acp_edit_start_line(update)
                        if start_line:
                            cached = dict(_pending_args[call_id])
                            cached["_start_line"] = start_line
                            asyncio.ensure_future(
                                stream_tool_call(call_id, _acp_tool_name(update), cached)
                            )
                        del _pending_args[call_id]
                    out = _acp_tool_content_to_text(update.get("content")) \
                        or update.get("rawOutput", "")
                    ui_status = "success" if status == "completed" else "error"
                    asyncio.ensure_future(stream_tool_result(call_id, ui_status, out, 0))
        return on_update


def _acp_tool_name(update: dict) -> str:
    """Resolve a display tool name from an ACP tool_call update.

    Prefers the concrete tool name in ``_meta.claudeCode.toolName`` (e.g.
    "Edit", "Read") so the UI can match its diff renderer; falls back to the
    human title or ACP ``kind``.
    """
    meta = update.get("_meta") or {}
    cc = meta.get("claudeCode") or {}
    return cc.get("toolName") or update.get("kind") or "tool"


def _acp_tool_content_to_text(content: Any) -> str:
    """Flatten an ACP tool_call_update ``content`` field into plain text.

    ACP sends content as a list of blocks (often ``{"type": "content",
    "content": {"type": "text", "text": ...}}``).  Returns "" when nothing
    textual is present.
    """
    if not content:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    items = content if isinstance(content, list) else [content]
    for item in items:
        if not isinstance(item, dict):
            continue
        inner = item.get("content", item)
        if isinstance(inner, dict) and inner.get("type") == "text":
            parts.append(inner.get("text", ""))
        elif item.get("type") == "text":
            parts.append(item.get("text", ""))
    return "\n".join(p for p in parts if p)


def _acp_edit_start_line(update: dict) -> int | None:
    """Extract the edit starting line number from an ACP ``tool_call_update``.

    Prefers ``_meta.claudeCode.toolResponse.structuredPatch[0].newStart``
    (available on the terminal update which has status=completed) over
    ``locations[0].line`` (available on the middle update for Read but
    not for Edit).
    """
    meta = update.get("_meta") or {}
    cc = meta.get("claudeCode") or {}
    tool_response = cc.get("toolResponse") or {}
    patches = tool_response.get("structuredPatch") or []
    if patches and isinstance(patches, list):
        start = patches[0].get("newStart")
        if isinstance(start, int):
            return start
    locs = update.get("locations") or []
    if locs and isinstance(locs, list) and isinstance(locs[0], dict):
        line = locs[0].get("line")
        if isinstance(line, int):
            return line
    return None


def _build_prompt_text(messages: list[dict]) -> str:
    """Convert Anthropic-format message history to a single prompt string for ACP.

    For multi-turn conversations, we reconstruct the conversation as a text
    prompt that the ACP agent can process.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(f"[{role}]: {content}")
        elif isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        text_parts.append(f"[tool result]: {block.get('content', '')}")
                    elif block.get("type") == "image":
                        text_parts.append("[Image attached]")
            if text_parts:
                parts.append(f"[{role}]: {' '.join(text_parts)}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_provider(cfg: Any, acp_manager: Any = None) -> AnthropicProvider | OpenAIProvider | AcpProvider:
    """
    Select and return the appropriate provider based on config.

    Rules:
    - If model is in ACP_MODEL_IDS → AcpProvider (requires acp_manager).
    - If cfg.api_base_url is set AND the model is NOT an Anthropic model
      (does not start with "claude-" and does not start with "anthropic/")
      → OpenAIProvider using OPENROUTER_API_KEY (fallback OPENAI_API_KEY).
    - Otherwise → AnthropicProvider using ANTHROPIC_API_KEY.
    """
    import os

    base_url: str | None = getattr(cfg, "api_base_url", None)
    model: str = getattr(cfg, "model", "")

    # ACP routing — intercept before other provider logic
    if model in ACP_MODEL_IDS:
        if acp_manager is None:
            raise RuntimeError(
                f"Model '{model}' requires ACP routing but no acp_manager was provided."
            )
        return AcpProvider(
            model=model,
            acp_manager=acp_manager,
        )

    # OpenCode Zen/Go routing — static model set matching
    # cfg.providers overrides api_key_env and base_url per provider name.
    if model in ZEN_MODEL_IDS:
        providers: dict = getattr(cfg, "providers", {})
        zen_cfg: dict = providers.get("opencode-zen", {}) if providers else {}
        env_key: str = zen_cfg.get("api_key_env", "OPENCODE_ZEN_API_KEY")
        base: str = zen_cfg.get("base_url", "https://opencode.ai/zen/v1")
        api_key: str | None = os.environ.get(env_key)
        if not api_key:
            raise RuntimeError(
                f"{env_key} is not set. Use /setkey {env_key} <key> first."
            )
        return OpenAIProvider(api_key=api_key, base_url=base, model_id=model)

    if model in GO_OPENAI_MODEL_IDS:
        providers = getattr(cfg, "providers", {})
        go_cfg: dict = providers.get("opencode-go", {}) if providers else {}
        env_key = go_cfg.get("api_key_env", "OPENCODE_GO_API_KEY")
        base = go_cfg.get("base_url", "https://opencode.ai/zen/go/v1")
        api_key = os.environ.get(env_key)
        if not api_key:
            raise RuntimeError(
                f"{env_key} is not set. Use /setkey {env_key} <key> first."
            )
        return OpenAIProvider(api_key=api_key, base_url=base, model_id=model)

    if model in GO_ANTHROPIC_MODEL_IDS:
        providers = getattr(cfg, "providers", {})
        go_cfg: dict = providers.get("opencode-go", {}) if providers else {}
        env_key = go_cfg.get("api_key_env", "OPENCODE_GO_API_KEY")
        base = go_cfg.get("base_url", "https://opencode.ai/zen/go/v1")
        # Anthropic SDK appends /v1/messages automatically, so strip trailing /v1
        if base.endswith("/v1"):
            base = base[:-3]
        api_key = os.environ.get(env_key)
        if not api_key:
            raise RuntimeError(
                f"{env_key} is not set. Use /setkey {env_key} <key> first."
            )
        return AnthropicProvider(api_key=api_key, base_url=base, model_id=model)

    is_anthropic_model = (
        model.startswith("claude-") or model.startswith("anthropic/")
    )
    is_deepseek_model = model.startswith("deepseek-")

    if is_deepseek_model:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Use /setkey DEEPSEEK_API_KEY <key> first."
            )
        return OpenAIProvider(api_key=api_key, base_url=base_url or "https://api.deepseek.com", model_id=model)

    if base_url and not is_anthropic_model:
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenRouter/OpenAI-compatible provider requires OPENROUTER_API_KEY "
                "(or OPENAI_API_KEY) to be set. Use /setkey OPENROUTER_API_KEY <key> first."
            )
        return OpenAIProvider(api_key=api_key, base_url=base_url, model_id=model)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Use /setkey ANTHROPIC_API_KEY <key> first."
            )
        return AnthropicProvider(api_key=api_key, model_id=model)
