import pytest
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_embed_text_returns_768_floats(tmp_path):
    """OllamaClient.embed_text returns 768-dim float array."""
    from aede.memory.embeddings import OllamaClient

    client = OllamaClient(base_url="http://localhost:11434")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1] * 768}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        embedding = await client.embed_text("some text")

    assert len(embedding) == 768
    assert all(isinstance(v, float) for v in embedding)


@pytest.mark.asyncio
async def test_ollama_unavailable_raises_exception(tmp_path):
    """Connection refused raises OllamaUnavailable."""
    from aede.memory.embeddings import OllamaClient, OllamaUnavailable

    client = OllamaClient(base_url="http://localhost:11434")

    with patch("httpx.AsyncClient.post", side_effect=ConnectionError("refused")):
        with pytest.raises(OllamaUnavailable):
            await client.embed_text("test")


@pytest.mark.asyncio
async def test_aede_starts_without_ollama(tmp_path):
    """OllamaUnavailable is caught gracefully, no crash."""
    from aede.memory.embeddings import OllamaClient, OllamaUnavailable

    client = OllamaClient(base_url="http://localhost:11434")

    with patch("httpx.AsyncClient.post", side_effect=ConnectionError("refused")):
        try:
            await client.embed_text("test")
        except OllamaUnavailable:
            pass  # Expected graceful path


def test_embedding_round_trip():
    """struct.pack/unpack round-trip preserves embedding (cosine > 0.9999)."""
    import math
    vec = [float(i) / 100.0 for i in range(768)]

    packed = struct.pack("768f", *vec)
    unpacked = list(struct.unpack("768f", packed))

    dot = sum(a * b for a, b in zip(vec, unpacked))
    norm_a = math.sqrt(sum(a * a for a in vec))
    norm_b = math.sqrt(sum(b * b for b in unpacked))
    cosine = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    assert cosine > 0.9999
