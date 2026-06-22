def test_reinjection_constant_exists():
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text()
    assert "REINJECTION_INTERVAL" in source
    assert "20000" in source


def test_reinjection_tracker_on_agent_loop():
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text()
    assert "tokens_since_last_reminder" in source
    assert "reinjection" in source.lower()
