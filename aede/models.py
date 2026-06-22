from __future__ import annotations
from pathlib import Path
from typing import Any
import json


VISION_MODELS: set[str] = {
    # Anthropic
    "claude-sonnet-4-6", "claude-opus-4-8", "claude-fable-5",
    "claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-4-20250514",
    # OpenAI
    "gpt-5.5", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
    # Google
    "gemini-3.5-flash", "gemini-2.5-flash",
    # DeepSeek (via API)
    "deepseek-v4-pro", "deepseek-v4-flash",
    # MiniMax
    "minimax-m3",
    # GLM
    "glm-5.2", "glm-5.1", "glm-5",
    # Kimi
    "kimi-k2.7", "kimi-k2.5",
}

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
        {"id": "zhipuai/glm-5.2", "label": "GLM-5.2"},
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
    ],
    "opencode-zen": [
        # Free models
        {"id": "deepseek-v4-flash-free", "label": "DeepSeek V4 Flash Free"},
        {"id": "nemotron-3-ultra-free", "label": "Nemotron 3 Ultra Free"},
        {"id": "big-pickle", "label": "Big Pickle"},
        {"id": "mimo-v2.5-free", "label": "MIMO V2.5 Free"},
        {"id": "north-mini-code-free", "label": "North Mini Code Free"},
        # Paid chat-completions models (exclusive to Zen)
        {"id": "grok-build-0.1", "label": "Grok Build 0.1"},
        {"id": "kimi-k2.5", "label": "Kimi K2.5"},
        {"id": "glm-5.2", "label": "GLM-5.2"},
    ],
    "opencode-go": [
        {"id": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
        {"id": "deepseek-v4-flash", "label": "DeepSeek V4 Flash"},
        {"id": "glm-5.2", "label": "GLM-5.2"},
        {"id": "glm-5.1", "label": "GLM-5.1"},
        {"id": "glm-5", "label": "GLM-5"},
        {"id": "kimi-k2.7", "label": "Kimi K2.7"},
        {"id": "kimi-k2.6", "label": "Kimi K2.6"},
        {"id": "minimax-m3", "label": "MiniMax M3"},
        {"id": "minimax-m2.7", "label": "MiniMax M2.7"},
        {"id": "minimax-m2.5", "label": "MiniMax M2.5"},
        {"id": "qwen3.7-max", "label": "Qwen 3.7 Max"},
        {"id": "qwen3.7-plus", "label": "Qwen 3.7 Plus"},
        {"id": "qwen3.6-plus", "label": "Qwen 3.6 Plus"},
        {"id": "mimo-v2.5", "label": "MIMO V2.5"},
        {"id": "mimo-v2.5-pro", "label": "MIMO V2.5 Pro"},
    ],
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
