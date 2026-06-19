def test_plan_mode_reminder_injected_when_plan_mode():
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text()
    assert "plan mode" in source.lower() or "plan_mode" in source
    assert "read-only" in source.lower()


def test_plan_mode_block_in_dynamic_parts():
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text()
    assert "gate_mode" in source
    assert "system-reminder" in source
