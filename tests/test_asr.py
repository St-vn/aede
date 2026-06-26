# tests/test_asr.py
from aede.asr import Transcript, AsrProvider


def test_transcript_dataclass():
    t = Transcript(text="hello", model="whisper-large-v3-turbo", provider="groq")
    assert t.text == "hello"
    assert t.model == "whisper-large-v3-turbo"
    assert t.provider == "groq"


def test_provider_protocol_runtime_checkable():
    class Dummy:
        async def transcribe(self, *, audio, mime, model, language=None):
            return Transcript(text="x", model=model, provider="dummy")

    assert isinstance(Dummy(), AsrProvider)


import pytest


@pytest.mark.asyncio
async def test_openai_compatible_transcribe(monkeypatch):
    from aede.asr import OpenAiCompatibleAsrProvider, Transcript

    class FakeTranscriptions:
        async def create(self, **kwargs):
            assert kwargs["model"] == "whisper-large-v3-turbo"

            class R:
                text = "transcribed text"

            return R()

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeClient:
        audio = FakeAudio()

    p = OpenAiCompatibleAsrProvider(
        api_key="k",
        base_url="https://api.groq.com/openai/v1",
        provider_name="groq",
    )
    monkeypatch.setattr(p, "_get_client", lambda: FakeClient())
    t = await p.transcribe(audio=b"\x00\x01", mime="audio/webm", model="whisper-large-v3-turbo")
    assert isinstance(t, Transcript)
    assert t.text == "transcribed text"
    assert t.provider == "groq"


@pytest.mark.asyncio
async def test_openrouter_transcribe(monkeypatch):
    from aede.asr import OpenRouterAsrProvider, Transcript

    captured = {}

    async def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")

        class R:
            status_code = 200

            def json(self):
                return {"text": "openrouter result"}

            def raise_for_status(self):
                pass

        return R()

    p = OpenRouterAsrProvider(api_key="k")
    monkeypatch.setattr(p, "_post", fake_post)
    t = await p.transcribe(audio=b"abc", mime="audio/webm", model="parakeet-tdt-0.6b-v3")
    assert t.text == "openrouter result"
    assert t.provider == "openrouter"
    assert t.model == "parakeet-tdt-0.6b-v3"


@pytest.mark.asyncio
async def test_google_transcribe(monkeypatch):
    from aede.asr import GoogleAsrProvider, Transcript

    async def fake_post(url, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {
                    "results": [
                        {"alternatives": [{"transcript": "chirp text"}]}
                    ]
                }

            def raise_for_status(self):
                pass

        return R()

    p = GoogleAsrProvider(api_key="k")
    monkeypatch.setattr(p, "_post", fake_post)
    t = await p.transcribe(audio=b"abc", mime="audio/webm", model="chirp-3")
    assert t.text == "chirp text"
    assert t.provider == "google"


def test_model_registry_maps_models_to_providers():
    from aede.asr import ASR_MODELS

    assert ASR_MODELS["whisper-large-v3-turbo"]["default_provider"] == "groq"
    assert "openrouter" in ASR_MODELS["parakeet-tdt-0.6b-v3"]["providers"]
    assert ASR_MODELS["chirp-3"]["default_provider"] == "google"


def test_get_asr_provider_uses_default_when_keyed(monkeypatch):
    from aede.asr import get_asr_provider, OpenAiCompatibleAsrProvider

    monkeypatch.setenv("GROQ_API_KEY", "k")
    p, model = get_asr_provider("whisper-large-v3-turbo")
    assert isinstance(p, OpenAiCompatibleAsrProvider)
    assert model == "whisper-large-v3-turbo"


def test_build_chain_falls_through_to_webspeech(monkeypatch):
    from aede.asr import build_fallback_chain

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    chain = build_fallback_chain("whisper-large-v3-turbo")
    assert chain == []  # no keyed providers → caller signals webspeech floor


def test_openrouter_model_id_is_namespaced(monkeypatch):
    """OpenRouter needs namespaced slugs (openai/whisper-1), not bare canonical ids."""
    from aede.asr import build_fallback_chain
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    chain = build_fallback_chain("voxtral-mini-transcribe")
    assert len(chain) == 1
    _provider, name, provider_model_id = chain[0]
    assert name == "openrouter"
    assert provider_model_id == "mistralai/voxtral-mini-transcribe"

@pytest.mark.asyncio
async def test_google_api_key_in_header_not_url(monkeypatch):
    from aede.asr import GoogleAsrProvider, Transcript

    captured: dict = {}

    async def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        class R:
            status_code = 200
            def json(self):
                return {"results": [{"alternatives": [{"transcript": "test"}]}]}
            def raise_for_status(self):
                pass
        return R()

    p = GoogleAsrProvider(api_key="my-secret-key")
    monkeypatch.setattr(p, "_post", fake_post)
    t = await p.transcribe(audio=b"abc", mime="audio/webm", model="chirp-3")

    assert "?key=" not in captured["url"], f"URL leaked key: {captured['url']}"
    assert captured["headers"] is not None, "no headers passed to _post"
    assert captured["headers"].get("x-goog-api-key") == "my-secret-key"
    assert t.text == "test"
