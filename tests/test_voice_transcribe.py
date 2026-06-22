import pytest
from fastapi.testclient import TestClient


def test_transcribe_returns_text_when_provider_keyed(monkeypatch):
    from aede import server, asr
    from aede.asr import Transcript

    class FakeProvider:
        async def transcribe(self, *, audio, mime, model, language=None):
            return Transcript(text="hello world", model=model, provider="groq")

    monkeypatch.setattr(asr, "build_fallback_chain", lambda model: [(FakeProvider(), "groq", "whisper-large-v3-turbo")])

    client = TestClient(server.app)
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("a.webm", b"\x00\x01", "audio/webm")},
        data={"model": "whisper-large-v3-turbo"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "hello world"
    assert body["provider"] == "groq"


def test_transcribe_signals_webspeech_when_no_provider(monkeypatch):
    from aede import server, asr

    monkeypatch.setattr(asr, "build_fallback_chain", lambda model: [])
    client = TestClient(server.app)
    resp = client.post(
        "/api/voice/transcribe",
        files={"audio": ("a.webm", b"\x00\x01", "audio/webm")},
        data={"model": "whisper-large-v3-turbo"},
    )
    assert resp.status_code == 200
    assert resp.json()["fallback"] == "webspeech"
