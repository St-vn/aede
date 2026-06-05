import pytest
import json
from pathlib import Path
from jarvis.tokens import TokenTracker, FALLBACK_PRICES, estimate_cost


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
    assert "claude-sonnet-4-20250514" in FALLBACK_PRICES
    assert "input" in FALLBACK_PRICES["claude-sonnet-4-20250514"]
    assert "output" in FALLBACK_PRICES["claude-sonnet-4-20250514"]
    assert "cache_read" in FALLBACK_PRICES["claude-sonnet-4-20250514"]


def test_estimate_cost_known_model():
    cost = estimate_cost(
        model="claude-sonnet-4-20250514",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=0,
        prices=None,
    )
    assert cost == pytest.approx(3.00)


def test_estimate_cost_cached_cheaper():
    uncached = estimate_cost(
        model="claude-sonnet-4-20250514",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=0,
        prices=None,
    )
    cached = estimate_cost(
        model="claude-sonnet-4-20250514",
        input_tokens=0,
        output_tokens=0,
        cached_tokens=1_000_000,
        prices=None,
    )
    assert cached < uncached


def test_price_cache_load_and_save(tmp_path):
    from jarvis.tokens import PriceCache
    cache_path = tmp_path / "model_prices.json"
    prices = {"claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.3}}
    pc = PriceCache(cache_path)
    pc.save(prices)
    loaded = pc.load()
    assert loaded is not None
    assert "claude-sonnet-4-20250514" in loaded


def test_price_cache_stale_returns_none(tmp_path):
    import time
    from jarvis.tokens import PriceCache
    cache_path = tmp_path / "model_prices.json"
    pc = PriceCache(cache_path)
    data = {"prices": {}, "fetched_at": time.time() - 90000}
    cache_path.write_text(json.dumps(data))
    assert pc.load() is None
