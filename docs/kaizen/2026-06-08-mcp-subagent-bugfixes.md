# Kaizen: Phase 2 MCP + Subagent Bug Fixes

Date: 2026-06-08
Session: MCP bridge loop, SIGINT, config, env, subagent depth fixes

## What went wrong

Spec audit revealed 8 issues across 4 Phase 2 features after merging all branches into `merge-phase2`. Two of these were genuinely runtime-critical:

1. **MCP spawn on main loop** — `spawn_all` was `async def` called with `await` from the main coroutine, so all `stdio_client` streams and `ClientSession` objects were created on the main event loop. But `call_sync` dispatched every tool call to the bridge's background loop via `run_coroutine_threadsafe`. MCP SDK streams are loop-affine (store creation loop internally), so calling `session.call_tool()` on a different loop would raise `RuntimeError: Task ... got Future ... attached to a different loop`. This would crash on the first real MCP tool call in production.

2. **SIGINT handler blocked** — `_handle_sigint` was a synchronous signal handler calling `console.print()`, `mcp_bridge.shutdown_all()` (which does `future.result(timeout=5)`), and `_shutdown()` (SQLite writes). Blocking from a signal handler risks deadlock if the event loop was mid-operation.

## What went well

- **Systematic debugging skill** forced root-cause tracing before proposing fixes — caught the loop-affine issue that a quick glance would have missed.
- **Parallel subagent dispatch** for Tasks 2-7 (all disjoint file sets) reduced wall-clock time from ~6 sequential cycles to ~1.
- **TDD-first approach** caught the `patch("aede.tools.router.run_subagent")` bug — subagent imported it inside a closure, not at module level. The RED test revealed the disconnect.

## Root causes

| Issue | Root cause |
|-------|-----------|
| MCP wrong loop | `spawn_all` `async def` with `await` from main coroutine instead of `run_coroutine_threadsafe` to bridge loop |
| SIGINT blocking | Handler did I/O instead of setting a flag |
| Config key miss | Only checked `mcp_servers` not `mcpServers` |
| Env lost parent | `{**cfg.env}` instead of `{**os.environ, **cfg.env}` |
| Depth not enforced | `orchestrator_spawn_depth` not passed in `_spawn` closure |
| Dead code | Defensive `isinstance` branch that was always True |
| Skills loader silent | Bare `pass` in `except` block |
| `_processes` empty | Never extracted subprocess handle from stdio transport |

## Prevention

- Review all "run on background thread" patterns for loop-affine object creation — the bridge loop pattern (thread + `run_until_complete`/`run_coroutine_threadsafe`) should be consistent: ALL async work on the bridge goes through its loop, never the caller's.
- Signal handlers should follow the "set flag only" pattern — add to code review checklist.
- When writing closure-based tool handlers, be explicit about all parameter passing — missing args are silently defaulted.
