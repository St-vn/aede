"""
Provider abstraction for aede agent.

Supports Anthropic (native SDK) and OpenAI-compatible endpoints (e.g. OpenRouter).
Heavy imports (anthropic, openai) are lazy — loaded inside methods, not at module level.
"""
from __future__ import annotations

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
    ) -> NormalizedResponse:
        ...


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class AnthropicProvider:
    """Wraps AsyncAnthropic and streams a turn, returning a NormalizedResponse."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
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
                # Content is already a list; shallow-copy and inject on last block
                last_content_blocks = list(last_content)
                if last_content_blocks:
                    last_block = dict(last_content_blocks[-1])
                    last_block["cache_control"] = {"type": "ephemeral"}
                    last_content_blocks = last_content_blocks[:-1] + [last_block]
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
            async for text in stream.text_stream:
                console.print(text, end="", highlight=False)
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

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
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
            oai_msg["content"] = "".join(text_parts) or None
            if tool_calls_oai:
                oai_msg["tool_calls"] = tool_calls_oai
            result.append(oai_msg)
        else:
            # Passthrough for any other role
            result.append({"role": role, "content": str(content)})

    return result


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

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None

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
    ) -> NormalizedResponse:
        client = self._get_client()

        # Build provider-aware reasoning/thinking params
        stream_kwargs: dict[str, Any] = {}
        is_deepseek_inner = model.startswith("deepseek-")
        is_gemini = self._base_url and "googleapis.com" in self._base_url

        if reasoning_effort != "auto":
            if is_deepseek_inner:
                # DeepSeek only accepts "high" and "max"
                deepseek_map: dict[str, str] = {
                    "low": "high", "medium": "high", "high": "high",
                    "xhigh": "max", "max": "max",
                }
                if reasoning_effort == "none":
                    stream_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
                else:
                    mapped = deepseek_map.get(reasoning_effort, "high")
                    stream_kwargs["reasoning_effort"] = mapped
                    stream_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            elif is_gemini:
                # Gemini via Google AI OpenAI-compatible endpoint
                level_map: dict[str, str] = {
                    "none": "minimal", "low": "low", "medium": "medium",
                    "high": "high", "xhigh": "high", "max": "high",
                }
                level = level_map.get(reasoning_effort, "medium")
                stream_kwargs["extra_body"] = {"thinking_config": {"thinking_level": level}}
            else:
                # OpenAI / OpenRouter — pass through
                stream_kwargs["reasoning_effort"] = reasoning_effort

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

            if delta.content:
                full_text_parts.append(delta.content)
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

        console.print()

        text_response = "".join(full_text_parts)

        # Finalize tool calls
        tool_calls: list[dict] = []
        assistant_tool_use_blocks: list[dict] = []
        for idx in sorted(tool_calls_acc.keys()):
            tc = tool_calls_acc[idx]
            raw_args = "".join(tc["arguments_parts"])
            try:
                parsed_input = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                parsed_input = {"_raw": raw_args}
            tool_calls.append({
                "id": tc["id"],
                "name": tc["name"],
                "input": parsed_input,
            })
            # Synthesize Anthropic-format tool_use block (as dict) for message history
            assistant_tool_use_blocks.append({
                "type": "tool_use",
                "id": tc["id"],
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
    "codex", "claude-code", "gemini", "agy",
    "cline", "cursor", "goose", "opencode",
    # Sub-model entries
    "codex/gpt-5.5", "codex/gpt-5.3-codex", "codex/o3", "codex/o4-mini",
    "claude-code/fable-5", "claude-code/opus-4-8", "claude-code/opus-4-7", "claude-code/sonnet-4-6", "claude-code/haiku-4-5",
    "agy/gemini-3-5-flash", "agy/claude-sonnet-4-6", "agy/claude-opus-4-6",
    "goose/anthropic-claude-sonnet-4-6", "goose/openai-gpt-4o",
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
    ) -> None:
        self._model = model
        self._acp_manager = acp_manager
        self._credential_provider = credential_provider
        self._current_agent: str | None = None

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
    ) -> NormalizedResponse:
        agent = model
        manager = self._acp_manager

        # Disconnect previous agent if model changed
        if self._current_agent and self._current_agent != agent:
            manager.disconnect(self._current_agent)

        # Auto-connect if not already connected
        if agent not in manager.list_connected():
            manager.connect(agent)
        else:
            manager.switch_to(agent)
        self._current_agent = agent

        # Get active session
        session_wrapper = manager.active_session()
        if session_wrapper is None:
            raise RuntimeError(f"ACP session for '{agent}' is not active")

        # Build prompt text from messages
        prompt_text = _build_prompt_text(messages)

        # Run prompt synchronously (blocking — streaming TBD)
        import asyncio
        result = await asyncio.to_thread(
            session_wrapper.session.prompt,
            prompt_text,
        )

        # Print response to console
        if result.text:
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
        return OpenAIProvider(api_key=api_key, base_url=base_url or "https://api.deepseek.com")

    if base_url and not is_anthropic_model:
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenRouter/OpenAI-compatible provider requires OPENROUTER_API_KEY "
                "(or OPENAI_API_KEY) to be set. Use /setkey OPENROUTER_API_KEY <key> first."
            )
        return OpenAIProvider(api_key=api_key, base_url=base_url)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Use /setkey ANTHROPIC_API_KEY <key> first."
            )
        return AnthropicProvider(api_key=api_key)
