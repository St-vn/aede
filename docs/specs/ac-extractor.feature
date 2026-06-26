# Trace Extractor — Acceptance Criteria (Gherkin)
#
# Consolidated from: .claude/docs/phase2/phase2-spec-trace-extractor.md §2
# Source spec status: Draft (2026-06-10)
# US-01..US-07 scenarios

Feature: Extract a learning from a failure-fix loop (US-01)

  Scenario: Non-transient error followed by successful fix yields a learning
    Given a completed trace with 6 tool calls
    And step 3 is a tool_call whose tool_result status is "error" with a non-transient message
    And a later step performs a corrected call that succeeds
    When TraceExtractor.extract(trace) runs
    Then at least one learning record is produced
    And it has non-empty attempt, failure_signal, critique, prescriptive_rule
    And its source == "auto_learned"
    And its provenance.session_tool_call_count == 6

  Scenario: Transient errors do not produce learnings
    Given a completed trace whose only error is a 429 rate-limit on one tool call
    When TraceExtractor.extract(trace) runs
    Then no learning is produced (transient signals are filtered)


Feature: Trigger gate skips trivial sessions (US-02)

  Scenario: Too few tool calls skips extraction
    Given a completed trace with 3 tool calls and one error-fix loop
    When the trigger gate is evaluated
    Then extraction is skipped (below the 5-tool-call threshold)

  Scenario: No failure-fix loop skips extraction
    Given a completed trace with 8 tool calls and zero errors
    When the trigger gate is evaluated
    Then extraction is skipped (no failure signal)

  Scenario: Explicit override bypasses the gate
    Given a completed trace with 3 tool calls
    When extraction runs with force=True
    Then the gate is bypassed and an extraction pass is attempted


Feature: Confidence and non-triviality gating at write time (US-03)

  Scenario: Low-confidence learning is rejected
    Given the extractor returns a candidate with confidence 0.4
    When it is gated
    Then it is not written to the store

  Scenario: Transient failure_signal is rejected even at high confidence
    Given a candidate with confidence 0.9 and failure_signal "connection timeout after 30s"
    When it is gated
    Then it is rejected (matches a transient pattern)

  Scenario: Clean candidate is written with provenance
    Given a candidate with confidence 0.8 and a non-transient failure_signal
    When it is gated and written
    Then a learning row exists with source "auto_learned" and trusted False
    And provenance fields (model_id, extraction_model_id, session_tool_call_count) are populated


Feature: Admissibility check against existing rules (US-04)

  Scenario: Contradicting rule is flagged inadmissible
    Given the store already has a trusted learning "Always use write_file for edits"
    And a new candidate prescriptive_rule "Never use write_file; always use create_file"
    When admissibility is checked
    Then the new candidate is flagged inadmissible (or carries conflicting_rule_ids)
    And it is not auto-trusted

  Scenario: Non-conflicting rule passes admissibility
    Given a new candidate that does not contradict any existing trusted rule
    When admissibility is checked
    Then it passes admissibility


Feature: Verification gates trust (US-05)

  Scenario: Code learning verified by passing tests becomes trusted
    Given a gated, admissible candidate of type "config-correction"
    And the injected test_runner returns True
    When the Verifier runs on it
    Then the learning's verifier_outcome == "pass" and trusted == True

  Scenario: Failed verification keeps learning untrusted
    Given the injected test_runner returns False
    When the Verifier runs
    Then verifier_outcome == "fail" and trusted == False
    And the learning remains stored but is not retrieved into prompts (trusted_only)


Feature: GEPA-compatible trace scoring instrumentation (US-06)

  Scenario: Tool call succeeding on first try scores 1.0
    Given a tool call that succeeds on the first try
    When it is logged
    Then its trace record has score 1.0 and passed True

  Scenario: Retry-then-succeed scores partial
    Given a tool call that errored once then succeeded on retry
    When the loop is logged
    Then the retried-then-succeeded outcome has score 0.5

  Scenario: Outright failure scores zero
    Given a tool call that errored and was never corrected
    When it is logged
    Then score 0.0 and passed False


Feature: Extractor runs on session end and via manual command (US-07)

  Scenario: Auto-run on /exit when trigger gate passes
    Given a session that meets the trigger gate (>=5 tool calls, >=1 failure-fix loop)
    When the session ends via /exit
    Then the extractor runs (non-blocking) and any learnings are written

  Scenario: Manual extraction of a past session
    Given a stored session id
    When the user runs "/extract <session_id>"
    Then the extractor loads that session's rollout, normalizes it, and runs
    And prints a summary of learnings produced and skipped
