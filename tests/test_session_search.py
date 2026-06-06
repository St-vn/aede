"""
Tests for session_search tool — T-01 (router registration) and T-02 (FTS5 query + context window).

TDD: these tests are written FIRST and must fail before implementation.
"""
from __future__ import annotations
import time
import pytest
from pathlib import Path
from aede.db import DB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "01SSEARCH000000000000000S1"
MODEL = "claude-sonnet-4-20250514"


def _make_db(tmp_home: Path) -> DB:
    return DB(tmp_home / "data" / "aede.db")


def _make_router(db: DB):
    """Build a ToolRouter with a db attached."""
    from aede.tools.router import ToolRouter

    return ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=4096,
        db=db,
    )


def _insert_session(db: DB, session_id: str = SESSION_ID) -> None:
    db.insert_session(
        id=session_id,
        parent_id=None,
        title="search test session",
        model=MODEL,
    )


def _insert_message(db: DB, msg_id: str, session_id: str, role: str, content: str) -> None:
    db.insert_message(
        id=msg_id,
        session_id=session_id,
        role=role,
        content=content,
        token_count=None,
    )


# ---------------------------------------------------------------------------
# T-01: ToolRouter registration
# ---------------------------------------------------------------------------


def test_tool_registered(tmp_home):
    """session_search appears in tool_names() and anthropic_tool_schemas() with correct schema."""
    db = _make_db(tmp_home)
    _insert_session(db)
    router = _make_router(db)

    # Must be in registry
    assert "session_search" in router.tool_names(), (
        "session_search not found in tool_names()"
    )

    # Must appear in anthropic_tool_schemas
    schemas = router.anthropic_tool_schemas()
    schema_names = [s["name"] for s in schemas]
    assert "session_search" in schema_names, (
        "session_search not found in anthropic_tool_schemas()"
    )

    # Find the schema and check input_schema
    ss_schema = next(s for s in schemas if s["name"] == "session_search")
    props = ss_schema["input_schema"]["properties"]

    assert "query" in props, "input_schema missing 'query' property"
    assert props["query"]["type"] == "string", "'query' property must be type string"

    assert "limit" in props, "input_schema missing 'limit' property"
    assert props["limit"]["type"] == "integer", "'limit' property must be type integer"

    required = ss_schema["input_schema"].get("required", [])
    assert "query" in required, "'query' must be required"
    assert "limit" not in required, "'limit' must be optional (not required)"


def test_session_search_not_gated(tmp_home):
    """session_search is read-only — requires_approval must return False."""
    db = _make_db(tmp_home)
    _insert_session(db)
    router = _make_router(db)
    assert not router.requires_approval("session_search"), (
        "session_search should not require approval (read-only tool)"
    )


# ---------------------------------------------------------------------------
# T-02: FTS5 query + context window
# ---------------------------------------------------------------------------


def test_search_with_context_window(tmp_home):
    """Insert 15 messages; search for unique token; verify hit + ±5 context + bookends."""
    db = _make_db(tmp_home)
    _insert_session(db)

    # Insert 15 messages with sequential IDs; message #8 (0-indexed: 7) contains the marker.
    # We need a unique token that FTS5 will tokenise as a single term.
    MARKER = "zzqqxxmarker"
    messages = []
    for i in range(15):
        content = f"Message number {i}." if i != 7 else f"Special content {MARKER} here."
        msg_id = f"01SSEARCH000000000000000M{i:X}"
        messages.append((msg_id, content))
        _insert_message(
            db=db,
            msg_id=msg_id,
            session_id=SESSION_ID,
            role="user" if i % 2 == 0 else "assistant",
            content=content,
        )
        # Tiny sleep so created_at values are monotonically distinct.
        time.sleep(0.002)

    # --- Test via DB.search_messages directly ---
    results = db.search_messages(query=MARKER, limit=10)

    # Must return at least one result group
    assert len(results) > 0, "search_messages returned no results"

    hit_group = results[0]

    # The hit message must be present
    context_contents = [m["content"] for m in hit_group["context"]]
    assert any(MARKER in c for c in context_contents), (
        f"Marker {MARKER!r} not found in context messages"
    )

    # Bookends must be present
    assert "bookends" in hit_group, "Result group missing 'bookends' key"
    bookend_contents = [m["content"] for m in hit_group["bookends"]]
    # First message (i=0) and last message (i=14) should be in bookends
    assert any("Message number 0" in c for c in bookend_contents), (
        "First session message not in bookends"
    )
    assert any("Message number 14" in c for c in bookend_contents), (
        "Last session message not in bookends"
    )

    # Session metadata must be present
    assert "session_id" in hit_group, "Result group missing 'session_id'"
    assert hit_group["session_id"] == SESSION_ID
    assert "session_title" in hit_group, "Result group missing 'session_title'"
    assert "session_created_at" in hit_group, "Result group missing 'session_created_at'"

    # Context window: marker is message index 7 (0-indexed), so we expect messages
    # at indices 2..12 (±5 around index 7), which is 11 messages after dedup.
    # The bookends (idx 0 and 14) are separate.
    # At minimum, 5 messages before and after the hit must be in context.
    context_set = set(c for c in context_contents)
    for i in range(2, 13):  # indices 2..12 inclusive = ±5 around index 7
        expected = f"Message number {i}." if i != 7 else f"Special content {MARKER} here."
        assert expected in context_set, (
            f"Expected context message at index {i} not found: {expected!r}"
        )


def test_search_via_execute_sync(tmp_home):
    """session_search callable via router.execute_sync — returns ToolResult with output."""
    db = _make_db(tmp_home)
    _insert_session(db)

    MARKER = "zzqqxxsynctest"
    _insert_message(
        db=db,
        msg_id="01SSEARCH000000000000000X1",
        session_id=SESSION_ID,
        role="user",
        content=f"Testing sync dispatch {MARKER} works.",
    )

    router = _make_router(db)
    result = router.execute_sync("session_search", {"query": MARKER})

    assert result.status == "success", f"execute_sync returned error: {result.output}"
    assert MARKER in result.output, (
        f"Marker {MARKER!r} not found in tool output:\n{result.output}"
    )


def test_search_no_results(tmp_home):
    """Querying a token that doesn't exist returns a clean 'no results' response."""
    db = _make_db(tmp_home)
    _insert_session(db)

    results = db.search_messages(query="totallymadeuptoken99xyz", limit=10)
    assert results == [], f"Expected empty list for no matches, got: {results}"


def test_db_search_without_db_raises(tmp_home):
    """session_search raises a clear error when called without a db."""
    from aede.tools.router import ToolRouter

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=4096,
        # no db=
    )
    # When no db is provided, session_search should not even be registered
    # (or if registered, should return an error result — we check either way)
    if "session_search" not in router.tool_names():
        return  # expected: not registered without db

    # If registered anyway, execute_sync must return status="error" not raise
    result = router.execute_sync("session_search", {"query": "anything"})
    assert result.status == "error", (
        "session_search without db should return error status"
    )
