from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


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
