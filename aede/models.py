from __future__ import annotations
from pathlib import Path
from typing import Any
import json


MODEL_PRESETS: dict[str, list[dict[str, str]]] = {
    "anthropic": [
        {"id": "claude-opus-4-8", "label": "Claude Opus 4.8"},
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
    ],
    "openai": [
        {"id": "gpt-5.5", "label": "GPT-5.5"},
    ],
    "deepseek": [
        {"id": "deepseek-chat", "label": "DeepSeek Chat (V4)"},
    ],
    "openrouter": [
        {"id": "openrouter/auto", "label": "OpenRouter Auto"},
    ],
    "google-ai": [
        {"id": "gemini-3.5-flash", "label": "Gemini 3.5 Flash"},
    ],
    "codex": [{"id": "codex", "label": "Codex"}],
    "claude-code": [{"id": "claude-code", "label": "Claude Code"}],
    "gemini": [{"id": "gemini", "label": "Gemini"}],
    "agy": [{"id": "agy", "label": "Agy"}],
}


def models_path(home: Path) -> Path:
    return home / "models.json"


def default_models() -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for provider, presets in MODEL_PRESETS.items():
        for p in presets:
            models.append({**p, "provider": provider})
    return models


def load_models(home: Path) -> list[dict[str, Any]]:
    path = models_path(home)
    if not path.exists():
        return default_models()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return default_models()


def save_models(home: Path, models: list[dict[str, Any]]) -> None:
    path = models_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(models, indent=2), encoding="utf-8")


def reset_models(home: Path) -> None:
    path = models_path(home)
    if path.exists():
        path.unlink()
