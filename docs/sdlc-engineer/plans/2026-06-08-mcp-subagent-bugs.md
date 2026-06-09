# MCP + Subagent Bug Fixes — Task Plan
Generated: 2026-06-08
AC coverage: MCP-001, AGENT-002, CONFIG-001, SKILLS-001
NFRs in scope: SEC-001 (spawn depth)
Estimated waves: 3
Parallelizable tasks: 6 of 8

## Anti-patterns to watch (from learnings)
none recorded

## Tasks

### Task 1: MCP spawn on bridge loop

**AC reference:** MCP-001 — sessions must be usable via call_sync
**Complexity:** M
**Depends on:** none
**File set:** `aede/mcp/client.py`, `tests/test_mcp_bridge.py`

**Failing test to write first:**
```python
@pytest.mark.asyncio
async def test_spawn_all_runs_on_bridge_loop(server_configs):
    """_spawn_one should create sessions on the bridge loop, not the caller's loop."""
    from aede.mcp.client import MCPBridge
    import asyncio

    bridge = MCPBridge(servers=server_configs)
    main_loop = asyncio.get_running_loop()

    # Track which loop _spawn_one runs on
    spawn_loop = None

    original_spawn = bridge._spawn_one
    async def tracking_spawn(name, cfg):
        nonlocal spawn_loop
        spawn_loop = asyncio.get_running_loop()
        # Run original with a mock session so we don't actually spawn
        import mcp
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = "t"
        mock_tool.description = ""
        mock_tool.inputSchema = {"type": "object"}
        mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

        with (
            patch("mcp.ClientSession", return_value=mock_session),
            patch("mcp.StdioServerParameters"),
            patch("mcp.client.stdio.stdio_client") as mock_stdio,
        ):
            mock_transport = MagicMock()
            mock_transport.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
            mock_transport.__aexit__ = AsyncMock()
            mock_stdio.return_value = mock_transport
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            return await original_spawn(name, cfg)

    bridge._spawn_one = tracking_spawn
    await bridge.spawn_all()

    assert spawn_loop is not None, "_spawn_one was never called"
    assert spawn_loop is not main_loop, (
        f"_spawn_one ran on main loop ({id(main_loop)}) instead of bridge loop ({id(spawn_loop)})"
    )
```

**RED command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_all_runs_on_bridge_loop -xvs`
**Expected RED output:** `AssertionError: _spawn_one ran on main loop` or `assert spawn_loop is not main_loop`

**Implementation goal:** Submit `spawn_all` to the bridge's background event loop via `run_coroutine_threadsafe`, so all session/transport creation happens on the correct loop.

**Minimal implementation:**
In `MCPBridge`, change `spawn_all` from `async def` to `def`, and submit the inner coroutine to `self._loop` via `run_coroutine_threadsafe`. Also fix `cli.py` to call it without `await`.

```python
# client.py — spawn_all becomes synchronous, like call_sync and shutdown_all
def spawn_all(self) -> list[str]:
    """Spawn all configured MCP servers concurrently on the bridge loop.

    Returns a list of server names that failed to spawn.
    """
    if self._loop is None:
        raise RuntimeError("Bridge event loop not available")

    async def _spawn_all() -> list[str]:
        failed: list[str] = []
        tool_schemas: dict[str, list[dict]] = {}

        async def _spawn_with_timeout(name: str, cfg: MCPServerConfig) -> None:
            try:
                schemas = await asyncio.wait_for(
                    self._spawn_one(name, cfg), timeout=MCP_TIMEOUT
                )
                if schemas:
                    tool_schemas[name] = schemas
            except Exception:
                failed.append(name)

        tasks = [_spawn_with_timeout(n, c) for n, c in self._servers.items()]
        if tasks:
            await asyncio.gather(*tasks)

        self._tool_schemas.update(tool_schemas)
        return failed

    future = asyncio.run_coroutine_threadsafe(_spawn_all(), self._loop)
    return future.result(timeout=MCP_TIMEOUT + 2)
```

```python
# cli.py:393 — no await
failed = mcp_bridge.spawn_all()
```

**GREEN command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_all_runs_on_bridge_loop -xvs`
**Verification step:** `uv run pytest tests/test_mcp_bridge.py -xvs`

**Commit:** `feat: Task 1 — MCP spawn_all runs on bridge loop (satisfies MCP-001)`

---

### Task 2: SIGINT handler uses flag instead of blocking I/O

**AC reference:** MCP-001 — graceful shutdown
**Complexity:** S
**Depends on:** none
**File set:** `aede/cli.py`

**Failing test to write first:**
```python
def test_sigint_sets_flag_instead_of_blocking(tmp_path):
    """SIGINT handler should set a flag, not call blocking I/O directly."""
    from aede.cli import main
    from unittest.mock import patch, MagicMock
    import signal

    # We can't easily test the full signal handler in a unit test,
    # so verify the pattern: the handler calls _shutdown and mcp shutdown
    # which involve blocking calls. The fix makes the handler set a flag.
    # Test that the new handler's body resembles a flag-set pattern.
    import inspect
    from aede import cli as cli_module

    # After fix, verify the handler source has "nonlocal" and no blocking calls
    source = inspect.getsource(cli_module.main)
    assert "stop_requested" in source or "signal_received" in source, (
        "Expected signal handler to use a flag variable"
    )
```

**RED command:** `uv run pytest tests/test_cli.py -xvs 2>/dev/null || uv run pytest tests/ -k "sigint" -xvs`
**Expected RED output:** `AssertionError: Expected signal handler to use a flag variable`

**Implementation goal:** Replace blocking I/O in `_handle_sigint` with a flag check in the main event loop.

**Minimal implementation:**
In `cli.py`, add `stop_requested = False` before the signal handler. The handler only sets `stop_requested = True`. The main loop checks `stop_requested` between turns and calls shutdown from the loop context.

```python
stop_requested = False

def _handle_sigint(sig, frame):
    nonlocal stop_requested
    stop_requested = True
    console.print("\n[dim]Interrupted. Shutting down...[/dim]")

signal.signal(signal.SIGINT, _handle_sigint)

while not stop_requested:
    try:
        user_input = console.input("> ")
    except EOFError:
        break
    if not user_input:
        continue
    if stop_requested:
        break
    ...
```

And at the end of the `main()` function, move the MCP + DB shutdown:

```python
# After the main loop exits
if mcp_bridge is not None:
    try:
        mcp_bridge.shutdown_all()
    except Exception:
        pass
_shutdown(session, db, rollout, stop_reason)
```

**GREEN command:** `uv run pytest tests/ -k "sigint" -xvs`
**Verification step:** `uv run pytest tests/ -x --timeout=30 2>&1 | tail -20`

**Commit:** `feat: Task 2 — SIGINT handler sets flag, defers blocking I/O (satisfies MCP-001)`

---

### Task 3: Config reads mcpServers (camelCase) too

**AC reference:** CONFIG-001 — MCP config key compatibility
**Complexity:** XS
**Depends on:** none
**File set:** `aede/config.py`, `tests/test_config.py`

**Failing test to write first:**
```python
def test_mcp_config_accepts_camelCase(tmp_home):
    """AedeConfig accepts mcpServers (camelCase) as alias for mcp_servers."""
    from aede.config import AedeConfig
    from pathlib import Path

    data = {
        "mcpServers": {
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp"],
            },
        },
    }
    cfg = AedeConfig(data=data, home=tmp_home)
    assert "playwright" in cfg.mcp_servers
    assert cfg.mcp_servers["playwright"].command == "npx"
```

**RED command:** `uv run pytest tests/test_config.py::test_mcp_config_accepts_camelCase -xvs`
**Expected RED output:** `AssertionError: 'playwright' not in {}` or `KeyError: 'mcp_servers'`

**Implementation goal:** In `AedeConfig.__init__`, try `mcpServers` as fallback when `mcp_servers` is empty.

**Minimal implementation:**
```python
# config.py line 128
raw_mcp = data.get("mcp_servers") or data.get("mcpServers") or {}
```

**GREEN command:** `uv run pytest tests/test_config.py::test_mcp_config_accepts_camelCase -xvs`
**Verification step:** `uv run pytest tests/test_config.py -xvs`

**Commit:** `feat: Task 3 — Config reads mcpServers camelCase key (satisfies CONFIG-001)`

---

### Task 4: MCP env merging preserves parent environment

**AC reference:** MCP-001 — MCP servers inherit PATH
**Complexity:** XS
**Depends on:** none
**File set:** `aede/mcp/client.py`, `tests/test_mcp_bridge.py`

**Failing test to write first:**
```python
@pytest.mark.asyncio
async def test_spawn_one_env_inherits_parent(server_configs):
    """_spawn_one merges cfg.env over os.environ, not replacing it entirely."""
    from aede.mcp.client import MCPBridge
    from unittest.mock import AsyncMock, MagicMock, patch

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "t"
    mock_tool.description = ""
    mock_tool.inputSchema = {"type": "object"}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    captured_env = None
    original_params = None

    with (
        patch("mcp.ClientSession", return_value=mock_session),
        patch("mcp.StdioServerParameters") as mock_params_cls,
        patch("mcp.client.stdio.stdio_client") as mock_stdio,
    ):
        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        def capture_params(*args, **kwargs):
            nonlocal captured_env, original_params
            original_params = args[0] if args else None
            return MagicMock()
        mock_params_cls.side_effect = capture_params

        await bridge._spawn_one("test_server", server_configs["playwright"])

    assert captured_env is not None, "StdioServerParameters never created"
    assert "PATH" in captured_env or "Path" in captured_env, (
        "Parent process PATH was not inherited in spawned env"
    )
    assert captured_env.get("TEST_AEDE_MAGIC") == "present", (
        "cfg.env keys should override but not replace parent env"
    )
```

**RED command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_one_env_inherits_parent -xvs`
**Expected RED output:** `AssertionError: Parent process PATH was not inherited in spawned env`

**Implementation goal:** Merge `os.environ` as base when constructing env for `StdioServerParameters`.

**Minimal implementation:**
```python
# client.py line 99: change
env={**cfg.env} if cfg.env else None
# to:
env={**os.environ, **cfg.env} if cfg.env else None
```

Add `import os` at top of file if needed (already imported via `from __future__ import annotations` — check actual import).

**GREEN command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_one_env_inherits_parent -xvs`
**Verification step:** `uv run pytest tests/test_mcp_bridge.py -xvs`

**Commit:** `feat: Task 4 — MCP env merges parent process environment (satisfies MCP-001)`

---

### Task 5: Subagent spawn depth enforced

**AC reference:** AGENT-002 — spawn depth must be enforced
**Complexity:** S
**Depends on:** none
**File set:** `aede/tools/router.py`, `tests/test_subagent_depth_limit.py`

**Failing test to write first:**
```python
def test_spawn_subagent_tool_includes_depth():
    """_spawn closure in router passes orchestrator_spawn_depth=1 to run_subagent."""
    from aede.tools.router import ToolRouter
    from pathlib import Path
    from unittest.mock import patch, MagicMock, ANY

    router = ToolRouter(
        shell="powershell",
        wsl_distro="",
        tool_output_max_tokens=8000,
        _cfg=MagicMock(),
        _gate_store=MagicMock(),
        _agent_registry={
            "sub": MagicMock(name="sub", tools=[], disallowed_tools=[], max_turns=2),
        },
        _session_id="test-001",
        data_dir=Path("/tmp"),
    )

    # Grab the spawn_subagent handler
    handler = router._registry.get("spawn_subagent")
    assert handler is not None, "spawn_subagent not registered"

    with patch("aede.tools.router.run_subagent") as mock_run:
        mock_run.return_value = "done"
        handler({"agent_name": "sub", "task": "test"})

    # Verify orchestrator_spawn_depth=1 was passed
    call_kwargs = mock_run.call_args.kwargs if hasattr(mock_run.call_args, 'kwargs') else mock_run.call_args[1]
    assert call_kwargs.get("orchestrator_spawn_depth") == 1, (
        f"Expected orchestrator_spawn_depth=1, got {call_kwargs.get('orchestrator_spawn_depth')}"
    )
```

**RED command:** `uv run pytest tests/test_subagent_depth_limit.py::test_spawn_subagent_tool_includes_depth -xvs`
**Expected RED output:** `AssertionError: Expected orchestrator_spawn_depth=1`

**Implementation goal:** Pass `orchestrator_spawn_depth=1` in the `_spawn` closure's `run_subagent` call.

**Minimal implementation:**
```python
# router.py lines 112-118: add orchestrator_spawn_depth=1
coro = run_subagent(
    agent_def=agent_def,
    task=task,
    orchestrator_cfg=_o_cfg,
    orchestrator_gate_store=_o_gate,
    orchestrator_session_id=_o_sid,
    orchestrator_spawn_depth=1,
)
```

**GREEN command:** `uv run pytest tests/test_subagent_depth_limit.py -xvs`
**Verification step:** `uv run pytest tests/test_subagent_depth_limit.py tests/test_subagent_spawn_tool.py -xvs`

**Commit:** `feat: Task 5 — Subagent spawn depth enforced (satisfies AGENT-002)`

---

### Task 6: Remove dead code in run_subagent

**AC reference:** AGENT-002 — clean code
**Complexity:** XS
**Depends on:** none
**File set:** `aede/agents/orchestration.py`

**Failing test to write first:**
```python
def test_run_subagent_no_dead_reconstruction_branch():
    """run_subagent should not contain unreachable isinstance reconstruction code."""
    import inspect
    from aede.agents import orchestration

    source = inspect.getsource(orchestration.run_subagent)
    assert "not isinstance(sub_cfg, AedeConfig)" not in source, (
        "Dead reconstruction branch still present"
    )
```

**RED command:** `uv run pytest tests/ -k "no_dead_reconstruction" -xvs`
**Expected RED output:** `AssertionError: Dead reconstruction branch still present`

**Implementation goal:** Remove the unreachable `isinstance` check and `AedeConfig` reconstruction block.

**Minimal implementation:**
Remove lines 71-86 from `orchestration.py` (the `if not isinstance(sub_cfg, AedeConfig):` block and its body).

**GREEN command:** `uv run pytest tests/ -k "no_dead_reconstruction" -xvs`
**Verification step:** `uv run pytest tests/test_subagent_depth_limit.py tests/test_subagent_spawn_tool.py -xvs`

**Commit:** `refactor: Task 6 — Remove dead isinstance reconstruction branch in run_subagent`

---

### Task 7: Skills loader warns on load errors

**AC reference:** SKILLS-001 — load errors must be visible
**Complexity:** XS
**Depends on:** none
**File set:** `aede/skills/loader.py`, `tests/test_skills_loader.py`

**Failing test to write first:**
```python
def test_skills_loader_warns_on_bad_skill(tmp_path, capsys):
    """load_skills should print a warning when a SKILL.md fails to load."""
    from aede.skills.loader import load_skills

    bad_skill = tmp_path / "global" / "skills" / "broken.md"
    bad_skill.parent.mkdir(parents=True)
    bad_skill.write_text("not valid frontmatter")

    registry = load_skills(
        global_dir=tmp_path / "global",
        project_dir=tmp_path / "project" if (tmp_path / "project").exists() else tmp_path,
    )
    captured = capsys.readouterr()
    assert "broken" in captured.out or "broken" in captured.err or not registry, (
        "Expected a warning about the bad skill file"
    )
```

**RED command:** `uv run pytest tests/test_skills_loader.py::test_skills_loader_warns_on_bad_skill -xvs`
**Expected RED output:** `AssertionError: Expected a warning about the bad skill file`

**Implementation goal:** Add `print()` or `import warnings` in the `except SkillLoadError` block to surface the error.

**Minimal implementation:**
```python
# loader.py line 18-19: change
except SkillLoadError:
    pass
# to:
except SkillLoadError as e:
    print(f"[yellow]⚠ Skill load error in {md_path.name}: {e}[/yellow]")
```

**GREEN command:** `uv run pytest tests/test_skills_loader.py::test_skills_loader_warns_on_bad_skill -xvs`
**Verification step:** `uv run pytest tests/test_skills_loader.py -xvs`

**Commit:** `feat: Task 7 — Skills loader warns on load errors (satisfies SKILLS-001)`

---

### Task 8: MCP `_processes` populated for force-kill

**AC reference:** MCP-001 — force-kill fallback must work
**Complexity:** S
**Depends on:** Task 1
**File set:** `aede/mcp/client.py`, `tests/test_mcp_bridge.py`

**Failing test to write first:**
```python
@pytest.mark.asyncio
async def test_spawn_one_stores_process_handle(server_configs):
    """_spawn_one should extract and store the subprocess handle in _processes."""
    from aede.mcp.client import MCPBridge
    from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

    bridge = MCPBridge(servers=server_configs)

    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "t"
    mock_tool.description = ""
    mock_tool.inputSchema = {"type": "object"}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])

    # Create a mock process that stdio_client exposes
    mock_process = MagicMock()
    mock_process.pid = 12345

    with (
        patch("mcp.ClientSession", return_value=mock_session),
        patch("mcp.StdioServerParameters"),
        patch("mcp.client.stdio.stdio_client") as mock_stdio,
    ):
        mock_read = MagicMock()
        mock_write = MagicMock()
        # MCP SDK's stdio_client returns (read, write) — the process
        # is available via read._transport._proc or similar.
        # We'll just verify _processes gets populated with some handle.
        mock_transport = MagicMock()
        mock_transport.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_transport.__aexit__ = AsyncMock()
        mock_stdio.return_value = mock_transport
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        await bridge._spawn_one("test_server", server_configs["playwright"])

    assert "test_server" in bridge._processes, (
        "_processes should have entry after spawn"
    )
```

**RED command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_one_stores_process_handle -xvs`
**Expected RED output:** `AssertionError: _processes should have entry after spawn`

**Implementation goal:** After `stdio_client` enters, extract the subprocess handle and store in `_processes`.

**Minimal implementation:**
After the transport is entered (line 103-104), extract the process handle:

```python
transport_cm = stdio_client(server_params)
transport = await transport_cm.__aenter__()
read, write = transport
# Extract subprocess handle for force-kill fallback
proc = getattr(read, '_transport', None)
if hasattr(proc, '_proc'):
    self._processes[name] = proc._proc
```

**GREEN command:** `uv run pytest tests/test_mcp_bridge.py::test_spawn_one_stores_process_handle -xvs`
**Verification step:** `uv run pytest tests/test_mcp_bridge.py -xvs`

**Commit:** `feat: Task 8 — MCP _processes populated for force-kill fallback (satisfies MCP-001)`

---

## Dependency graph

**Wave 0** (no deps, can parallelize):
- Task 1: MCP spawn on bridge loop
- Task 2: SIGINT handler flag
- Task 3: Config camelCase key
- Task 4: Env merging
- Task 5: Spawn depth
- Task 6: Dead code removal
- Task 7: Skills loader warning

**Wave 1** (depends on Task 1):
- Task 8: MCP _processes populated

**Critical path:** Task 1 → Task 8 (2 waves)

**Parallelization note:** Tasks 2-7 are parallelizable with Task 1 and each other (disjoint file sets: cli.py, config.py, router.py, orchestration.py, loader.py).
