import json
import pytest
from pathlib import Path
from jarvis.rollout import Rollout


def test_rollout_creates_file(tmp_home):
    r = Rollout(tmp_home / "data" / "sessions", "01JSESSION00001")
    r.write({"type": "session_start", "session_id": "01JSESSION00001"})
    files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
    assert len(files) == 1


def test_rollout_appends_records(tmp_home):
    r = Rollout(tmp_home / "data" / "sessions", "01JSESSION00002")
    r.write({"type": "session_start", "session_id": "01JSESSION00002"})
    r.write({"type": "user_message", "content": "hello"})
    r.write({"type": "session_end", "status": "archived"})
    files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
    # Find the file for this session
    session_file = None
    for f in files:
        if "01JSESSION00002" in f.name:
            session_file = f
            break
    assert session_file is not None
    lines = session_file.read_text().strip().splitlines()
    assert len(lines) == 3


def test_rollout_valid_jsonl(tmp_home):
    r = Rollout(tmp_home / "data" / "sessions", "01JSESSION00003")
    r.write({"type": "user_message", "content": "test"})
    files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
    for line in files[-1].read_text().strip().splitlines():
        parsed = json.loads(line)
        assert parsed["v"] == 1
        assert "ts" in parsed


def test_rollout_path_includes_date(tmp_home):
    r = Rollout(tmp_home / "data" / "sessions", "01JSESSION00004")
    r.write({"type": "session_start"})
    files = list((tmp_home / "data" / "sessions").rglob("*.jsonl"))
    # path should be YYYY/MM/DD/rollout-<id>.jsonl
    session_file = None
    for f in files:
        if "01JSESSION00004" in f.name:
            session_file = f
            break
    assert session_file is not None
    parts = session_file.parts
    assert any(len(p) == 4 and p.isdigit() for p in parts)  # year
