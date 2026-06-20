def test_provider_prompt_files_exist():
    import pathlib
    prompts_dir = pathlib.Path("aede/prompts")
    assert prompts_dir.exists()
    assert (prompts_dir / "anthropic.md").exists()
    assert (prompts_dir / "openai.md").exists()
    assert (prompts_dir / "deepseek.md").exists()
    assert (prompts_dir / "__init__.py").exists()

def test_get_provider_prompt_variant_exists():
    import pathlib
    source = pathlib.Path("aede/agent.py").read_text()
    assert "_get_provider_prompt_variant" in source


def test_deepseek_instruction_adherence_section():
    import pathlib
    content = pathlib.Path("aede/prompts/deepseek.md").read_text(encoding="utf-8")
    assert "Instruction Adherence" in content
    assert "hard switch" in content
