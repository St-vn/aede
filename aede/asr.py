from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class Transcript:
    text: str
    model: str
    provider: str


@runtime_checkable
class AsrProvider(Protocol):
    async def transcribe(
        self, *, audio: bytes, mime: str, model: str, language: str | None = None
    ) -> Transcript: ...


class OpenAiCompatibleAsrProvider:
    def __init__(self, api_key: str, base_url: str, provider_name: str) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._provider_name = provider_name
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    async def transcribe(
        self, *, audio: bytes, mime: str, model: str, language: str | None = None
    ) -> Transcript:
        client = self._get_client()
        ext = mime.split("/")[-1] or "webm"
        buf = io.BytesIO(audio)
        buf.name = f"audio.{ext}"
        kwargs: dict[str, Any] = {"model": model, "file": buf}
        if language:
            kwargs["language"] = language
        resp = await client.audio.transcriptions.create(**kwargs)
        return Transcript(
            text=getattr(resp, "text", "") or "",
            model=model,
            provider=self._provider_name,
        )
