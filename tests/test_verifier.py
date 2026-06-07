import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_code_verify_passes_on_test_pass(tmp_path):
    """Verifier.run_code_verify sets verifier_outcome='pass', trusted=True on test pass."""
    from aede.memory.verifier import Verifier
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "def foo(): pass", LearningSource.USER, "s1")

    verifier = Verifier(store=store)
    result = await verifier.run_code_verify(store.read_all()[0])

    assert result["verifier_outcome"] == "pass"
    assert result["trusted"] is True


@pytest.mark.asyncio
async def test_llm_coherence_check_sets_lower_trust(tmp_path):
    """Verifier.run_llm_verify sets lower_trust=True on LLM coherence pass."""
    from aede.memory.verifier import Verifier
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ROOT_CAUSE, "Root cause was missing initialization", LearningSource.USER, "s1")

    verifier = Verifier(store=store)

    mock_provider = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"coherent": true, "reason": "makes sense"}'
    mock_provider.stream_turn = AsyncMock(return_value=mock_resp)

    with patch("aede.provider.get_provider", return_value=mock_provider), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        result = await verifier.run_llm_verify(store.read_all()[0])

    assert result["verifier_outcome"] == "llm_coherence_pass"
    assert result["trusted"] is True
    assert result["lower_trust"] is True


@pytest.mark.asyncio
async def test_verifier_updates_learning_trusted_flag(tmp_path):
    """Post-verify, learning record is updated with trusted/lower_trust/verifier_outcome."""
    from aede.memory.verifier import Verifier
    from aede.memory.store import LearningsStore, LearningType, LearningSource

    store = LearningsStore(tmp_path / "learnings.jsonl")
    store.write_learning(LearningType.ANTI_PATTERN, "def foo(): pass", LearningSource.USER, "s1")

    verifier = Verifier(store=store)
    learning = store.read_all()[0]
    result = await verifier.run_code_verify(learning)

    if result.get("trusted"):
        store.update(learning["id"], trusted=True, verifier_outcome=result["verifier_outcome"])

    updated = store.read_all()[0]
    assert updated["trusted"] is True
    assert updated["verifier_outcome"] == "pass"
