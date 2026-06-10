from __future__ import annotations
from pathlib import Path
from typing import Any
import json


MODEL_PRESETS: dict[str, list[dict[str, str]]] = {
    "anthropic": [
        {"id": "claude-fable-5", "label": "Claude Fable 5"},
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
    "codex": [
        {"id": "codex", "label": "Codex"},
        {"id": "codex/gpt-5.5", "label": "Codex / GPT-5.5"},
        {"id": "codex/gpt-5.3-codex", "label": "Codex / GPT-5.3-Codex"},
        {"id": "codex/o3", "label": "Codex / o3"},
        {"id": "codex/o4-mini", "label": "Codex / o4-mini"},
    ],
    "claude-code": [
        {"id": "claude-code", "label": "Claude Code"},
        {"id": "claude-code/fable-5", "label": "Claude Code / Fable 5"},
        {"id": "claude-code/opus-4-8", "label": "Claude Code / Opus 4.8"},
        # {"id": "claude-code/opus-4-7", "label": "Claude Code / Opus 4.7"},
        {"id": "claude-code/sonnet-4-6", "label": "Claude Code / Sonnet 4.6"},
        {"id": "claude-code/haiku-4-5", "label": "Claude Code / Haiku 4.5"},
    ],
    "gemini": [{"id": "gemini", "label": "Gemini"}],
    "agy": [
        {"id": "agy", "label": "Antigravity"},
        {"id": "agy/gemini-3-5-flash", "label": "Antigravity / Gemini 3.5 Flash"},
        {"id": "agy/gemini-3-1-pro", "label": "Antigravity / Gemini 3.1 Pro"},
        {"id": "agy/claude-sonnet-4-6", "label": "Antigravity / Claude Sonnet 4.6"},
        {"id": "agy/claude-opus-4-6", "label": "Antigravity / Claude Opus 4.6"},
    ],
    "cline": [{"id": "cline", "label": "Cline"}],
    "cursor": [{"id": "cursor", "label": "Cursor"}],
    "goose": [
        {"id": "goose", "label": "Goose"},
        {"id": "goose/anthropic-claude-sonnet-4-6", "label": "Goose / Claude Sonnet 4.6"},
        {"id": "goose/openai-gpt-4o", "label": "Goose / GPT-4o"},
    ],
    "opencode": [{"id": "opencode", "label": "OpenCode"}],
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
