# MCP Client — Acceptance Criteria (Gherkin)
#
# Consolidated from: .claude/docs/phase2/phase2-spec-mcp-client.md §2
# Source spec status: Draft (2026-06-06)
# US-01..US-09

Feature: MCP server config parsing (US-01)

  Scenario: Valid mcpServers block in global config parses correctly
    Given ~/.aede/config.yml contains a mcpServers block with server "playwright"
    And command is "npx", args is ["@playwright/mcp@latest"], env is {"DISPLAY": ":0"}
    When load_config() is called
    Then cfg.mcp_servers["playwright"].command == "npx"
    And cfg.mcp_servers["playwright"].args == ["@playwright/mcp@latest"]
    And cfg.mcp_servers["playwright"].env == {"DISPLAY": ":0"}
    And cfg.mcp_servers["playwright"].trusted == False

  Scenario: trusted flag is parsed correctly
    Given ~/.aede/config.yml contains server "docling" with trusted: true
    When load_config() is called
    Then cfg.mcp_servers["docling"].trusted == True

  Scenario: Project config overrides global for the same server name
    Given ~/.aede/config.yml declares server "fs" with command "node"
    And ./aede.yml declares server "fs" with command "uvx"
    When load_config() is called
    Then cfg.mcp_servers["fs"].command == "uvx"

  Scenario: Project config adds a server not in global config
    Given ~/.aede/config.yml declares server "playwright"
    And ./aede.yml declares server "docling"
    When load_config() is called
    Then cfg.mcp_servers has keys "playwright" and "docling"

  Scenario: No mcpServers key results in empty dict
    Given ~/.aede/config.yml has no mcpServers key
    When load_config() is called
    Then cfg.mcp_servers == {}

  Scenario: args and env are optional with safe defaults
    Given ~/.aede/config.yml contains server "minimal" with only command: python
    When load_config() is called
    Then cfg.mcp_servers["minimal"].args == []
    And cfg.mcp_servers["minimal"].env == {}


Feature: Eager server spawn at session start (US-02)

  Scenario: Servers are spawned before the first prompt is shown
    Given config has one MCP server "playwright"
    When the aede session starts (before the ">" prompt is shown)
    Then the "playwright" process has been spawned
    And the MCP initialize handshake has completed
    And tools/list has been called
    And the discovered tools are registered in ToolRouter

  Scenario: Spawn failure does not prevent session from starting
    Given config declares server "broken" with command "nonexistent-binary"
    When the aede session starts
    Then aede prints a warning referencing MCP server 'broken' failing to spawn
    And aede starts normally and shows the ">" prompt
    And the eight built-in tools are still available

  Scenario: Partial success — one server fails, one succeeds
    Given config declares servers "broken" (bad command) and "playwright" (good command)
    When the aede session starts
    Then a warning is shown for "broken"
    And tools from "playwright" are available
    And "broken" contributes no tools

  Scenario: Spawn timeout kills the slow server
    Given config declares server "slow" whose process hangs during initialize
    When 10 seconds elapse
    Then aede kills the "slow" process
    And prints a warning about "slow" timing out during startup
    And session starts without "slow" tools


Feature: MCP tool naming and registry merge (US-03)

  Scenario: Single server tools are namespaced correctly
    Given server "playwright" exposes tools "navigate" and "screenshot"
    When tools are loaded into ToolRouter
    Then ToolRouter.tool_names() includes "mcp__playwright__navigate"
    And ToolRouter.tool_names() includes "mcp__playwright__screenshot"
    And ToolRouter.tool_names() does NOT include bare "navigate" or "screenshot"

  Scenario: Two servers with same-named tool have no collision
    Given server "fs" exposes tool "read"
    And server "git" exposes tool "read"
    When tools are loaded
    Then ToolRouter has "mcp__fs__read" and "mcp__git__read" as distinct tools

  Scenario: MCP tool name conversion for Anthropic API
    Given server "playwright" tool "navigate" has inputSchema with url property
    When the schema is converted for the Anthropic API
    Then the resulting dict has name "mcp__playwright__navigate"
    And description from the MCP server
    And input_schema matching the MCP inputSchema

  Scenario: /tools command shows MCP tools
    Given one MCP server is connected with two tools
    When the user types /tools
    Then the output lists all mcp__* tool names alongside built-in tools


Feature: MCP tool call through approval gate (US-04)

  Scenario: Untrusted MCP tool requires approval
    Given server "playwright" is configured with trusted: false (default)
    And the model emits a tool_use block with name "mcp__playwright__navigate"
    When AgentLoop.run_turn processes the tool call
    Then ToolRouter.requires_approval("mcp__playwright__navigate") returns True
    And the gate prompt is shown with tool name and server attribution

  Scenario: User allows an MCP tool call once
    Given the gate is shown for "mcp__playwright__navigate"
    When the user allows once
    Then the tool call is dispatched to MCPBridge.call_tool
    And the result is returned to the model as a tool_result content block
    And output is truncated if it exceeds tool_output_max_tokens * 4 chars

  Scenario: User denies an MCP tool call
    Given the gate is shown for "mcp__playwright__navigate"
    When the user denies
    Then a tool_result is returned with is_error=True and content "Tool call denied by user."
    And the MCP server process is not called


Feature: Per-server trusted auto-run (US-05)

  Scenario: Trusted server tool bypasses gate
    Given server "docling" has trusted: true in config
    When AgentLoop.run_turn encounters a call to "mcp__docling__convert"
    Then ToolRouter.requires_approval("mcp__docling__convert") returns False
    And the gate prompt is NOT called
    And the tool executes immediately

  Scenario: Untrusted server (default) requires approval
    Given server "playwright" has no trusted flag (defaults to false)
    When AgentLoop.run_turn encounters "mcp__playwright__navigate"
    Then ToolRouter.requires_approval returns True

  Scenario: Session allow-always persists for a session
    Given "mcp__playwright__navigate" is untrusted
    And the user selects "Always allow — Session scope"
    Then gate_store.is_allowed("mcp__playwright__navigate") returns True
    And subsequent calls to that tool skip the gate for the session


Feature: Spawn failure graceful degradation (US-06)

  Scenario: Unknown command degrades gracefully
    Given server "bad" has command "this-does-not-exist"
    When spawn is attempted at session start
    Then the exception is caught and a yellow warning is printed
    And no mcp__bad__* tools appear in ToolRouter
    And all eight built-in tools are still available

  Scenario: Spawn timeout kills the hanging server
    Given server "hangs" never completes the MCP initialize handshake
    When 10 seconds elapse
    Then the process is terminated
    And a warning is printed about the timeout
    And session continues without "hangs" tools

  Scenario: Failed server does not affect other servers
    Given servers "bad" (broken) and "playwright" (healthy)
    After session start:
    Then "playwright" tools are available in ToolRouter
    And "bad" contributed no tools


Feature: Mid-session server crash handling (US-07)

  Scenario: call_tool on a crashed server returns error result
    Given server "playwright" was healthy at startup
    And the "playwright" process has since terminated
    When the model requests "mcp__playwright__navigate" and execute_sync is called
    Then ToolResult.status == "error"
    And ToolResult.output contains a message about server unavailability
    And aede does NOT raise an unhandled exception
    And the session remains interactive

  Scenario: Built-in tools remain available after MCP crash
    Given "playwright" has crashed
    When the model calls "read_file"
    Then read_file executes normally


Feature: MCP shutdown on session end (US-08)

  Scenario: /exit triggers MCP shutdown
    Given two MCP servers are connected
    When the user types /exit
    Then MCPBridge.shutdown_all() is called before _shutdown() writes session_end
    And both server processes receive graceful shutdown
    And any process that does not exit within 3 seconds is killed
    And no MCP processes remain after aede exits

  Scenario: No MCP servers configured — shutdown is a no-op
    Given cfg.mcp_servers == {}
    When /exit is typed
    Then MCPBridge.shutdown_all() is called and returns immediately (no error)


Feature: Output truncation for MCP results (US-09)

  Scenario: MCP result within cap is not truncated
    Given tool_output_max_tokens is 8000
    And MCPBridge.call_tool returns a text result of 4000 tokens
    When execute_sync processes the result
    Then ToolResult.output is the full text (no truncation marker)

  Scenario: MCP result exceeding cap is truncated
    Given tool_output_max_tokens is 8000
    And MCPBridge.call_tool returns a text result of 12000 tokens
    When execute_sync processes the result
    Then ToolResult.output is truncated at 32000 chars (8000 * 4)
    And the truncation suffix is appended indicating truncation
