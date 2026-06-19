import pytest
import json
from pathlib import Path
from aede.tokens import TokenTracker, FALLBACK_PRICES, estimate_cost


def test_tracker_accumulates(tmp_home):
    tracker = TokenTracker(session_id="SID001", db=None)
    tracker.record(turn=1, input_tokens=100, output_tokens=20, cached_tokens=80)
    tracker.record(turn=2, input_tokens=200, output_tokens=40, cached_tokens=150)
    totals = tracker.totals()
    assert totals["input_tokens"] == 300
    assert totals["output_tokens"] == 60
    assert totals["cached_tokens"] == 230


def test_cache_hit_rate():
    tracker = TokenTracker(session_id="SID002", db=None)
    tracker.record(turn=1, input_tokens=100, output_tokens=10, cached_tokens=80)
    assert tracker.cache_hit_rate() == pytest.approx(0.8)


def test_cache_hit_rate_zero_input():
    tracker = TokenTracker(session_id="SID003", db=None)
    assert tracker.cache_hit_rate() == 0.0


def test_fallback_prices_exist():
    assert "claude-sonnet-4-6" in FALLBACK_PRICES
    assert "input" in FALLBACK_PRICES["claude-sonnet-4-6"]
    assert "output" in FALLBACK_PRICES["claude-sonnet-4-6"]
    assert "cache_read" in FALLBACK_PRICES["claude-sonnet-4-6"]


def test_estimate_cost_known_model():
    cost = estimate_cost(
        model="claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=0,
        prices=None,
    )
    assert cost == pytest.approx(3.00)


def test_estimate_cost_cached_cheaper():
    uncached = estimate_cost(
        model="claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=0,
        prices=None,
    )
    cached = estimate_cost(
        model="claude-sonnet-4-6",
        input_tokens=0,
        output_tokens=0,
        cached_tokens=1_000_000,
        prices=None,
    )
    assert cached < uncached


def test_price_cache_load_and_save(tmp_path):
    from aede.tokens import PriceCache
    cache_path = tmp_path / "model_prices.json"
    prices = {"claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3}}
    pc = PriceCache(cache_path)
    pc.save(prices)
    loaded = pc.load()
    assert loaded is not None
    assert "claude-sonnet-4-6" in loaded


# ---------------------------------------------------------------------------
# BC-06 — TokenTracker.record(role=) + DB schema migration
# ---------------------------------------------------------------------------

def test_token_record_with_role_column(tmp_home, tmp_path):
    """Inserting a token record with role='critic' must persist to DB with that role."""
    from aede.db import DB
    from aede.tokens import TokenTracker
    import sqlite3

    db_path = tmp_path / "test.db"
    # Create a dummy session first (foreign key)
    db = DB(db_path)
    db.insert_session(id="SID-TC", parent_id=None, title="test", model="claude-sonnet-4-6")

    tracker = TokenTracker(session_id="SID-TC", db=db)
    tracker.record(turn=1, input_tokens=500, output_tokens=200, cached_tokens=0, role="critic")

    # Query the DB directly to confirm role column is stored
    con = sqlite3.connect(str(db_path))
    row = con.execute("SELECT role FROM token_usage WHERE session_id='SID-TC'").fetchone()
    con.close()
    assert row is not None, "No token_usage row found"
    assert row[0] == "critic", f"Expected role='critic', got {row[0]!r}"


def test_critic_tokens_tracked(tmp_home, tmp_path):
    """Recording critic tokens with role='critic' and agent with role='agent' both work."""
    from aede.db import DB
    from aede.tokens import TokenTracker

    db_path = tmp_path / "test2.db"
    db = DB(db_path)
    db.insert_session(id="SID-TT", parent_id=None, title="test", model="m")

    tracker = TokenTracker(session_id="SID-TT", db=db)
    tracker.record(turn=1, input_tokens=100, output_tokens=50, cached_tokens=0)           # default role="agent"
    tracker.record(turn=1, input_tokens=500, output_tokens=200, cached_tokens=0, role="critic")

    totals = tracker.totals()
    assert totals["input_tokens"] == 600
    assert totals["output_tokens"] == 250


def test_totals_by_role(tmp_home, tmp_path):
    """totals_by_role() must return per-role sums correctly."""
    from aede.db import DB
    from aede.tokens import TokenTracker

    db_path = tmp_path / "test3.db"
    db = DB(db_path)
    db.insert_session(id="SID-TR", parent_id=None, title="test", model="m")

    tracker = TokenTracker(session_id="SID-TR", db=db)
    tracker.record(turn=1, input_tokens=100, output_tokens=50, cached_tokens=0)           # agent
    tracker.record(turn=2, input_tokens=200, output_tokens=80, cached_tokens=0)           # agent
    tracker.record(turn=1, input_tokens=500, output_tokens=200, cached_tokens=0, role="critic")

    by_role = tracker.totals_by_role()
    assert "agent" in by_role
    assert "critic" in by_role
    assert by_role["agent"]["input_tokens"] == 300
    assert by_role["agent"]["output_tokens"] == 130
    assert by_role["critic"]["input_tokens"] == 500
    assert by_role["critic"]["output_tokens"] == 200


def test_price_cache_stale_returns_none(tmp_path):
    import time
    from aede.tokens import PriceCache
    cache_path = tmp_path / "model_prices.json"
    pc = PriceCache(cache_path)
    data = {"prices": {}, "fetched_at": time.time() - 90000}
    cache_path.write_text(json.dumps(data))
    assert pc.load() is None
