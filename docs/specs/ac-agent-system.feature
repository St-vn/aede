# Agent System (Skills / Agents / Subagents) — Acceptance Criteria (Gherkin)
#
# Consolidated from: .claude/docs/phase2/phase2-spec-agent-system.md §3
# Source spec status: Spec complete (2026-06-06)
# Phases A (SKILL.md), B (AGENT.md), C (Import), D (Subagent Orchestration)

# ============================================================
# Phase A — SKILL.md
# ============================================================

Feature: SKILL.md authoring and parsing (A-1)

  Scenario: Valid SKILL.md is parsed without error
    Given a file "SKILL.md" with valid YAML frontmatter containing "name" and "description"
    And a non-empty markdown body
    When aede parses the file via SkillDef.from_file()
    Then a SkillDef object is returned with name, description, and body populated
    And no exception is raised

  Scenario: Missing required field raises loud error at load time
    Given a SKILL.md missing the "name" field
    When aede attempts to load skills from the search path
    Then a SkillLoadError is raised naming the offending file and field
    And the process does not silently skip the file

  Scenario: Optional fields have safe defaults
    Given a SKILL.md with only "name" and "description" in frontmatter
    When parsed
    Then trigger_phrases defaults to []
    And allowed_tools defaults to None (= all tools)
    And model defaults to None (= inherit)


Feature: Skill search path loading with shadow rule (A-2)

  Scenario: Project-local skill shadows global skill of same name
    Given a global skill "summarize" at ~/.aede/skills/summarize/SKILL.md
    And a project-local skill "summarize" at .aede/skills/summarize/SKILL.md
    When skills are loaded
    Then only the project-local "summarize" is in the registry
    And the global "summarize" is not loaded

  Scenario: Non-conflicting global and local skills both load
    Given a global skill "web-researcher"
    And a project-local skill "code-reviewer"
    When skills are loaded
    Then both skills are in the registry

  Scenario: Missing search path directory is not an error
    Given ~/.aede/skills/ does not exist
    When skills are loaded
    Then no exception is raised
    And the registry is empty

  Scenario: Malformed SKILL.md emits warning and is skipped
    Given a SKILL.md with invalid YAML frontmatter
    When skills are loaded
    Then a warning is printed naming the file
    And other valid skills in the same path continue to load


Feature: Skill injection into system prompt (A-3)

  Scenario: Skills are injected in suffix not prefix
    Given a loaded skill "code-reviewer" with a 200-token body
    When build_system_prompt() is called with skills=["code-reviewer"]
    Then the returned prompt string contains "## Agent Skills"
    And the section appears after "## Session" (the last stable suffix section)
    And STABLE_SYSTEM_PROMPT is unchanged

  Scenario: No skills = no section injected
    Given no active skills
    When build_system_prompt() is called
    Then the prompt contains no "## Agent Skills" section

  Scenario: Skill body exceeding token budget triggers warning
    Given a skill with body exceeding 2000 tokens (approx 8000 chars)
    When skills are loaded
    Then a warning is printed about the large skill body
    And the skill is still loaded and injected (warn, not reject)


Feature: /skills listing command (A-4)

  Scenario: /skills prints a compact table
    Given skills "web-researcher" (global) and "code-reviewer" (project) are loaded
    When the user types "/skills"
    Then a table is printed with columns: Name, Description (truncated at 60 chars), Source (global or project)
    And no exception is raised

  Scenario: No skills loaded produces a message
    Given the skill registry is empty
    When the user types "/skills"
    Then a message "No skills loaded." is printed


# ============================================================
# Phase B — AGENT.md
# ============================================================

Feature: AGENT.md authoring and parsing (B-1)

  Scenario: Valid AGENT.md parses without error
    Given a file "researcher.md" with "name" and "description" in frontmatter
    And a non-empty body
    When AgentDef.from_file() is called
    Then an AgentDef object is returned with name, description, and body populated

  Scenario: Missing required "name" field raises loud error
    Given an AGENT.md missing "name"
    When aede loads agents
    Then an AgentLoadError is raised naming the file and field

  Scenario: Optional fields have safe defaults
    Given an AGENT.md with only "name" and "description"
    When parsed
    Then model equals "inherit"
    And skills equals []
    And tools equals None (no restriction)
    And disallowedTools equals []
    And maxTurns equals 20


Feature: Agent definition validation at load time (B-2)

  Scenario: Agent declaring unknown skill fails loud
    Given an AGENT.md declaring skills: ["nonexistent-skill"]
    When the agent is loaded and validated
    Then an AgentLoadError is raised referencing "nonexistent-skill"
    And the agent is not added to the agent registry

  Scenario: Agent declaring unknown tool fails loud
    Given an AGENT.md declaring tools: ["nonexistent_tool"]
    When the agent is loaded and validated
    Then an AgentLoadError is raised referencing "nonexistent_tool"

  Scenario: Valid agent with all fields resolving loads successfully
    Given an AGENT.md with skills: ["code-reviewer"] and tools: ["read_file", "search_files"]
    And "code-reviewer" is in the skill registry
    And "read_file" and "search_files" are in the ToolRouter
    When the agent is loaded
    Then it enters the agent registry without error

  Scenario: /agents listing shows table
    Given agents "researcher" and "coder" are loaded
    When the user types "/agents"
    Then a table is printed with columns: Name, Description (truncated 60 chars), Model, Source (global or project)


# ============================================================
# Phase C — Import
# ============================================================

Feature: Claude Code agent import (C-1)

  Scenario: 1:1 fields are mapped exactly
    Given a Claude Code agent file with name, description, model, tools, disallowedTools, maxTurns, skills, and body
    When "aede import <file>" is run
    Then the output AGENT.md contains all 1:1-mapped fields with identical values
    And the body is preserved verbatim

  Scenario: Unsupported fields are annotated not silently dropped
    Given a Claude Code agent file with fields: permissionMode, mcpServers, memory, isolation, hooks
    When imported
    Then the output AGENT.md contains a YAML comment block listing each unsupported field and its original value
    And none of the unsupported fields are silently lost

  Scenario: Import report is printed to console
    Given any Claude Code agent file
    When imported
    Then the console shows the count of fields mapped, fields annotated (unsupported), and output path

  Scenario: Import does not overwrite without confirmation
    Given an existing .aede/agents/researcher.md
    When "aede import researcher.md" would produce the same output path
    Then the user is prompted to confirm overwrite
    And the file is only overwritten on "y"

  Scenario: Import of non-existent file fails with clear error
    Given a path that does not exist
    When "aede import <path>" is run
    Then an error is printed: "File not found: <path>"
    And exit code 1


Feature: OpenCode agent import (C-2)

  Scenario: OpenCode file imports with same fidelity as Claude Code
    Given an OpenCode agent file (YAML frontmatter + body structurally identical to Claude Code)
    When imported
    Then the output AGENT.md is equivalent to what a Claude Code import would produce
    And the import report notes source format as "OpenCode"

  Scenario: Format auto-detection for identical schema
    Given a markdown file with YAML frontmatter but no explicit format tag
    When imported
    Then aede treats it as Claude Code / OpenCode format (they share the same schema)
    And the import report notes "Source format: Claude Code / OpenCode (auto-detected)"


# ============================================================
# Phase D — Subagent Orchestration
# ============================================================

Feature: Subagent spawn and context isolation (D-1)

  Scenario: Subagent gets a fresh context window (no bleed)
    Given an orchestrator session O with 10 messages of history
    When the orchestrator spawns subagent A
    Then subagent A's AgentLoop._messages starts empty (not a copy of O's history)
    And subagent A cannot read O's message history through the LLM

  Scenario: Subagent session is recorded in DB with parent_id
    Given an orchestrator session with session_id "PARENT"
    When subagent A is spawned
    Then a new row is inserted into sessions with parent_id == "PARENT"
    And subagent A's messages are stored under its own session_id

  Scenario: Subagent uses filtered ToolRouter (tool scoping)
    Given an AGENT.md declaring tools: ["read_file", "search_files"]
    When the subagent is spawned
    Then a new ToolRouter instance is constructed with only read_file and search_files registered
    And the subagent cannot call powershell even if it hallucinates the name
    And UnknownToolError is returned to the model for any out-of-scope tool call

  Scenario: Subagent uses model override from AGENT.md
    Given an AGENT.md with model: "claude-haiku-4-20250514"
    And the orchestrator's cfg.model is "claude-sonnet-4-20250514"
    When the subagent is spawned
    Then get_provider(sub_cfg) is called with model "claude-haiku-4-20250514"
    And the orchestrator's provider is unaffected

  Scenario: Subagent model inherits orchestrator model when model is "inherit"
    Given an AGENT.md with model: "inherit"
    When the subagent is spawned
    Then the subagent's model equals orchestrator's cfg.model


Feature: Subagent result return (D-2)

  Scenario: Result is a string returned to orchestrator not printed to user
    Given a subagent that produces a final text response "Analysis complete: X"
    When run_subagent() returns
    Then the return value is the string "Analysis complete: X"
    And the text is NOT printed directly to the terminal during subagent execution

  Scenario: Subagent exceeds maxTurns — graceful termination
    Given an AGENT.md with maxTurns: 5
    And the subagent has not produced a final text response after 5 turns
    When the 5th turn completes
    Then the subagent is terminated
    And a string is returned indicating termination at maxTurns
    And the subagent session is marked status='archived' in the DB

  Scenario: Subagent fails with API error — error propagated to orchestrator
    Given a subagent that hits an API error on its first turn
    When run_subagent() returns
    Then a string is returned containing "[subagent error: ..."
    And the orchestrator receives it as an error tool_result
    And the orchestrator session continues (does not crash)


Feature: Subagent depth limit enforcement (D-3)

  Scenario: Orchestrator spawning subagent succeeds (depth 0 → 1)
    Given an orchestrator running at depth 0 (no parent)
    When it spawns a subagent
    Then the spawn succeeds

  Scenario: Subagent attempting to spawn a nested subagent is rejected
    Given a subagent running at depth 1
    When the subagent's AgentLoop attempts to call spawn_subagent()
    Then a DepthLimitError is raised
    And an error string is returned to the model indicating max depth reached
    And no new session is created


Feature: Per-agent LLM routing (D-4)

  Scenario: Anthropic model resolves to AnthropicProvider
    Given an AGENT.md with model: "claude-haiku-4-20250514"
    When the subagent provider is resolved
    Then get_provider() returns an AnthropicProvider
    And ANTHROPIC_API_KEY is used

  Scenario: Non-Anthropic model with api_base_url set resolves to OpenAIProvider
    Given an AGENT.md with model: "google/gemini-2.5-flash"
    And orchestrator cfg.api_base_url is set to an OpenRouter URL
    When the subagent provider is resolved
    Then get_provider() returns an OpenAIProvider

  Scenario: Subagent model override does not affect orchestrator cfg
    Given orchestrator cfg.model = "claude-sonnet-4-20250514"
    And AGENT.md model = "claude-haiku-4-20250514"
    When sub_cfg is constructed
    Then sub_cfg.model = "claude-haiku-4-20250514"
    And sub_cfg.api_base_url is inherited from orchestrator cfg
    And all other cfg fields are inherited from orchestrator cfg
