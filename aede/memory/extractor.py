"""
TraceExtractor — post-task pass that mines completed traces for typed learnings.

The extractor normalises a completed trace, identifies non-trivial
failure → fix → outcome loops, and emits critique-then-fix learning records
through the existing LearningsStore + Verifier pipeline.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Transient error patterns that should not produce learnings.
_TRANSIENT_PATTERNS: tuple[str, ...] = (
    "429", "500", "502", "503",
    "dns", "timeout", "timed out",
    "connection refused", "connection reset",
    "rate limit", "rate_limit",
)


@dataclass
class TraceStep:
    index: int
    tool_name: str
    inputs: dict[str, Any]
    output: str
    status: str
    score: float


@dataclass
class Trace:
    session_id: str
    task_description: str
    steps: list[TraceStep] = field(default_factory=list)
    final_outcome: str = "unknown"
    tool_call_count: int = 0


# ---------------------------------------------------------------------------
# Rollout normalisation
# ---------------------------------------------------------------------------

def _load_rollout(path: Path) -> list[dict[str, Any]]:
    """Load all records from a rollout JSONL file."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def _extract_task_description(records: list[dict[str, Any]]) -> str:
    """Return the first user_message content, or 'unknown task'."""
    for r in records:
        if r.get("type") == "user_message":
            text = (r.get("content") or "").strip()
            if text:
                return text[:500]
    return "unknown task"


def _is_transient(message: str) -> bool:
    """Return True if *message* matches a known-transient error pattern."""
    lower = message.lower()
    return any(re.search(p, lower) for p in _TRANSIENT_PATTERNS)


def normalize_rollout(records: list[dict[str, Any]]) -> Trace:
    """Convert aede rollout JSONL records into a normalised ``Trace``.

    Pairs ``tool_call`` / ``tool_result`` records by ``call_id`` and assigns
    GEPA-compatible scores (1.0 clean / 0.5 retry-then-success / 0.0 fail).
    """
    session_id = ""
    for r in records:
        sid = r.get("session_id", "")
        if sid:
            session_id = sid
            break

    task_description = _extract_task_description(records)

    # Pair tool calls with their results by call_id
    call_map: dict[str, dict[str, Any]] = {}
    for r in records:
        if r.get("type") == "tool_call":
            cid = r.get("call_id", "")
            if cid:
                call_map.setdefault(cid, {}).update(r)
        elif r.get("type") == "tool_result":
            cid = r.get("call_id", "")
            if cid:
                call_map.setdefault(cid, {}).update(r)

    # Build steps from paired records, tracking retries
    steps: list[TraceStep] = []
    retry_keys: dict[str, int] = {}
    final_outcome = "unknown"

    for r in records:
        if r.get("type") == "session_end":
            status = r.get("status", "")
            final_outcome = "success" if status == "archived" else "failure"
            continue

    # Process paired calls in insertion order (use ordered list of call_ids)
    seen_call_ids: list[str] = []
    for r in records:
        if r.get("type") == "tool_call":
            cid = r.get("call_id", "")
            if cid and cid not in seen_call_ids:
                seen_call_ids.append(cid)

    for idx, cid in enumerate(seen_call_ids):
        paired = call_map.get(cid)
        if not paired:
            continue

        tool_name = paired.get("name", paired.get("tool_name", "?"))
        tool_input = paired.get("args") or paired.get("input") or {}
        result_text = paired.get("result", paired.get("output", ""))
        call_status = paired.get("status", "approved")

        if isinstance(tool_input, str):
            try:
                tool_input = json.loads(tool_input)
            except (json.JSONDecodeError, TypeError):
                tool_input = {"raw": tool_input}

        result_output = str(result_text) if result_text is not None else ""
        truncated = result_output[:2000]

        call_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        was_retry = call_key in retry_keys

        if call_status == "error":
            score = 0.0
            retry_keys[call_key] = retry_keys.get(call_key, 0) + 1
        elif was_retry:
            score = 0.5
            retry_keys.pop(call_key, None)
        else:
            score = 1.0

        steps.append(TraceStep(
            index=idx,
            tool_name=tool_name,
            inputs=tool_input,
            output=truncated,
            status=call_status,
            score=score,
        ))

    return Trace(
        session_id=session_id,
        task_description=task_description,
        steps=steps,
        final_outcome=final_outcome,
        tool_call_count=len(steps),
    )


# ---------------------------------------------------------------------------
# Trigger gate
# ---------------------------------------------------------------------------

def _has_non_transient_failure_fix(steps: list[TraceStep]) -> bool:
    """Return True if there is at least one non-transient error followed by a later success."""
    for i, step in enumerate(steps):
        if step.status == "error" and step.score == 0.0:
            if _is_transient(step.output):
                continue
            # Check if a later step (same or different tool) succeeds
            for j in range(i + 1, len(steps)):
                if steps[j].score >= 0.5 and steps[j].tool_name == step.tool_name:
                    return True
                if steps[j].score >= 0.5:
                    return True
    return False


def should_extract(trace: Trace, *, force: bool = False) -> bool:
    """Determine whether extraction should run for *trace*.

    Trigger gate (all required unless *force*):
      1. ≥ 5 tool calls
      2. ≥ 1 non-transient failure → fix loop
    """
    if force:
        return True
    if trace.tool_call_count < 5:
        return False
    if not _has_non_transient_failure_fix(trace.steps):
        return False
    return True


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """\
You are a trace-mining assistant.  Your job is to analyse a completed agent
session trace and extract reusable learnings from any failure-to-fix loops you
find.

A failure-to-fix loop is:
1. A tool call that failed with a non-transient error
2. One or more subsequent tool calls that corrected the situation and succeeded

For each loop you identify, produce a critique-then-fix learning record with:
- attempt: what the agent tried that failed (1-2 sentences)
- failure_signal: the actual error message or symptom
- critique: why the initial approach was wrong (1-2 sentences)
- prescriptive_rule: what the agent should do instead in the future (1-2 sentences, actionable)
- confidence: float 0.0-1.0

Rules:
- Skip transient errors (rate limits, timeouts, DNS failures)
- Skip one-off typos that don't generalise
- Skip errors that were not actually fixed
- Max 3 records per trace
- Output ONLY a JSON array of objects, nothing else
"""


def _format_trace_for_prompt(trace: Trace) -> str:
    """Format a Trace into a compact text representation for the LLM prompt."""
    lines = [f"Task: {trace.task_description}", ""]
    for step in trace.steps:
        status_mark = "✓" if step.score >= 0.5 else "✗"
        retry_mark = " (retry)" if step.score == 0.5 else ""
        lines.append(f"  {step.index}. {status_mark} {step.tool_name}{retry_mark}")
        if step.score == 0.0:
            lines.append(f"     Error: {step.output[:200]}")
    lines.append(f"\nOutcome: {trace.final_outcome}")
    return "\n".join(lines)


class TraceExtractor:
    """Post-task extractor that mines completed traces for typed learnings.

    Args:
        llm: An injectable LLM client with a ``messages.create(...)`` method.
            When ``None``, a real ``anthropic.Anthropic`` client is constructed
            lazily (requires ``ANTHROPIC_API_KEY``).
        model: Model name to use for extraction.  Defaults to ``claude-haiku-4-5``
            (cheap, fast — asymmetric extraction per locked decision).
    """

    def __init__(self, llm: Any | None = None, model: str = "claude-haiku-4-5") -> None:
        self._llm: Any | None = llm
        self._model: str = model

    def _get_llm(self) -> Any:
        if self._llm is not None:
            return self._llm
        import anthropic
        return anthropic.Anthropic()

    def extract(self, trace: Trace, *, force: bool = False) -> list[dict[str, Any]]:
        """Run the extraction pass over *trace*.

        Args:
            trace: Normalised ``Trace`` from ``normalize_rollout``.
            force: Bypass the trigger gate when ``True``.

        Returns:
            A list of critique-then-fix learning dicts (max 3).  Each dict
            has keys: ``attempt``, ``failure_signal``, ``critique``,
            ``prescriptive_rule``, ``confidence``, ``tool_calls_involved``.
            Returns an empty list if nothing to extract.
        """
        if not should_extract(trace, force=force):
            return []

        prompt = _format_trace_for_prompt(trace)
        client = self._get_llm()

        response = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        reply_text: str = response.content[0].text if response.content else ""
        if not reply_text.strip():
            return []

        # Parse JSON array from the response
        try:
            learnings = json.loads(reply_text)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Try to extract a JSON array from markdown code fence
            import re as _re
            m = _re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", reply_text)
            if m:
                try:
                    learnings = json.loads(m.group(1))
                except (json.JSONDecodeError, TypeError, ValueError):
                    return []
            else:
                return []

        if not isinstance(learnings, list):
            return []

        # Validate and normalise each learning
        validated: list[dict[str, Any]] = []
        for item in learnings[:3]:
            if not isinstance(item, dict):
                continue
            required = ("attempt", "failure_signal", "critique", "prescriptive_rule")
            if all(k in item for k in required):
                item.setdefault("confidence", 0.5)
                item.setdefault("tool_calls_involved", [])
                validated.append(item)

        return validated


# ---------------------------------------------------------------------------
# Write-time gating pipeline
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    written: bool = False
    trusted: bool = False
    reason: str = ""
    record: dict[str, Any] | None = None


def gate_candidate(
    candidate: dict[str, Any],
    existing_rules: list[dict[str, Any]],
    verifier: Any,
    store: Any,
    admissibility_llm: Any | None = None,
    model_id: str = "",
    extraction_model_id: str = "",
) -> GateResult:
    """Run the full write-time gating pipeline on *candidate*.

    Pipeline order:
      1. Confidence gate (reject < 0.6)
      2. Non-triviality gate (reject transient failure signals)
      3. Admissibility gate (reject contradictions with existing trusted rules)
      4. Write to store (trusted=False)
      5. Verifier gate (code or LLM coherence path) → set trusted
    """
    # --- 1. Confidence gate ---
    confidence = candidate.get("confidence", 0.0)
    if confidence < 0.6:
        return GateResult(reason=f"confidence ({confidence})")

    # --- 2. Non-triviality gate ---
    failure_signal = candidate.get("failure_signal", "")
    if _is_transient(failure_signal):
        return GateResult(reason=f"transient ({failure_signal[:100]})")

    # --- 3. Admissibility gate ---
    from aede.memory.admissibility import check_admissibility
    admissibility = check_admissibility(candidate, existing_rules, llm=admissibility_llm)
    if not admissibility.admissible:
        return GateResult(
            reason=f"admissibility: {admissibility.reason}",
        )

    # --- 4. Write to store ---
    prescriptive_rule = candidate.get("prescriptive_rule", "")
    provenance: dict[str, Any] = {
        "source": "auto_learned",
        "model_id": model_id,
        "extraction_model_id": extraction_model_id,
        "session_tool_call_count": candidate.get("provenance", {}).get("session_tool_call_count", 0),
    }

    record = store.write_learning(
        type="config-correction",
        content=prescriptive_rule,
        source="auto_learned",
        source_session_id=candidate.get("provenance", {}).get("source_session_id", ""),
        trusted=False,
        lower_trust=True,
        verifier_outcome=None,
        provenance=provenance,
        importance_count=2,
        conflicting_rule_ids=admissibility.conflicting_rule_ids,
    )

    # --- 5. Verifier gate ---
    # Non-code learnings always go through LLM coherence verification
    try:
        verdict = verifier.run_llm_verify({"content": prescriptive_rule})
        trusted = bool(verdict.get("trusted", False))
        verifier_outcome = verdict.get("verifier_outcome", None)
    except Exception:
        trusted = False
        verifier_outcome = "error"

    # Update the stored record
    record["trusted"] = trusted
    record["verifier_outcome"] = verifier_outcome
    store.update(record["id"], record)

    return GateResult(
        written=True,
        trusted=trusted,
        reason="passed all gates",
        record=record,
    )


# ---------------------------------------------------------------------------
# Deferred extraction queue
# ---------------------------------------------------------------------------

class ExtractionQueue:
    """Lightweight marker queue for deferred post-session extraction.

    At session end, a marker ``{session_id, timestamp}`` is appended to
    ``pending_extractions.jsonl``.  On the next startup, the queue is drained
    and each marker is processed.  This avoids running the LLM extractor during
    shutdown (which races DB + interpreter teardown).
    """

    def __init__(self, data_dir: Path) -> None:
        self._path: Path = data_dir / "pending_extractions.jsonl"

    def enqueue(self, session_id: str) -> None:
        """Append a pending-extraction marker for *session_id*."""
        record = json.dumps({"session_id": session_id, "ts": time.time()})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(record + "\n")

    def pending(self) -> list[str]:
        """Return all currently pending session IDs."""
        if not self._path.exists():
            return []
        ids: list[str] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    sid = data.get("session_id", "")
                    if sid:
                        ids.append(sid)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
        return ids

    def clear(self) -> None:
        """Remove the queue file (all markers processed)."""
        if self._path.exists():
            self._path.unlink()

    def process_all(
        self,
        data_dir: Path,
        store: Any,
        verifier: Any,
        admissibility_llm: Any | None = None,
        model_id: str = "",
        extraction_model_id: str = "",
        console: Any | None = None,
    ) -> list[GateResult]:
        """Process every pending extraction marker.

        For each session ID, loads the rollout JSONL, normalises it, runs the
        extractor, and gates each candidate.  Removes the queue file on
        completion so failed markers are retried on next startup.

        Returns a list of ``GateResult`` objects for all processed candidates.
        """
        results: list[GateResult] = []
        session_ids = self.pending()
        if not session_ids:
            return results

        extractor = TraceExtractor(llm=admissibility_llm, model=extraction_model_id)
        from aede.memory.store import LearningsStore
        from aede.memory.verifier import Verifier
        from aede.memory.retrieval import hybrid_retrieve

        resolved_store = store or LearningsStore(data_dir)
        resolved_verifier = verifier or Verifier()

        for sid in session_ids:
            rollout_path = self._find_rollout(data_dir, sid)
            if rollout_path is None:
                continue

            records = _load_rollout(rollout_path)
            trace = normalize_rollout(records)
            candidates = extractor.extract(trace)

            for cand in candidates:
                if cand.get("provenance") is None:
                    cand["provenance"] = {}
                cand["provenance"]["source_session_id"] = sid

            # Fetch existing trusted rules for admissibility check
            try:
                existing = resolved_store.list_all() if hasattr(resolved_store, "list_all") else []
            except Exception:
                existing = []

            for cand in candidates:
                result = gate_candidate(
                    cand,
                    existing,
                    verifier=resolved_verifier,
                    store=resolved_store,
                    admissibility_llm=admissibility_llm,
                    model_id=model_id,
                    extraction_model_id=extraction_model_id,
                )
                results.append(result)

                if console:
                    status = "✓" if result.written else "✗"
                    trust = " (trusted)" if result.trusted else ""
                    console.print(f"  {status} {result.reason}{trust}")

        self.clear()
        return results

    @staticmethod
    def _find_rollout(data_dir: Path, session_id: str) -> Path | None:
        """Search for a rollout JSONL by session_id, scanning date directories."""
        sessions_dir = data_dir / "sessions"
        if not sessions_dir.exists():
            return None
        # Walk YYYY/MM/DD/ directories
        for year_dir in sorted(sessions_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                for day_dir in sorted(month_dir.iterdir()):
                    if not day_dir.is_dir():
                        continue
                    candidate = day_dir / f"rollout-{session_id}.jsonl"
                    if candidate.exists():
                        return candidate
        return None
