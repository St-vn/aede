"""
Ollama embedding client for aede.

Provides OllamaClient.embed_text(text) -> list[float] via the local Ollama
HTTP API.  Raises OllamaUnavailable on connection or timeout errors so callers
can degrade gracefully without crashing.
"""
from __future__ import annotations


class OllamaUnavailable(Exception):
    """Raised when the Ollama embedding service cannot be reached."""


class EmbeddingDimensionError(Exception):
    """Raised when the embedding vector has unexpected dimensions."""


class OllamaClient:
    """Thin HTTP client for Ollama's /api/embeddings endpoint.

    Args:
        base_url: Ollama server base URL (default: http://localhost:11434).
        model: Embedding model name (default: nomic-embed-text, 768 dims).
        timeout_s: HTTP request timeout in seconds (default: 5).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout_s: int = 5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    def embed_text(self, text: str) -> list[float]:
        """Return the embedding vector for *text*.

        Makes a POST to ``{base_url}/api/embeddings`` with the configured model.

        Args:
            text: The string to embed.

        Returns:
            A list of floats (768 dims for nomic-embed-text).

        Raises:
            OllamaUnavailable: If Ollama is unreachable or times out.
            EmbeddingDimensionError: If the response is missing the embedding
                key, returns an empty vector, or the vector has the wrong
                number of dimensions.
        """
        import httpx  # lazy — heavy import

        url = f"{self._base_url}/api/embeddings"
        payload = {"model": self._model, "prompt": text}

        try:
            with httpx.Client(timeout=self._timeout_s) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as exc:
            raise OllamaUnavailable(f"Cannot connect to Ollama at {self._base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise OllamaUnavailable(f"Ollama request timed out ({self._timeout_s}s): {exc}") from exc

        embedding_raw = data.get("embedding")
        if embedding_raw is None:
            raise EmbeddingDimensionError(
                "Ollama response missing 'embedding' key"
            )
        vector = [float(v) for v in embedding_raw]
        if not vector:
            raise EmbeddingDimensionError(
                "Ollama returned an empty embedding vector"
            )
        if len(vector) != 768:
            raise EmbeddingDimensionError(
                f"Expected 768-dim embedding, got {len(vector)} dims"
            )
        return vector
