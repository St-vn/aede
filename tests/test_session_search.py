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


def _make_router(db: DB, session_id: str | None = None):
    """Build a ToolRouter with a db attached."""
    from aede.tools.router import ToolRouter

    return ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=4096,
        db=db,
        _session_id=session_id,
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


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# T-03: Cross-session isolation (CVE fix)
# ---------------------------------------------------------------------------


SESSION_A = "01SSEARCH000000000000000SA"
SESSION_B = "01SSEARCH000000000000000SB"


def test_cross_session_isolation_via_db(tmp_home):
    """search_messages with session_id returns only messages from that session."""
    db = _make_db(tmp_home)
    db.insert_session(id=SESSION_A, parent_id=None, title="session A", model=MODEL)
    db.insert_session(id=SESSION_B, parent_id=None, title="session B", model=MODEL)

    MARKER = "zzqqxxcrosssession"
    _insert_message(db, "01SSEARCH000000000000M0A", SESSION_A, "user",
                    f"Session A secret: {MARKER}")
    _insert_message(db, "01SSEARCH000000000000M0B", SESSION_B, "user",
                    "Session B mundane content")

    global_results = db.search_messages(query=MARKER, limit=10)
    assert len(global_results) == 1, "Global search should find the marker"

    scoped_a = db.search_messages(query=MARKER, limit=10, session_id=SESSION_A)
    assert len(scoped_a) == 1, "Session A scoped search should find the marker"

    scoped_b = db.search_messages(query=MARKER, limit=10, session_id=SESSION_B)
    assert scoped_b == [], f"Session B scoped search should be empty, got: {scoped_b}"


def test_cross_session_isolation_via_execute_sync(tmp_home):
    """session_search via router.execute_sync with session_id scopes results."""
    db = _make_db(tmp_home)
    db.insert_session(id=SESSION_A, parent_id=None, title="session A", model=MODEL)
    db.insert_session(id=SESSION_B, parent_id=None, title="session B", model=MODEL)

    MARKER = "zzqqxxroutescope"
    _insert_message(db, "01SSEARCH000000000000M0C", SESSION_A, "user",
                    f"Session A: {MARKER}")
    _insert_message(db, "01SSEARCH000000000000M0D", SESSION_B, "user",
                    "Session B only")

    router_a = _make_router(db, session_id=SESSION_A)
    result_a = router_a.execute_sync("session_search", {"query": MARKER})
    assert result_a.status == "success", f"session_search failed: {result_a.output}"
    assert MARKER in result_a.output, "Session A should see its own message"

    router_b = _make_router(db, session_id=SESSION_B)
    result_b = router_b.execute_sync("session_search", {"query": MARKER})
    assert result_b.status == "success"
    assert "(no results" in result_b.output, "Session B should get no-results for Session A marker"


# T-06: write_learning tool registration
# ---------------------------------------------------------------------------


def test_write_learning_registered(tmp_home):
    """write_learning is in the registry with a valid schema and requires approval."""
    from aede.config import bootstrap
    from aede.tools.router import ToolRouter, GATE_TOOLS

    bootstrap(tmp_home)
    data_dir = tmp_home / "data"

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=4096,
        db=None,
        data_dir=data_dir,
    )

    # Must appear in tool_names
    assert "write_learning" in router.tool_names(), (
        "write_learning not found in tool_names()"
    )

    # Must appear in anthropic_tool_schemas with correct fields
    schemas = router.anthropic_tool_schemas()
    schema_names = [s["name"] for s in schemas]
    assert "write_learning" in schema_names, (
        "write_learning not found in anthropic_tool_schemas()"
    )

    wl_schema = next(s for s in schemas if s["name"] == "write_learning")
    props = wl_schema["input_schema"]["properties"]
    required = wl_schema["input_schema"].get("required", [])

    assert "type" in props, "schema missing 'type' property"
    assert "content" in props, "schema missing 'content' property"
    assert "source" in props, "schema missing 'source' property"
    assert "source_session_id" in props, "schema missing 'source_session_id' property"

    for field in ["type", "content", "source"]:
        assert field in required, f"'{field}' must be required in schema"

    # MUST require approval — it is a memory write (MEM-03 / Q10)
    assert router.requires_approval("write_learning"), (
        "write_learning must require approval (memory write — gated)"
    )

    # Confirm it is in GATE_TOOLS (the canonical gated set)
    assert "write_learning" in GATE_TOOLS, (
        "write_learning must be listed in GATE_TOOLS"
    )
