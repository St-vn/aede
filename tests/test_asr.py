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
