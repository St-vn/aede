"""
Token tracking and cost estimation for aede sessions.

``TokenTracker`` accumulates per-turn usage reported by the provider and
persists it to the DB.  ``PriceCache`` maintains a 24-hour disk cache of
OpenRouter model pricing so cost estimates are available without a live API
call.  ``estimate_cost`` converts token counts to USD using the price table.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

FALLBACK_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00, "cache_read": 0.30},
    "claude-opus-4-20250514":   {"input": 15.00, "output": 75.00, "cache_read": 1.50},
    "claude-haiku-4-20250514":  {"input": 0.80,  "output": 4.00,  "cache_read": 0.08},
}

CACHE_TTL_SECONDS = 86400  # 24 hours


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    prices: dict[str, dict[str, float]] | None,
) -> float | None:
    """Estimate session cost in USD.

    Args:
        model: Model identifier used to look up per-token pricing.
        input_tokens: Total input tokens billed this session.
        output_tokens: Total output tokens billed this session.
        cached_tokens: Subset of ``input_tokens`` served from the prompt cache.
        prices: Mapping of model → ``{input, output, cache_read}`` prices per
            million tokens.  Falls back to ``FALLBACK_PRICES`` if ``None``.

    Returns:
        Estimated cost in USD, or ``None`` if the model is not in the price
        table.
    """
    price_table = prices or FALLBACK_PRICES
    p = price_table.get(model)
    if not p:
        return None
    per_m = 1_000_000
    uncached_input = max(0, input_tokens - cached_tokens)
    cost = (
        uncached_input / per_m * p["input"]
        + cached_tokens / per_m * p["cache_read"]
        + output_tokens / per_m * p["output"]
    )
    return cost


class TokenTracker:
    """Accumulates token usage across turns and persists each row to the DB.

    In-memory records are kept for the lifetime of the process so ``totals``
    and ``cache_hit_rate`` can be computed without a DB query.
    """

    def __init__(self, session_id: str, db: Any) -> None:
        self._session_id = session_id
        self._db = db
        self._records: list[dict] = []

    def record(
        self,
        turn: int,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
    ) -> None:
        """Record token usage for one completed LLM turn and persist it to the DB."""
        self._records.append({
            "turn": turn,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
        })
        if self._db is not None:
            from ulid import ULID
            self._db.insert_token_usage(
                id=str(ULID()),
                session_id=self._session_id,
                turn_number=turn,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_tokens=cached_tokens,
            )

    def totals(self) -> dict[str, int]:
        """Return cumulative ``{input_tokens, output_tokens, cached_tokens}`` for the session."""
        return {
            "input_tokens": sum(r["input_tokens"] for r in self._records),
            "output_tokens": sum(r["output_tokens"] for r in self._records),
            "cached_tokens": sum(r["cached_tokens"] for r in self._records),
        }

    def cache_hit_rate(self) -> float:
        """Return the fraction of input tokens served from the prompt cache (0.0–1.0)."""
        t = self.totals()
        if t["input_tokens"] == 0:
            return 0.0
        return t["cached_tokens"] / t["input_tokens"]


class PriceCache:
    """Disk-backed cache for OpenRouter model pricing data.

    Prices are stored as JSON at ``path`` with a ``fetched_at`` Unix timestamp.
    The cache is considered stale after ``CACHE_TTL_SECONDS`` (24 hours) and
    ``load`` returns ``None`` to signal a refresh is needed.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, dict[str, float]] | None:
        """Load prices from disk; returns ``None`` if the file is absent, stale, or corrupt."""
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            fetched_at = data.get("fetched_at", 0)
            if time.time() - fetched_at > CACHE_TTL_SECONDS:
                return None
            return data.get("prices")
        except Exception:
            return None

    def save(self, prices: dict[str, dict[str, float]]) -> None:
        """Persist ``prices`` to disk with the current timestamp."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"prices": prices, "fetched_at": time.time()}))

    async def fetch_openrouter(self) -> dict[str, dict[str, float]] | None:
        """Fetch current model pricing from the OpenRouter API.

        Returns a ``{model_id: {input, output, cache_read}}`` dict (prices per
        million tokens), or ``None`` if the request fails for any reason.
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://openrouter.ai/api/v1/models")
                resp.raise_for_status()
                data = resp.json()
                prices: dict[str, dict[str, float]] = {}
                for model in data.get("data", []):
                    mid = model.get("id", "")
                    pricing = model.get("pricing", {})
                    if pricing:
                        prices[mid] = {
                            "input": float(pricing.get("prompt", 0)) * 1_000_000,
                            "output": float(pricing.get("completion", 0)) * 1_000_000,
                            "cache_read": float(pricing.get("input_cache_read", 0)) * 1_000_000,
                        }
                return prices
        except Exception:
            return None
