def test_baseline_stable_prompt_exists():
    import pathlib
    fixture = pathlib.Path("tests/fixtures/system_prompt_baseline/stable_prompt.txt")
    assert fixture.exists(), f"Baseline fixture missing: {fixture}"
    assert len(fixture.read_text()) > 100, "Baseline prompt too short (likely empty)"


def test_baseline_permission_modes_exists():
    import pathlib
    fixture = pathlib.Path("tests/fixtures/system_prompt_baseline/permission_modes.txt")
    assert fixture.exists(), f"Baseline fixture missing: {fixture}"
    assert len(fixture.read_text()) > 50, "Permission modes file too short (likely empty)"


def test_behavior_contract_has_all_sections():
    import pathlib
    sections = pathlib.Path("tests/fixtures/system_prompt_baseline/behavior_contract_sections.txt").read_text().strip().split("\n")
    prompt = pathlib.Path("tests/fixtures/system_prompt_baseline/stable_prompt.txt").read_text()
    for section in sections:
        assert section.strip() in prompt, f"Missing section: {section}"
