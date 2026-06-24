"""
Tests for OllamaClient — T-07 (embed_text) and T-08 (Ollama-down fallback).

TDD: written FIRST; must fail before implementation.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# T-07: OllamaClient.embed_text — happy path
# ---------------------------------------------------------------------------


def test_embed_text_returns_768_dim_floats():
    """embed_text returns a list of 768 floats when Ollama responds normally."""
    from aede.memory.embeddings import OllamaClient

    fake_embedding = [0.1] * 768
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": fake_embedding}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.return_value = mock_response

        client = OllamaClient()
        result = client.embed_text("hello world")

    assert isinstance(result, list), "embed_text must return a list"
    assert len(result) == 768, f"Expected 768 dims, got {len(result)}"
    assert all(isinstance(v, float) for v in result), "All elements must be float"


# ---------------------------------------------------------------------------
# #45: embedding dimension guard (added at ratify — fix shipped without a test)
# ---------------------------------------------------------------------------


def test_embed_text_raises_on_wrong_dimension():
    """A non-768-dim vector raises EmbeddingDimensionError (#45)."""
    from aede.memory.embeddings import OllamaClient, EmbeddingDimensionError
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": [0.1] * 100}  # wrong dims
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        with pytest.raises(EmbeddingDimensionError):
            OllamaClient().embed_text("x")


def test_embed_text_raises_on_empty_vector():
    """An empty embedding raises EmbeddingDimensionError (#45)."""
    from aede.memory.embeddings import OllamaClient, EmbeddingDimensionError
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": []}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        with pytest.raises(EmbeddingDimensionError):
            OllamaClient().embed_text("x")


def test_embed_text_raises_on_missing_key():
    """A response with no 'embedding' key raises EmbeddingDimensionError (#45)."""
    from aede.memory.embeddings import OllamaClient, EmbeddingDimensionError
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_response
        with pytest.raises(EmbeddingDimensionError):
            OllamaClient().embed_text("x")


def test_embed_text_posts_correct_payload():
    """embed_text POSTs to /api/embeddings with model and prompt fields."""
    from aede.memory.embeddings import OllamaClient

    fake_embedding = [0.0] * 768
    mock_response = MagicMock()
    mock_response.json.return_value = {"embedding": fake_embedding}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.return_value = mock_response

        client = OllamaClient(base_url="http://localhost:11434", model="nomic-embed-text")
        client.embed_text("test input")

        call_args = instance.post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", call_args[0][0])
        # URL should end with /api/embeddings
        assert "/api/embeddings" in str(url), f"Expected /api/embeddings in URL, got {url}"
        # JSON body should contain model and prompt
        json_body = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else None
        if json_body is None:
            # try kwargs
            json_body = call_args.kwargs.get("json")
        assert json_body is not None, "No JSON body passed to POST"
        assert json_body.get("model") == "nomic-embed-text"
        assert json_body.get("prompt") == "test input"


# ---------------------------------------------------------------------------
# T-08: Ollama-down fallback
# ---------------------------------------------------------------------------


def test_ollama_unavailable_raises_exception():
    """ConnectError from httpx raises OllamaUnavailable, not raw httpx exception."""
    import httpx
    from aede.memory.embeddings import OllamaClient, OllamaUnavailable

    with patch("httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = httpx.ConnectError("Connection refused")

        client = OllamaClient()
        with pytest.raises(OllamaUnavailable):
            client.embed_text("hello")


def test_timeout_raises_ollama_unavailable():
    """TimeoutException from httpx raises OllamaUnavailable."""
    import httpx
    from aede.memory.embeddings import OllamaClient, OllamaUnavailable

    with patch("httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = httpx.TimeoutException("timed out")

        client = OllamaClient()
        with pytest.raises(OllamaUnavailable):
            client.embed_text("hello")


def test_aede_starts_without_ollama():
    """Constructing OllamaClient when Ollama is down does not crash."""
    import httpx
    from aede.memory.embeddings import OllamaClient, OllamaUnavailable

    # Construction must always succeed
    client = OllamaClient()
    assert client is not None

    # Calling embed_text raises OllamaUnavailable (not raw exception, not crash)
    with patch("httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = httpx.ConnectError("refused")

        with pytest.raises(OllamaUnavailable):
            client.embed_text("test")
        # No unhandled exception — test reaching here = pass


def test_config_has_ollama_keys(tmp_home):
    """AedeConfig exposes ollama_base_url, ollama_embed_model, ollama_timeout_s."""
    from aede.config import load_config
    cfg = load_config(home=tmp_home)

    assert hasattr(cfg, "ollama_base_url"), "Missing cfg.ollama_base_url"
    assert hasattr(cfg, "ollama_embed_model"), "Missing cfg.ollama_embed_model"
    assert hasattr(cfg, "ollama_timeout_s"), "Missing cfg.ollama_timeout_s"

    assert cfg.ollama_base_url == "http://localhost:11434"
    assert cfg.ollama_embed_model == "nomic-embed-text"
    assert cfg.ollama_timeout_s == 5
