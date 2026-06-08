# Task Plan: Merge 4 Phase 2 Branches into Main + Fix MCP Bug

## Goal
Merge `phase2-basic-correctness`, `phase2-mcp-client`, `phase2-memory-session-search`, and `phase2-acp-connections` into main, fixing the MCP session-closed bug along the way.

## Current Phase
Phase 1: Documentation & Planning

## Phases

### Phase 1: Documentation & Planning
- [x] Audit all branches (commits, diffs vs main, spec compliance)
- [x] Read all Phase 2 docs (specs, research, tasks, deferred)
- [x] Document discrepancies (MCP bugs, ACP undocumented, cross-cutting deletions)
- [x] Create task_plan.md, findings.md, progress.md
- [x] Update ACP research doc with Phase 3 deferral note
- [ ] Determine merge order and conflict strategy
- [ ] Get user go-ahead on conflict resolution approach
- **Status:** in_progress

### Phase 2: Fix MCP Bugs (TDD)
- [ ] Write failing test for session-closed bug (RED)
- [ ] Fix `_spawn_one` to keep session alive after return (GREEN)
- [ ] Write failing test for await bug (RED)
- [ ] Fix `spawn_all()` call in `cli.py` (GREEN)
- [ ] Write failing test for config wiring bug (RED)
- [ ] Wire `_parse_mcp_servers` into `AedeConfig.__init__` (GREEN)
- [ ] Write failing test for missing `mcp` SDK dependency (RED)
- [ ] Add `mcp` to `pyproject.toml` (GREEN)
- [ ] Log root cause to `docs/kaizen/`
- **Status:** pending

### Phase 3: Merge Branches Sequentially
- [ ] Create `merge-phase2` branch from main (`3b83999`)
- [ ] Merge `basic-correctness` (no-op, 0 commits ahead)
- [ ] Merge `memory-session-search` → resolve shared-file conflicts
- [ ] Merge `mcp-client` (with fixes from Phase 2) → resolve conflicts
- [ ] Merge `acp-connections` → resolve conflicts
- [ ] Final conflict: reconcile all 3 branch versions of shared files
- **Status:** pending

### Phase 4: Verification
- [ ] Run full test suite (`uv run pytest`)
- [ ] Run `uv run aede` smoke test (quick launch + exit)
- [ ] Fix any regressions
- [ ] Verify gate rendering + tool routing still works
- **Status:** pending

### Phase 5: Cleanup & Documentation
- [ ] Log kaizen entries for any new bugs found during merge
- [ ] Squash merge to main
- [ ] Update documentation to reflect merged state
- **Status:** pending

## Key Questions
1. Merge order: memory → mcp → acp, or different? (MCP has bugs, so fixing first then merging)
2. When shared files conflict 3 ways (gate.py, config.py, cli.py) — which branch's version should win for each section?
3. ACP custom JSON-RPC (no SDK) — kept as-is, deferred to Phase 3 for SDK replacement?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Fix MCP bugs before merging | Merging broken code propagates bugs; fix on the branch then merge |
| Merge in additive-first order | New modules (acp/, mcp/) don't conflict; saves shared-file conflicts for last |
| ACP custom impl kept, deferred to Phase 3 | Functional and tested; SDK replacement is a separate effort |
| basic-correctness first (no-op) | Zero risk, establishes merge branch |
| User resolves shared-file conflicts | 3 branches modifying same lines need human judgment |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

## Notes
- `basic-correctness` is 0 commits ahead of main — pure no-op merge
- MCP session bug: `_spawn_one` uses `async with ClientSession` which closes on return
- ACP branch uses custom JSON-RPC, not the `agent-client-protocol` SDK from the research doc
- All branches remove `gate_backend` protocol from gate.py — need to decide which version wins
- Re-read this plan before major decisions
