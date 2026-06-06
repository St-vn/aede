"""
LearningsStore — append-only JSONL store for agent learnings.

Each learning is a JSON object on its own line in ``data_dir/learnings.jsonl``.

Schema fields
-------------
id               : str   — ULID, unique per learning
created_at       : int   — Unix milliseconds
type             : str   — IN ('anti-pattern','failed-approach','root-cause','config-correction')
content          : str   — free-text body of the learning
source           : str   — IN ('user','auto_learned','test_failure','tool_error')
source_session_id: str   — session that produced this learning
trusted          : bool  — False by default; elevated by verifier (Phase D)
lower_trust      : bool  — False by default; set for non-code learnings pending verification
verifier_outcome : str|None — None until Phase D verifier runs
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

VALID_TYPES = frozenset({"anti-pattern", "failed-approach", "root-cause", "config-correction"})
VALID_SOURCES = frozenset({"user", "auto_learned", "test_failure", "tool_error"})


class LearningsStore:
    """Append-only JSONL store for agent learnings.

    All writes append a single JSON line.  Deletes and edits perform a
    full-rewrite of the file (acceptable for the expected file sizes).

    Args:
        data_dir: Path to the aede data directory (``cfg.data_dir``).
                  The learnings file is at ``data_dir / "learnings.jsonl"``.
    """

    def __init__(self, data_dir: Path) -> None:
        self._path: Path = data_dir / "learnings.jsonl"

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_learning(
        self,
        type: str,
        content: str,
        source: str,
        source_session_id: str,
        trusted: bool = False,
        lower_trust: bool = False,
        verifier_outcome: str | None = None,
    ) -> dict[str, Any]:
        """Validate and append one learning to the JSONL file.

        Args:
            type: Category — must be one of VALID_TYPES.
            content: Free-text body of the learning.
            source: Origin — must be one of VALID_SOURCES.
            source_session_id: ID of the session that produced this learning.
            trusted: Defaults to False.  Set True only by the verifier (Phase D).
            lower_trust: Defaults to False.  Set True for non-code learnings.
            verifier_outcome: Defaults to None.  Populated by Phase D verifier.

        Returns:
            The full record dict that was written.

        Raises:
            ValueError: If ``type`` or ``source`` are not in their valid sets.
        """
        if type not in VALID_TYPES:
            raise ValueError(
                f"Invalid learning type: {type!r}. Must be one of: {sorted(VALID_TYPES)}"
            )
        if source not in VALID_SOURCES:
            raise ValueError(
                f"Invalid learning source: {source!r}. Must be one of: {sorted(VALID_SOURCES)}"
            )

        from ulid import ULID

        record: dict[str, Any] = {
            "id": str(ULID()),
            "created_at": int(time.time() * 1000),
            "type": type,
            "content": content,
            "source": source,
            "source_session_id": source_session_id,
            "trusted": trusted,
            "lower_trust": lower_trust,
            "verifier_outcome": verifier_outcome,
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_all(self) -> list[dict[str, Any]]:
        """Return all learnings as a list of dicts, in file order."""
        if not self._path.exists():
            return []
        records = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip malformed lines
        return records

    def get(self, learning_id: str) -> dict[str, Any] | None:
        """Return the single learning with the given id, or None if not found."""
        for record in self.list_all():
            if record.get("id") == learning_id:
                return record
        return None

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, learning_id: str) -> bool:
        """Remove the learning with the given id.

        Returns True if it was found and removed, False if not found.
        Performs a full file rewrite.
        """
        records = self.list_all()
        new_records = [r for r in records if r.get("id") != learning_id]
        if len(new_records) == len(records):
            return False  # not found
        self._rewrite(new_records)
        return True

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------

    def update(self, learning_id: str, updated: dict[str, Any]) -> bool:
        """Replace the record with the given id with ``updated``.

        Returns True if the record was found and updated, False otherwise.
        Performs a full file rewrite.
        """
        records = self.list_all()
        found = False
        new_records = []
        for r in records:
            if r.get("id") == learning_id:
                new_records.append(updated)
                found = True
            else:
                new_records.append(r)
        if found:
            self._rewrite(new_records)
        return found

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rewrite(self, records: list[dict[str, Any]]) -> None:
        """Overwrite the JSONL file with the given records."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
