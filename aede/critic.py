"""
Asymmetric critic for aede — Phase 2 Basic Correctness.

A separate LLM invocation with a "ruthless code critic" persona that reviews
proposed code before the approval gate.  The critic is advisory only: findings
are shown to the user, who then decides at the existing prompt_gate.

All heavy imports (anthropic/openai SDK via provider) are lazy — inside functions.
"""
from __future__ import annotations

import json
import types
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


CRITIC_SYSTEM_PROMPT = """\
You are a ruthless, expert code reviewer. Your ONLY job is to identify correctness
bugs, logic errors, and spec violations in the code you are given. You do NOT comment
on style, formatting, whitespace, naming conventions, or anything that does not affect
the runtime behaviour of the code.

For each issue you find, output a JSON array of objects with exactly two keys:
  "severity": one of "HIGH", "MEDIUM", or "LOW"
  "message":  a concise description of the problem

Rules:
- HIGH: crashes, data loss, wrong output, broken contracts, security holes.
- MEDIUM: logic bugs that produce wrong results in some cases.
- LOW: edge cases, potential issues that may not matter in practice.
- If there are NO correctness issues, return exactly: []
- Return ONLY the JSON array on a single line, then optionally prose after a blank line.
  The parser will read only the first JSON array it finds.
- Never report style, formatting, docstrings, or whitespace as issues.
"""


@dataclass
class CriticFinding:
    """A single finding from the critic LLM."""
    severity: str   # "HIGH" | "MEDIUM" | "LOW"
    message: str


def get_critic_provider(cfg: Any) -> Any:
    """Return a provider for the critic, building from critic_model / critic_api_base_url.

    Same-model fallback: when critic_model is absent (None), constructs a shim
    config that mirrors cfg.model and cfg.api_base_url so get_provider returns
    the exact same provider type as the main agent — different system prompt is
    the only distinction.
    """
    from aede.provider import get_provider

    critic_model: str | None = getattr(cfg, "critic_model", None) or None
    critic_api_base_url: str | None = getattr(cfg, "critic_api_base_url", None) or None

    # Build a lightweight shim that get_provider can read.
    shim = types.SimpleNamespace(
        model=critic_model if critic_model else cfg.model,
        api_base_url=critic_api_base_url if critic_api_base_url else getattr(cfg, "api_base_url", None),
    )
    return get_provider(shim)


async def evaluate(
    cfg: Any,
    code: str,
    task_context: str,
    tracker: Any = None,
    turn: int = 0,
) -> list[CriticFinding]:
    """Call the critic LLM with the proposed code and return a list of findings.

    The critic is invoked with CRITIC_SYSTEM_PROMPT plus a user message containing
    the code and task context.  It returns a JSON array; this function parses that
    array into CriticFinding instances.

    When ``tracker`` is provided the critic's token usage is recorded with
    ``role="critic"`` so ``/tokens`` accounts for the separate critic invocation.

    On any parse error or exception the function returns an empty list rather than
    crashing — callers rely on non-fatal behaviour.
    """
    provider = get_critic_provider(cfg)
    model = getattr(cfg, "critic_model", None) or cfg.model

    user_message = (
        f"Task context: {task_context}\n\n"
        f"Proposed code:\n```\n{code}\n```\n\n"
        "Review the code above for correctness bugs only. "
        "Return a JSON array of findings as instructed."
    )

    # Use stream_turn with no tools — critic is read-only.
    # We need a minimal SystemPrompt-like object that providers handle.
    class _CriticPrompt:
        stable: str = CRITIC_SYSTEM_PROMPT
        dynamic: str = ""

    try:
        resp = await provider.stream_turn(
            model=model,
            system=_CriticPrompt(),
            tools=[],
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1024,
            console=_NullConsole(),
        )
        if tracker is not None:
            tracker.record(
                turn=turn,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cached_tokens=resp.cached_tokens,
                role="critic",
            )
        return _parse_findings(resp.text)
    except Exception:
        return []


def _parse_findings(text: str) -> list[CriticFinding]:
    """Extract the first JSON array from the response text and map to CriticFinding objects."""
    text = text.strip()
    # Find the first '[' and attempt to parse a JSON array from there.
    bracket = text.find("[")
    if bracket == -1:
        return []
    try:
        # Try to find a matching ']' by attempting json.loads progressively.
        # Simple approach: extract everything from '[' to last ']'.
        close = text.rfind("]")
        if close == -1:
            return []
        raw = text[bracket:close + 1]
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        findings = []
        for item in data:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity", "LOW")).upper()
            if severity not in ("HIGH", "MEDIUM", "LOW"):
                severity = "LOW"
            message = str(item.get("message", ""))
            findings.append(CriticFinding(severity=severity, message=message))
        return findings
    except (json.JSONDecodeError, ValueError):
        return []


class _NullConsole:
    """Minimal console shim that swallows all output from the critic streaming."""

    def print(self, *args: Any, **kwargs: Any) -> None:  # noqa: A003
        pass
