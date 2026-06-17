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
