from __future__ import annotations
from typing import Any


class OllamaUnavailable(Exception):
    """Raised when the Ollama server is unreachable."""


class OllamaClient:
    """HTTP client for Ollama embeddings API (lazy httpx import)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text", timeout_s: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string and return a 768-dim float vector."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return list(data["embedding"])
        except (httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
            raise OllamaUnavailable(f"Ollama unavailable: {e}") from e
