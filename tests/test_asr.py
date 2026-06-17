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
