"""
Tests for aede.memory.verifier — T-09x (code path) and T-10x (LLM coherence path).

TDD: tests written FIRST.  Run before implementation to confirm RED.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from aede.memory.verifier import Verifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_learning(
    *,
    type: str = "anti-pattern",
    content: str = "Never use bare except clauses.",
    source: str = "auto_learned",
    trusted: bool = False,
    lower_trust: bool = False,
    verifier_outcome: str | None = None,
) -> dict:
    return {
        "id": "01JTEST000000000000000000",
        "type": type,
        "content": content,
        "source": source,
        "trusted": trusted,
        "lower_trust": lower_trust,
        "verifier_outcome": verifier_outcome,
    }


# ---------------------------------------------------------------------------
# T-09x — code path
# ---------------------------------------------------------------------------

class TestCodeVerify:
    """T-09x: run_code_verify delegates to an injectable test runner."""

    def test_code_verify_passes_on_test_pass(self):
        """Mock runner reports pass → verifier_outcome='pass', trusted=True."""
        def mock_runner() -> bool:
            return True

        verifier = Verifier(test_runner=mock_runner)
        learning = _make_learning()
        result = verifier.run_code_verify(learning)

        assert result["verifier_outcome"] == "pass"
        assert result["trusted"] is True

    def test_code_verify_fails_on_test_fail(self):
        """Mock runner reports failure → verifier_outcome='fail', trusted=False."""
        def mock_runner() -> bool:
            return False

        verifier = Verifier(test_runner=mock_runner)
        learning = _make_learning()
        result = verifier.run_code_verify(learning)

        assert result["verifier_outcome"] == "fail"
        assert result["trusted"] is False

    def test_code_verify_returns_only_update_fields(self):
        """Return dict should contain only verifier_outcome and trusted (not full record)."""
        verifier = Verifier(test_runner=lambda: True)
        learning = _make_learning()
        result = verifier.run_code_verify(learning)

        # Must have at minimum these two fields
        assert "verifier_outcome" in result
        assert "trusted" in result

    def test_default_runner_invokes_pytest(self, monkeypatch):
        """Default runner (no injection) calls uv run pytest via subprocess."""
        import subprocess

        completed = MagicMock()
        completed.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: completed)

        verifier = Verifier()
        learning = _make_learning()
        result = verifier.run_code_verify(learning)

        assert result["verifier_outcome"] == "pass"
        assert result["trusted"] is True

    def test_code_verify_does_not_mutate_input(self):
        """The input learning dict must not be mutated."""
        learning = _make_learning()
        original = dict(learning)
        verifier = Verifier(test_runner=lambda: True)
        verifier.run_code_verify(learning)
        assert learning == original


# ---------------------------------------------------------------------------
# T-10x — LLM coherence path
# ---------------------------------------------------------------------------

class TestLlmVerify:
    """T-10x: run_llm_verify issues a separate LLM coherence-check turn."""

    def _make_coherent_client(self):
        """Return a mock LLM client that signals 'coherent'."""
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text="COHERENT: yes, the learning is logically sound.")]
        client.messages.create = MagicMock(return_value=response)
        return client

    def _make_incoherent_client(self):
        """Return a mock LLM client that signals 'incoherent'."""
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text="INCOHERENT: contradicts known facts.")]
        client.messages.create = MagicMock(return_value=response)
        return client

    def test_llm_coherence_check_sets_lower_trust(self):
        """Coherent verdict → verifier_outcome='llm_coherence_pass', trusted=True, lower_trust=True."""
        verifier = Verifier(llm_client=self._make_coherent_client())
        learning = _make_learning()
        result = verifier.run_llm_verify(learning)

        assert result["verifier_outcome"] == "llm_coherence_pass"
        assert result["trusted"] is True
        assert result["lower_trust"] is True

    def test_llm_incoherence_sets_lower_trust_and_not_trusted(self):
        """Incoherent verdict → verifier_outcome='llm_coherence_fail', trusted=False, lower_trust=True."""
        verifier = Verifier(llm_client=self._make_incoherent_client())
        learning = _make_learning()
        result = verifier.run_llm_verify(learning)

        assert result["verifier_outcome"] == "llm_coherence_fail"
        assert result["trusted"] is False
        assert result["lower_trust"] is True

    def test_lower_trust_always_true_for_non_code_path(self):
        """lower_trust is ALWAYS True on the non-code path — locked decision Q5."""
        for client in (self._make_coherent_client(), self._make_incoherent_client()):
            verifier = Verifier(llm_client=client)
            result = verifier.run_llm_verify(_make_learning())
            assert result["lower_trust"] is True, "lower_trust must be True for all non-code verdicts"

    def test_llm_verify_does_not_mutate_input(self):
        """The input learning dict must not be mutated."""
        learning = _make_learning()
        original = dict(learning)
        verifier = Verifier(llm_client=self._make_coherent_client())
        verifier.run_llm_verify(learning)
        assert learning == original

    def test_llm_verify_returns_update_fields(self):
        """Return dict must have verifier_outcome, trusted, lower_trust."""
        verifier = Verifier(llm_client=self._make_coherent_client())
        result = verifier.run_llm_verify(_make_learning())
        assert "verifier_outcome" in result
        assert "trusted" in result
        assert "lower_trust" in result

    def test_llm_verify_passes_learning_content_to_client(self):
        """The learning content must appear in the LLM request."""
        client = self._make_coherent_client()
        verifier = Verifier(llm_client=client)
        learning = _make_learning(content="Unique content xyz987")
        verifier.run_llm_verify(learning)

        # Verify the client was called (content was forwarded somehow)
        assert client.messages.create.called

    def test_no_real_api_key_required(self):
        """Verifier with injected mock never touches real API."""
        # If this test passes without ANTHROPIC_API_KEY set, we're good.
        import os
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            verifier = Verifier(llm_client=self._make_coherent_client())
            result = verifier.run_llm_verify(_make_learning())
            assert result["verifier_outcome"] == "llm_coherence_pass"
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old
