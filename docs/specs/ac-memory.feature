# Memory System — Acceptance Criteria (Gherkin)
#
# Consolidated from: .claude/docs/phase2/phase2-spec-memory-system.md §4
# Source spec status: Specification · ready for implementation planning (2026-06-06)
# Stories: MEM-01..MEM-13

Feature: messages_fts populated on write (MEM-01)

  Scenario: FTS index contains message after insert
    Given an in-memory DB initialised via DB(path)
    And a session row inserted with id "sess-001"
    When a message with content "xyzzy_unique_token" is inserted via insert_message
    Then querying messages_fts WHERE messages_fts MATCH 'xyzzy_unique_token' returns exactly 1 row

  Scenario: FTS index removes entry after delete
    Given a message row exists with content "delete_me_token"
    When the message row is deleted
    Then querying messages_fts WHERE messages_fts MATCH 'delete_me_token' returns 0 rows

  Scenario: FTS index reflects update
    Given a message row exists with content "before_update"
    When the content is updated to "after_update"
    Then MATCH 'before_update' returns 0 rows
    And MATCH 'after_update' returns 1 row

  Scenario: Backfill on DB open
    Given an existing DB file with un-indexed messages (no triggers were present)
    When a new DB instance is opened on that file
    Then all pre-existing messages are discoverable via MATCH queries


Feature: session_search returns contextual message content (MEM-02)

  Scenario: Basic search returns matches with context window
    Given messages exist in session "sess-001" with one containing "pytest conftest"
    When the model calls session_search with query "pytest conftest"
    Then the result contains the matching message content
    And the result contains up to 5 messages before the match
    And the result contains up to 5 messages after the match
    And the result contains the session's first message (bookend)
    And the result contains the session's last message (bookend)
    And the result includes session_id, title, and created_at metadata

  Scenario: No matches returns empty result not error
    Given no messages contain "zzz_no_match_xyz"
    When the model calls session_search with query "zzz_no_match_xyz"
    Then the result is an empty list
    And no exception is raised

  Scenario: Tool error is returned as result not exception
    Given the FTS index is unavailable (DB locked)
    When the model calls session_search
    Then a ToolResult with status="error" is returned
    And the agent loop continues normally

  Scenario: session_search does not require approval
    Given session_search is registered in ToolRouter
    Then requires_approval("session_search") returns False


Feature: Learnings written to JSONL in critique-then-fix format (MEM-03)

  Scenario: Valid learning is appended to JSONL file
    Given the learnings file exists at ~/.aede/data/learnings.jsonl
    When write_learning is called with type="anti-pattern" and content fields (attempt, failure_signal, critique, rule)
    Then a new line is appended to the file
    And the line is valid JSON
    And all required fields (id, type, content, created_at, source, trusted, source_session_id) are present

  Scenario: JSONL file is created if absent
    Given the learnings file does not exist
    When write_learning is called
    Then the file is created and contains the new entry

  Scenario: Crash during write does not corrupt existing entries
    Given the learnings file has 5 existing entries
    When the process is killed mid-write (simulated by truncation test)
    Then all 5 prior entries remain parseable
    And at most 1 entry (the in-progress one) is malformed

  Scenario: Unknown learning type is rejected
    When write_learning is called with type="unknown_type"
    Then a ValueError is raised before writing


Feature: Each learning carries full provenance (MEM-04)

  Scenario: Auto-learned entry defaults to trusted=false
    When write_learning is called with source="auto_learned"
    Then the written entry has trusted=false

  Scenario: User-sourced entry defaults to trusted=false until verified
    When write_learning is called with source="user"
    Then the written entry has trusted=false
    And verifier_outcome is null

  Scenario: Verifier outcome is stored with learning
    Given a learning exists with id "learn-001"
    When the verifier runs and records outcome="pass"
    Then the learning is updated with verifier_outcome="pass" and trusted=true


Feature: Ollama embedding client returns 768-dim vectors (MEM-05)

  Scenario: Successful embedding call
    Given Ollama is running at localhost:11434
    When embed_text("some text") is called
    Then a list of 768 floats is returned
    And all values are finite (no NaN or Inf)

  Scenario: Unavailable Ollama raises OllamaUnavailable
    Given Ollama is not reachable (connection refused)
    When embed_text("any text") is called
    Then OllamaUnavailable is raised (not ConnectionError or requests.exceptions)

  Scenario: Timeout triggers OllamaUnavailable
    Given Ollama takes longer than 5 seconds to respond
    When embed_text is called
    Then OllamaUnavailable is raised within 5.5 seconds


Feature: aede degrades to FTS5 retrieval when Ollama is unavailable (MEM-06)

  Scenario: aede starts normally without Ollama
    Given Ollama is not running
    When "uv run aede" is executed
    Then the agent starts without error
    And no crash or exception surfaces to the user

  Scenario: Retrieval falls back to FTS5 when Ollama is down
    Given Ollama is not reachable
    And learnings exist in the store
    When pre-task retrieval is triggered
    Then FTS5 keyword retrieval is used
    And a console warning "Ollama unavailable — using keyword-only retrieval" is printed

  Scenario: Embedding write is skipped gracefully when Ollama is down
    Given Ollama is not reachable
    When write_learning is called
    Then the learning is written to JSONL without an embedding
    And embedding column is null in the DB row


Feature: Embeddings stored as BLOB and round-tripped accurately (MEM-07)

  Scenario: Embedding round-trip preserves vector
    Given a 768-dim float vector v
    When v is packed via struct.pack and stored as BLOB
    And retrieved and unpacked via struct.unpack
    Then cosine_similarity(v, unpacked) > 0.9999

  Scenario: Learning without embedding has null BLOB
    Given a learning was written without Ollama available
    Then its embedding column is NULL in the learnings DB table
    And it can still be retrieved via FTS5


Feature: Top-k cosine retrieval returns correct nearest neighbours (MEM-08)

  Scenario: Known nearest neighbour is ranked first
    Given a corpus of 100 learnings with known embeddings
    And learning "target" is most similar to query Q
    When top_k_cosine(Q, k=5) is called
    Then "target" is the first result

  Scenario: k=5 returns at most available results
    Given fewer than 3 learnings have embeddings
    When top_k_cosine(Q, k=5) is called
    Then at most 3 results are returned (no padding)

  Scenario: Only trusted learnings are returned by default
    Given a mix of trusted and untrusted learnings
    When top_k_cosine is called with trusted_only=True (default)
    Then all results have trusted=true


Feature: Hybrid FTS5+cosine retrieval combines both signal types (MEM-09)

  Scenario: Semantic-only match is returned
    Given a learning whose content does not share keywords with query Q
    But whose embedding is semantically close to Q
    When retrieve(Q, k=5) is called
    Then the learning appears in results

  Scenario: Keyword-only match is returned
    Given a learning whose content contains exact keywords from query Q
    But whose embedding has low cosine similarity to Q
    When retrieve(Q, k=5) is called
    Then the learning appears in results

  Scenario: Hybrid score ranks better matches higher
    Given learning A has high cosine similarity and low FTS rank
    And learning B has high FTS rank and low cosine similarity
    And learning C has both high cosine and high FTS rank
    When retrieve is called
    Then C ranks above A and B


Feature: Relevant trusted learnings injected into system-prompt suffix (MEM-10)

  Scenario: Learnings section appears in system prompt when learnings exist
    Given 3 trusted learnings are relevant to the current session task
    When build_system_prompt is called with learnings injected
    Then the returned string contains "## Lessons from Prior Runs"
    And the section appears after the "## Session" block
    And all 3 learnings appear in the section

  Scenario: Section is absent when no trusted learnings exist
    Given the learnings store has no trusted entries
    When build_system_prompt is called
    Then the returned string does not contain "## Lessons from Prior Runs"

  Scenario: Injected learnings respect token budget cap
    Given 20 trusted learnings exist totalling 10,000 tokens
    When build_system_prompt is called
    Then at most max_learnings_tokens worth of learnings are injected
    And the most relevant (by retrieval score) are preferred

  Scenario: Only trusted learnings are injected
    Given 2 trusted and 5 untrusted learnings exist
    When pre-task injection runs
    Then only the 2 trusted learnings appear in the suffix


Feature: Independent verifier gates trust before marking learning trusted (MEM-11)

  Scenario: Code learning verified by test suite outcome
    Given a proposed learning with type="anti-pattern" relating to a code pattern
    And a test suite is available and passes
    When the verifier runs
    Then verifier_outcome="pass" and trusted=true are set

  Scenario: Code learning fails verification
    Given a proposed learning about a code pattern
    When the verifier runs and the test suite fails
    Then verifier_outcome="fail" and trusted=false remain

  Scenario: Non-code learning gets lower-trust LLM-turn verification
    Given a proposed learning with type="root-cause" about a non-code task
    When the verifier runs a separate LLM coherence check
    Then verifier_outcome is "llm_coherence_pass" or "llm_coherence_fail"
    And trusted is set to true only on pass
    And a lower_trust flag is set to true on the learning record

  Scenario: Verifier is not the proposing agent
    Given the agent just proposed a learning
    When the verifier runs
    Then it executes as a separate subprocess or separate API turn
    And the agent's own output is not used as the verification signal


Feature: Each agent turn emits a GEPA-compatible trace (MEM-12)

  Scenario: Trace written for a turn with tool calls
    Given an agent turn with 2 tool calls
    When the turn completes
    Then a trace record is written to ~/.aede/data/traces/<session_id>.jsonl
    And the record contains: session_id, turn_number, timestamp, input_tokens, output_tokens, cached_tokens, tool_calls, reasoning_text, outcome

  Scenario: Trace queryable by session_id
    Given traces from 3 different sessions
    When querying traces by session_id="sess-002"
    Then only traces from session "sess-002" are returned

  Scenario: Trace file is append-only; crash does not corrupt prior entries
    Given 10 traces have been written
    When the process crashes during the 11th write
    Then the first 10 traces remain parseable

  Scenario: Trace writing does not crash agent on error
    Given the trace file is not writable (permissions error)
    When the agent loop runs
    Then the agent continues normally
    And a warning is logged


Feature: Operator can manage learnings via CLI (MEM-13)

  Scenario: List all learnings
    Given 5 learnings exist in the store
    When "aede memory list" is run
    Then 5 rows are printed with id, type, trusted, created_at, and content preview

  Scenario: Show full learning detail
    Given a learning with id "abc123"
    When "aede memory show abc123" is run
    Then the full record is printed in human-readable format

  Scenario: Delete a learning
    Given a learning with id "abc123"
    When "aede memory delete abc123" is run
    Then the learning is removed from the store
    And "aede memory list" no longer shows it

  Scenario: Edit a learning opens $EDITOR
    Given a learning with id "abc123"
    When "aede memory edit abc123" is run
    Then the learning JSON is written to a temp file
    And $EDITOR is opened on that file
    And on save the updated content is written back
    And the record is validated before save (rejects invalid type values)
