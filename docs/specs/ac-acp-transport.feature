# ACP Transport Rewrite — Acceptance Criteria (Gherkin)
#
# Consolidated from: .claude/docs/acp-transport-rewrite-spec.md §4
# Source spec status: Spec (2026-06-10)
# Covers Must-have US-1..US-8. US-9/US-10 (Should-have) are in backlog.

Feature: Concurrent turns do not collide (US-1)

  Scenario: Two concurrent sessions get their own correct responses
    Given an agent subprocess connected with two active sessions A and B
    When session A and session B each send a prompt at the same time
    Then each prompt resolves with the response correlated to its own JSON-RPC id
    And neither response is dropped, duplicated, or swapped between sessions


Feature: Long turns complete without timeout (US-2)

  Scenario: Long-running prompt resolves when agent finishes
    Given a prompt that the agent will answer after a long delay
    When the prompt is in flight
    Then no transport-level timeout fires on session/prompt
    And the only resource held is one pending-future entry (no blocking thread)
    And the prompt resolves whenever the agent returns its stopReason


Feature: Live streaming reaches the UI (US-3)

  Scenario: Agent message chunks are forwarded in order
    Given a prompt in flight
    When the agent emits session/update notifications with agent_message_chunk text
    Then each chunk is routed to the originating session by params.sessionId
    And forwarded to the WebSocket as a text_delta event in arrival order
    And the final response carries the accumulated text and stopReason


Feature: Backend stays healthy under load (US-4)

  Scenario: Thread pool is not used for ACP I/O
    Given many turns have been run, including some abandoned while pending
    When a new turn is started
    Then it connects and prompts without queueing behind dead threads
    And no ThreadPoolExecutor is used for ACP request I/O

  Scenario: Abandoned pending turns do not grow thread count
    Given 20 turns have been started and abandoned while pending
    When a new turn is started
    Then the number of live threads has not grown by more than a small constant
    And the new turn completes normally


Feature: Turn cancellation (US-5)

  Scenario: User cancel resolves the turn cleanly
    Given a prompt in flight for session S
    When the user cancels the turn
    Then the client sends a session/cancel notification for S
    And any pending session/request_permission owed to the agent is answered "cancelled"
    And the session/prompt future resolves with stopReason=cancelled
    And no thread is killed and no future is abandoned


Feature: Reentrant agent requests are answered mid-turn (US-6)

  Scenario: Agent fs/read_text_file request answered while prompt is pending
    Given a prompt is in flight (its future not yet resolved)
    When the agent sends a fs/read_text_file request
    Then the reader loop dispatches it to the client handler and replies
    And the original prompt future remains pending and later resolves normally

  Scenario: Agent session/request_permission answered while prompt is pending
    Given a prompt is in flight
    When the agent sends a session/request_permission request
    Then the client handler answers the permission request
    And the original prompt future remains pending and later resolves normally


Feature: Sub-models and subscription auth (US-7)

  Scenario: Model override injected at spawn for sub-model selection
    Given the user selects model "claude-code/opus-4-8"
    When the agent connects
    Then the base agent "claude-code" is used
    And model_override "claude-opus-4-8" is injected as ANTHROPIC_MODEL at spawn
    And if a subscription/logged-in auth exists no API key is required

  Scenario: Switching sub-model respawns with new env
    Given an agent session using "claude-code/sonnet-4-5"
    When the user switches to "claude-code/opus-4-8"
    Then the subprocess is respawned with the updated ANTHROPIC_MODEL env var


Feature: WebSocket disconnect cleans up (US-8)

  Scenario: WebSocket disconnect cancels the turn and cleans up
    Given a turn is in flight over a WebSocket
    When the WebSocket disconnects
    Then the server cancels the turn task
    And the ACP client fails/cleans pending futures for that turn
    And reader/writer tasks and the subprocess are not leaked
