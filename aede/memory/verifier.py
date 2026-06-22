"""
Verifier — Phase D+E verdict functions for agent learnings.

Two independent paths:
- ``run_code_verify``: runs the test suite (injectable runner) and returns a
  pass/fail verdict.
- ``run_llm_verify``: issues a separate LLM coherence-check turn and returns
  a coherence verdict.  Non-code learnings are ALWAYS lower_trust (Q5).

Both methods are pure verdict functions: they accept a learning dict and
return an *update* dict of fields to apply.  They do NOT write to any store —
store integration is deferred to T-11x.

Heavy imports (``anthropic``) are lazy — imported inside the method that
needs them, not at module level.
"""
from __future__ import annotations

import subprocess
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Default test runner
# ---------------------------------------------------------------------------

def _default_test_runner() -> bool:
    """Run ``uv run pytest`` via subprocess.

    Returns True if the test suite passes (returncode 0), False otherwise.
    """
    result = subprocess.run(
        ["uv", "run", "pytest"],
        capture_output=True,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

_COHERENT_VERDICT = "llm_coherence_pass"
_INCOHERENT_VERDICT = "llm_coherence_fail"

_COHERENCE_SYSTEM_PROMPT = (
    "You are a strict knowledge-base verifier.  Your only job is to assess "
    "whether the provided learning is internally coherent, factually plausible, "
    "and non-contradictory.  Reply with exactly one word on the first line: "
    "'COHERENT' if the learning passes, 'INCOHERENT' if it does not.  "
    "Follow with a one-sentence explanation."
)


class Verifier:
    """Verdict-only verifier for agent learnings.

    Args:
        test_runner: Callable ``() -> bool`` used by ``run_code_verify``.
            Defaults to a function that runs ``uv run pytest`` via subprocess.
        llm_client: Synchronous Anthropic-like client used by
            ``run_llm_verify``.  Must expose ``client.messages.create(...)``
            and return an object whose ``.content[0].text`` is a string.
            Defaults to ``None``; when ``None`` and ``run_llm_verify`` is
            called, a real ``anthropic.Anthropic`` client is constructed
            lazily (requires ``ANTHROPIC_API_KEY``).
    """

    def __init__(
        self,
        *,
        test_runner: Callable[[], bool] | None = None,
        llm_client: Any | None = None,
    ) -> None:
        self._test_runner: Callable[[], bool] = test_runner or _default_test_runner
        self._llm_client: Any | None = llm_client

    # ------------------------------------------------------------------
    # T-09x — code path
    # ------------------------------------------------------------------

    def run_code_verify(self, learning: dict) -> dict:
        """Run the test suite and return a verdict update dict.

        Args:
            learning: The learning record dict (not mutated).

        Returns:
            A dict with fields to merge back into the learning::

                {"verifier_outcome": "pass" | "fail", "trusted": bool}
        """
        passed = self._test_runner()
        if passed:
            return {"verifier_outcome": "pass", "trusted": True}
        return {"verifier_outcome": "fail", "trusted": False}

    # ------------------------------------------------------------------
    # T-10x — LLM coherence path
    # ------------------------------------------------------------------

    def run_llm_verify(self, learning: dict) -> dict:
        """Issue a separate LLM turn to check coherence of a non-code learning.

        Non-code learnings are ALWAYS ``lower_trust=True`` (locked decision Q5).

        Args:
            learning: The learning record dict (not mutated).

        Returns:
            A dict with fields to merge back into the learning::

                {
                    "verifier_outcome": "llm_coherence_pass" | "llm_coherence_fail",
                    "trusted": bool,
                    "lower_trust": True,  # always True for non-code path
                }
        """
        client = self._get_llm_client()
        content_text = learning.get("content", "")

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system=_COHERENCE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Assess the following learning for coherence:\n\n{content_text}"
                    ),
                }
            ],
        )

        reply_text: str = response.content[0].text if response.content else ""
        first_word = (
            reply_text.strip().split()[0].upper().rstrip(":.,!?")
            if reply_text.strip()
            else ""
        )

        coherent = first_word == "COHERENT"

        return {
            "verifier_outcome": _COHERENT_VERDICT if coherent else _INCOHERENT_VERDICT,
            "trusted": coherent,
            "lower_trust": True,  # locked decision Q5 — always lower_trust for non-code
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_llm_client(self) -> Any:
        """Return the injected client or construct a real one lazily."""
        if self._llm_client is not None:
            return self._llm_client
        # Lazy import — only reached in production (no API key needed in tests)
        import anthropic
        return anthropic.Anthropic()
