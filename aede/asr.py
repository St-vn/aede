from __future__ import annotations

import base64
import io
import os
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


class OpenRouterAsrProvider:
    BASE = "https://openrouter.ai/api/v1/audio/transcriptions"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _post(self, url: str, **kwargs: Any) -> Any:
        import httpx

        async with httpx.AsyncClient(timeout=60) as c:
            return await c.post(url, **kwargs)

    async def transcribe(
        self, *, audio: bytes, mime: str, model: str, language: str | None = None
    ) -> Transcript:
        b64 = base64.b64encode(audio).decode("ascii")
        payload: dict[str, Any] = {
            "model": model,
            "audio": {"data": b64, "format": mime.split("/")[-1]},
        }
        if language:
            payload["language"] = language
        resp = await self._post(
            self.BASE,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return Transcript(
            text=data.get("text", "") or "", model=model, provider="openrouter"
        )


class GoogleAsrProvider:
    BASE = "https://speech.googleapis.com/v2/speech:recognize"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def _post(self, url: str, **kwargs: Any) -> Any:
        import httpx

        async with httpx.AsyncClient(timeout=60) as c:
            return await c.post(url, **kwargs)

    async def transcribe(
        self, *, audio: bytes, mime: str, model: str, language: str | None = None
    ) -> Transcript:
        b64 = base64.b64encode(audio).decode("ascii")
        payload: dict[str, Any] = {
            "config": {
                "model": model,
                "languageCodes": [language or "en-US"],
                "autoDecodingConfig": {},
            },
            "content": b64,
        }
        resp = await self._post(f"{self.BASE}?key={self._api_key}", json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for r in data.get("results", []):
            alts = r.get("alternatives", [])
            if alts:
                text += alts[0].get("transcript", "")
        return Transcript(text=text, model=model, provider="google")


ASR_MODELS: dict[str, dict[str, Any]] = {
    "whisper-large-v3-turbo": {
        "default_provider": "groq",
        "providers": ["groq", "openai", "openrouter"],
    },
    "whisper-large-v3": {
        "default_provider": "groq",
        "providers": ["groq", "openai", "openrouter"],
    },
    "chirp-3": {"default_provider": "google", "providers": ["google", "openrouter"]},
    "parakeet-tdt-0.6b-v3": {
        "default_provider": "openrouter",
        "providers": ["openrouter"],
    },
    "qwen3-asr-flash": {"default_provider": "openrouter", "providers": ["openrouter"]},
    "voxtral-mini-transcribe": {
        "default_provider": "openrouter",
        "providers": ["openrouter"],
    },
}

_PROVIDER_ENV = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _build_provider(name: str, api_key: str) -> Any:
    if name == "groq":
        return OpenAiCompatibleAsrProvider(
            api_key, "https://api.groq.com/openai/v1", "groq"
        )
    if name == "openai":
        return OpenAiCompatibleAsrProvider(
            api_key, "https://api.openai.com/v1", "openai"
        )
    if name == "google":
        return GoogleAsrProvider(api_key)
    if name == "openrouter":
        return OpenRouterAsrProvider(api_key)
    raise ValueError(f"unknown ASR provider {name}")


def get_asr_provider(model: str, provider: str | None = None) -> tuple[Any, str]:
    spec = ASR_MODELS.get(model)
    if spec is None:
        raise ValueError(f"unknown ASR model {model}")
    name = provider or spec["default_provider"]
    key = os.environ.get(_PROVIDER_ENV[name])
    if not key:
        raise RuntimeError(f"{_PROVIDER_ENV[name]} not set for provider {name}")
    return _build_provider(name, key), model


def build_fallback_chain(model: str) -> list[tuple[Any, str]]:
    spec = ASR_MODELS.get(model, {"providers": []})
    chain: list[tuple[Any, str]] = []
    for name in spec["providers"]:
        key = os.environ.get(_PROVIDER_ENV[name])
        if key:
            chain.append((_build_provider(name, key), name))
    return chain
