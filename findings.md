# Findings & Decisions — Phase 2 Branch Merge

## Requirements
- Merge `phase2-basic-correctness` into main (no-op)
- Merge `phase2-mcp-client` into main (fix 3 critical bugs first)
- Merge `phase2-memory-session-search` into main
- Merge `phase2-acp-connections` into main
- All merges via `merge-phase2` branch
- Full test suite must pass at each step
- Document everything for future reference

## Research Findings

### Branch Status
| Branch | Behind Main | Ahead | Style | Module Type |
|--------|-------------|-------|-------|-------------|
| basic-correctness | 18 | 0 | No-op | — |
| mcp-client | 19 | 1 | Single commit | New `aede/mcp/` + shared file changes |
| memory-session-search | 19 | 4 | 4 commits | Memory features + shared file changes |
| acp-connections | 15 | 1 | Single commit | New `aede/acp/` + shared file changes |

### MCP Branch: 3 Critical Bugs
1. **Session-closed**: `_spawn_one` uses `async with mcp.ClientSession(...)` — session closes on function return, but `call_sync` uses it later
2. **Spawn not awaited**: `cli.py` calls `mcp_bridge.spawn_all()` without `await` in async function — coroutine evaporates
3. **Config not wired**: `_parse_mcp_servers` function exists but is never called from `AedeConfig.__init__` — `mcp_servers` field doesn't exist on config
4. **Missing dep**: `mcp` SDK not added to `pyproject.toml`

### ACP Branch: Custom JSON-RPC (Not SDK)
- The research doc (`.claude/docs/research/acp-connections.md`) recommends `agent-client-protocol` SDK
- The branch implements its own JSON-RPC from scratch in `aede/acp/client.py`
- No `agent-client-protocol` dependency in `pyproject.toml`
- Recommendation: keep as-is for Phase 2, defer SDK migration to Phase 3

### Memory Branch: Closest to Spec
- Generally matches the memory system spec
- Notable additions not in spec: dual JSONL+SQLite storage, learnings FTS5 table
- Minor: OllamaClient is sync (spec implied async)

### Cross-Cutting Changes (All Branches)
All branches modify the same shared files in similar ways:
- `gate.py`: Remove `GateBackend` protocol and `TerminalGateBackend`
- `config.py`: Remove BC/memory config keys (different keys per branch)
- `cli.py`: Add new subcommands, remove old ones
- `agent.py`: Simplify `AgentLoop.__init__` (no `gate_backend`)
- `db.py`: Remove projects table from DDL
- `tools/router.py`: Add/remove tools

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Fix MCP bugs before merging | Can't merge broken code; fix on the branch then merge |
| Merge additive modules first | acp/ and mcp/ directories won't conflict; saves hardest for last |
| Keep ACP custom impl for Phase 2 | Works, has tests, SDK migration is distinct work |
| Create merge-phase2 branch | Safe spot for conflict resolution before landing on main |
| User decides on shared-file conflicts | 3 versions of same files need human judgment |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| ACP has no spec doc | Found `.claude/docs/research/acp-connections.md` — research brief, not spec |
| All branches behind main by 15-19 commits | Rebase would be needed; merge approach instead |
| No dedicated ACP spec in phase2/ directory | ACP is only covered by research doc + deferred list mention |

## Resources
- `.claude/docs/phase2/phase2-spec-mcp-client.md` — MCP spec
- `.claude/docs/phase2/phase2-spec-memory-system.md` — Memory system spec
- `.claude/docs/phase2/phase2-spec-basic-correctness.md` — BC spec
- `.claude/docs/phase2/phase2-tasks-basic-correctness-and-mcp.md` — Task breakdown
- `.claude/docs/phase2/phase2-spec-agent-system.md` — Agent system (different from ACP)
- `.claude/docs/research/acp-connections.md` — ACP research brief
- `.claude/docs/phase2/phase2-defer-list.md` — Deferred items
- `agentclientprotocol.com` — Official ACP protocol docs
