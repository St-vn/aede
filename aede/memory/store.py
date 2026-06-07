from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from ulid import ULID


class LearningType(str, Enum):
    ANTI_PATTERN = "anti-pattern"
    FAILED_APPROACH = "failed-approach"
    ROOT_CAUSE = "root-cause"
    CONFIG_CORRECTION = "config-correction"


class LearningSource(str, Enum):
    USER = "user"
    AUTO_LEARNED = "auto_learned"
    TEST_FAILURE = "test_failure"
    TOOL_ERROR = "tool_error"


VALID_TYPES = {e.value for e in LearningType}
VALID_SOURCES = {e.value for e in LearningSource}


class LearningsStore:
    """Append-only JSONL store for learnings with read/update/delete."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write_learning(
        self,
        type: str | LearningType,
        content: str,
        source: str | LearningSource,
        source_session_id: str,
        trusted: bool = False,
        embedding: bytes | None = None,
    ) -> dict[str, Any]:
        type_val = type.value if isinstance(type, LearningType) else type
        source_val = source.value if isinstance(source, LearningSource) else source

        if type_val not in VALID_TYPES:
            raise ValueError(f"Invalid learning type: {type_val!r}. Valid: {VALID_TYPES}")
        if source_val not in VALID_SOURCES:
            raise ValueError(f"Invalid learning source: {source_val!r}. Valid: {VALID_SOURCES}")

        import time
        record = {
            "id": str(ULID()),
            "type": type_val,
            "content": content,
            "source": source_val,
            "source_session_id": source_session_id,
            "trusted": trusted,
            "lower_trust": False,
            "verifier_outcome": None,
            "created_at": int(time.time() * 1000),
        }
        if embedding is not None:
            record["embedding_b64"] = embedding.hex()

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        results: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        return results

    def delete(self, learning_id: str) -> bool:
        items = self.read_all()
        filtered = [i for i in items if i["id"] != learning_id]
        if len(filtered) == len(items):
            return False
        self._rewrite_all(filtered)
        return True

    def update(self, learning_id: str, **kwargs: Any) -> bool:
        items = self.read_all()
        found = False
        for item in items:
            if item["id"] == learning_id:
                item.update({k: v for k, v in kwargs.items() if v is not None})
                found = True
                break
        if not found:
            return False
        self._rewrite_all(items)
        return True

    def _rewrite_all(self, items: list[dict[str, Any]]) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")
