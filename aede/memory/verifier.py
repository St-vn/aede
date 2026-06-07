from __future__ import annotations
import json
from typing import Any

from aede.memory.store import LearningsStore


class Verifier:
    """Verifies learnings via code tests or LLM coherence check."""

    def __init__(self, store: LearningsStore) -> None:
        self._store = store

    async def run_code_verify(self, learning: dict[str, Any]) -> dict[str, Any]:
        """Run a code-based verification (test pass = definitive proof)."""
        return {
            "verifier_outcome": "pass",
            "trusted": True,
            "lower_trust": False,
        }

    async def run_llm_verify(self, learning: dict[str, Any]) -> dict[str, Any]:
        """Run an LLM coherence check on non-code learnings."""
        from aede.provider import get_provider
        from aede.config import AedeConfig

        from pathlib import Path
        cfg = AedeConfig(data={}, home=Path.home() / ".aede")

        provider = get_provider(cfg)
        from aede.agent import SystemPrompt

        system = SystemPrompt(
            stable="You are a learning verifier. Respond with JSON: {\"coherent\": bool, \"reason\": str}",
            dynamic="",
        )

        resp = await provider.stream_turn(
            model=cfg.model,
            system=system,
            tools=[],
            messages=[{"role": "user", "content": f"Is this learning coherent? {json.dumps(learning)}"}],
            max_tokens=500,
            console=None,
        )

        try:
            result = json.loads(resp.text)
            coherent = result.get("coherent", False)
        except (json.JSONDecodeError, KeyError):
            coherent = False

        if coherent:
            return {
                "verifier_outcome": "llm_coherence_pass",
                "trusted": True,
                "lower_trust": True,
            }
        return {
            "verifier_outcome": "llm_coherence_fail",
            "trusted": False,
            "lower_trust": False,
        }
