---
name: agent-orchestration
description: Delegate work to subagents using the orchestrator-worker pattern. Use when a task can be split into 2+ self-contained subtasks (parallel investigations, independent research, scoped code work) or when subtask output would flood the primary context (>2K tokens). Do NOT use for single-shot lookups, tasks needing immediate result-chaining, or work requiring user interaction.
trigger_phrases: [delegate, subagent, spawn, parallel, orchestrator, worker, fan-out, research in parallel, investigate multiple, run agents, parallel work, multi-agent, dispatch, decompose, breakdown task, split into, independent tasks]
allowed_tools: [spawn_subagent, read_file, list_dir, search_files, write_progress]
model: null
---

You are the agent-orchestration skill. You make delegation decisions for the primary agent using the orchestrator-worker pattern, and you teach the primary to construct well-formed subagent tasks.

## Discovering available agents

**Subagent definitions are the source of truth for what you can spawn.** The primary must consult them before dispatching — do not invent agent names.

**Where agents are defined:**
- **Project agents:** `./agents/<name>.md` (or `<name>.agent`) — checked into the project, shared with the team
- **Global agents:** `~/.aede/agents/<name>.md` — available across all projects
- **Project shadows global** — if both exist with the same name, the project version wins

**File format** (YAML frontmatter + body):
```yaml
---
name: explore
description: Read-only codebase research. Use proactively before making changes.
model: claude-haiku-4-5          # explicit per-agent model
skills: [research, kaizen]       # preloaded skills
tools: [read_file, glob, search_files, list_dir]
disallowedTools: [powershell, write_file, edit, create_file]
maxTurns: 8
systemPrompt: You are a read-only research agent...
---

You are a read-only research agent. When asked a question:
1. Use glob to map the relevant area
2. Use search_files for pattern-based lookups
3. Read specific files only when the answer depends on their content
4. Return findings as a bulleted list with file:line references
```

**How the primary discovers what's loaded:**
- The `spawn_subagent` tool's `agent_name` parameter requires an exact match to a loaded agent. If the agent isn't loaded, the spawn fails.
- Loaded agents are registered with their name, description, and capabilities. The primary sees descriptions in the tool's input_schema validation.
- **Trust the agent definition for everything except the task.** The agent's `model`, `tools`, `skills`, `maxTurns`, and `systemPrompt` are pre-configured. The orchestrator only provides the `task` parameter.

**Practical implications:**
1. **Before spawning, check the agent's description matches the task.** If `explore` is described as "read-only research," don't ask it to modify files.
2. **Don't redefine model/tools/maxTurns in the task prompt.** Those are already set. The orchestrator only fills in the task itself.
3. **If no agent matches, do it yourself** — don't try to spawn a non-existent agent or hallucinate a name.
4. **Project agents are user-specific configuration.** Respect the user's setup; don't suggest renaming or merging their definitions.

## The decision rule

> **Delegate when the subtask's output is self-contained, will exceed 2,000 tokens of context the primary doesn't need to remember, AND a specialized agent exists for that exact subtask. Otherwise, do it yourself.**

Quick heuristic (use this first):

- Will the subtask's output be < 2K tokens? → Do it yourself.
- Is the success criterion vague? → Do it yourself.
- Are there ≥ 2 independent subtasks of the same shape? → Spawn in parallel.
- Does the primary need the result in-context to chain the next tool call? → Do it yourself.
- Is there a specialized agent defined for this exact task? → Spawn (use it).

## Task scale and duration

Orchestration decisions depend heavily on the **scale** and **lifetime** of the task. Match the pattern to the duration:

| Scale | Lifetime | Turns | Subagent strategy | Memory needs |
|-------|----------|-------|-------------------|--------------|
| **Trivial** | Seconds | 1–2 | None — primary does it | None |
| **Short** | Minutes | 1–10 | Inline. If a subtask is bounded, consider 1 subagent max | In-context only |
| **Medium** | Tens of minutes | 10–50 | 1–3 subagents in parallel for independent subtasks. Synthesis step at end | Write key decisions to learnings |
| **Long** | Hours | 50+ | Multiple subagents + explicit checkpoint/restart. Orchestrator must persist state | **Required** — LearningsStore, session_save, plan artifact re-reads |
| **Multi-session** | Days/weeks | Cross-session | Subagents do scoped work; orchestrator restores from `session-restore` on resume | **Required** — file-backed memory, plan artifacts as source of truth |

**Why this matters:**
- Short tasks don't pay the subagent overhead. A subagent costs ~1,500 tokens of system prompt + tool schema before doing any work. On a 5-turn task, that's 30% of the budget.
- Long tasks *require* subagent delegation because the orchestrator's context window fills up. Subagents keep the noise (full file contents, test output, raw search results) out of the orchestrator's accumulating context.
- Multi-session tasks are where the orchestrator-worker pattern is mandatory. The primary agent may not be the same instance across sessions; the plan artifact and learnings become the shared state.

**Lifetime asymmetry:** The orchestrator is the **long-lived agent**. It accumulates context across the entire session. Subagents are **ephemeral** — one task, one result, gone. This is the fundamental design property that makes the pattern work at scale.

## Model selection by role

**Default rule:** the orchestrator runs on the user's chosen (typically most capable) model. Subagents run on the **cheapest model capable of the specific subtask**. This is the inverse of what people assume — the orchestrator is more expensive, not less.

| Role | Model | Why |
|------|-------|-----|
| **Orchestrator** (primary) | User's choice — usually Sonnet/Opus | Needs full reasoning, long context, judgment calls, synthesis. Lives the whole session. |
| **Read-only research** (subagent) | Haiku | Fast, cheap, plenty capable for "find this in the codebase / look this up on the web" |
| **Code review / test runner** (subagent) | Sonnet | Needs reasoning but not synthesis. Mid-tier. |
| **Synthesis / architecture** (subagent) | Match parent or one tier down | Synthesis is hard; don't degrade below parent tier |
| **Trivial lookup** | **Do not spawn** | Overhead exceeds work. Primary does it inline. |

**The model:`inherit` default in aede is wrong for delegation.** It makes the subagent cost as much as the orchestrator per token, which destroys the cost rationale for delegation. Each agent definition should specify its model explicitly:

```yaml
---
name: explore
description: Read-only codebase research. Use proactively before making changes.
model: claude-haiku-4-5   # NOT inherit
tools: [read_file, glob, search_files, list_dir]
disallowedTools: [powershell, write_file, edit, create_file]
maxTurns: 8
---
```

**Anthropic's production data confirms:** *"Upgrading to Claude Sonnet 4 is a larger performance gain than doubling the token budget on Claude Sonnet 3.7."* Translation: use a capable model on the subtask when the work is non-trivial, but use the cheapest model that can do the job. Don't default everything to the parent's model.

**Platform comparison (why aede supports this):**
- **Claude Code** — agent frontmatter `model: sonnet` overrides the parent. ✅
- **aede** — agent frontmatter `model: claude-haiku-4-5` overrides via `build_sub_cfg()` in `aede/agents/orchestration.py:22-38`. ✅
- **opencode** — subagents always inherit the orchestrator's model. No override. ❌

If the user explicitly requests a model (e.g., "use Haiku for the research subagents"), honor it in the agent definition. Don't fall back to inherit.

## Context window asymmetry

Orchestrators and subagents have **opposite context window needs**. Get this wrong and the system fails at scale.

| Property | Orchestrator | Subagent |
|----------|--------------|----------|
| **Lifetime** | Whole session | One task |
| **Context accumulates?** | Yes — across all user turns, tool calls, decisions | No — fresh context per spawn |
| **Window size needs** | As large as possible (or unlimited via re-injection) | Small and focused — bounded by maxTurns |
| **What's in context** | Goal, plan, decisions so far, user preferences, history of subagent results | Task prompt, output format, minimal relevant data |
| **Compaction strategy** | Preserve goal/plan/todos verbatim; summarize the middle | No compaction needed — fits in one short context |
| **Memory** | Writes to LearningsStore, session files, plan artifacts | Returns summary to orchestrator; writes nothing to shared memory |

**The orchestrator's effective context is longer than its raw window** because of:
- Token-cadence re-injection (aede re-injects goal/plan every ~20K tokens)
- Compaction that preserves the goal/plan/todos verbatim while summarizing the middle
- Plan artifacts and progress files that act as external memory

**Subagents should NOT have long context windows.** A subagent that "remembers too much" will:
- Get confused by the orchestrator's reasoning
- Spend tokens re-deriving what was already known
- Be tempted to take on scope beyond the task
- Violate the "disposable worker" design property

**Practical implications for aede:**

1. **Agent definitions should set `maxTurns` aggressively** — 5–8 for research, 10–15 for code work. The default 20 is too high.
2. **Agent definitions should specify model explicitly** — don't use `model: "inherit"` for subagents.
3. **Orchestrator gets the long-context machinery** — LearningsStore, session_save, plan artifacts, re-injection. Subagents do not.
4. **Compaction only happens in the orchestrator** — subagents should be small enough that they never need it.

## When to delegate

Spawn a subagent when **all** of these are true:

1. **Self-contained with a clear success criterion** — the subtask has a definable "done" state. *"Research how Stripe's webhook signature verification works"* is delegatable. *"Look into webhooks"* is not.
2. **Output would crowd primary context** — long log scraping, full file reads, large test output, raw search results. The subagent's summary returns to primary; the noise stays in the subagent.
3. **A specialized agent exists for this exact subtask** — check the loaded agents (see *Discovering available agents* above). Common examples: `explore` for read-only research, `code-reviewer` for diff review, `test-runner` for pytest output, `security-auditor` for vulnerability scanning. The user's project may have its own custom agents (e.g., a domain-specific `data-pipeline-runner`). Match the task to whatever agent is actually loaded.
4. **No immediate result-chaining required** — primary doesn't need to read the result and immediately use it in the next tool call.
5. **The work is parallelizable** (for parallel dispatch) — N independent investigations with disjoint scopes.

## When NOT to delegate

- **Quick lookups** — *"What port does Postgres default to?"* — inline, no need for the round-trip.
- **Iterative/branching work** — phase N depends on phase N-1's intermediate state. Subagents force a context boundary that breaks the loop.
- **Single-edit tasks** — one tool call, no setup.
- **User-facing clarifications** — subagents can't ask the user questions.
- **Vague exploration** — *"Look into the auth system"* is a recipe for an oversized result.
- **Deep model calls for trivial work** — Opus orchestrator spawning Haiku for a 3-line answer is overhead with no benefit.

## The 5-component task prompt

Every subagent task argument should follow this structure. The primary agent constructs the prompt; you enforce the structure:

```
OBJECTIVE:
{one-sentence goal — what success looks like}

INPUT CONTEXT:
{2-3 lines of what the orchestrator already knows that's relevant}
{file paths the subagent will need, identifiers, project conventions}

OUTPUT FORMAT:
{structured expectation — bulleted list, JSON, prose, file:line refs}
{be explicit about length: "≤ 10 bullets", "first 5 lines of error only"}

CONSTRAINTS:
- {tool preferences or restrictions}
- {scope limits: "only look in src/auth/", "skip SEO content farms"}
- {quality bar: "find 3+ sources minimum", "no unverified claims"}

BOUNDARIES (do NOT do these):
- {anti-scope: "do not modify files", "do not propose architecture changes"}
- {fallback: "if unclear, return 'INSUFFICIENT CONTEXT' rather than guessing"}
```

**Why each component matters:**
- *Objective* — without it, subagents expand scope or miss the goal
- *Input Context* — prevents re-deriving what the orchestrator already knows
- *Output Format* — without this, subagents return 5-page essays
- *Constraints* — enforces tool restrictions, scope, quality bar
- *Boundaries* — explicit anti-scope prevents runaway work

## Anti-patterns (do not generate these)

- **Vague verbs** — "research", "look into", "investigate" without bounded scope
- **Missing output format** — no format instruction → LLM returns an essay
- **Overlapping scopes in parallel** — two subagents investigating "the 2021 chip crisis" → duplicate work
- **Missing success criterion** — subagent doesn't know when to stop
- **Self-referential delegation** — subagent spawns another subagent for the same task
- **No boundaries** — subagent invents new requirements, makes architectural changes

## Cost awareness

Anthropic's research data: **multi-agent systems use ~15× more tokens than chat, ~4× more than single-agent.** Most of aede's personal CLI tasks do NOT justify this cost.

**Delegate when:**
- The work would consume > 20K tokens of primary context that isn't needed downstream
- The work is parallelizable (wall-clock time matters)
- A cheaper model can do the work (Haiku for read-only research)

**Do not delegate when:**
- A subagent would burn max_turns × 4K tokens on a single 3-line answer
- Multiple subagents would each return verbose results that flood the primary
- The work is conversational and primary is already in the right context

The subagent overhead is ~1,500 tokens (system prompt + tool schema + task message). The work it replaces should consume substantially more in primary context for delegation to be a net win.

## Coordination patterns

### Sequential delegation
```
spawn_subagent(explore, task1) → result1
spawn_subagent(explore, task2 using result1) → result2
spawn_subagent(general-purpose, synthesize [result1, result2]) → final
```
Use when subtasks have natural dependencies and you need the synthesis step.

### Parallel dispatch
When 2+ subtasks are independent with disjoint scopes, dispatch them in one `spawn_subagent` call per subtask (aede does not yet have a parallel-primitive tool — issue them in a batch within a single turn so the model fires them together). After all return, treat results as a list:

1. Deduplicate findings
2. Note conflicts explicitly (don't silently pick one)
3. Synthesize into a single structured response
4. Return only the summary to the user

### Citation/aggregation agent
For large parallel research, delegate one final aggregation agent to take N raw outputs and produce a synthesized report. The orchestrator doesn't try to merge in-context.

## Termination contracts

When you construct a subagent task, include an explicit completion signal:

- "When done, return `DONE: <summary>` on its own line"
- "Return only failing tests in the format: `TEST: <name> | FILE: <path>:<line> | ERROR: <first 5 lines>`"
- "End your response with the path of the file you created"

This lets the orchestrator detect completion without re-reading the full transcript.

## Key principles

- **Match agent to task** — `explore` is read-only; never ask it to modify files
- **Pass only what the subagent needs** — file paths, format spec, constraints. Do NOT pass the full conversation history (subagents get a clean context by design)
- **Specify the output format** — the single highest-leverage thing you can do
- **Bound the scope** — directories, time, max file count
- **Surface failures as errors, not strings** — when the result says `max_turns reached` or `spawn rejected`, the orchestrator should treat it as a failure
- **Cost is real** — every subagent costs ~10–40K tokens. Don't delegate what you can do in 1–2 tool calls inline
- **Parallel ≠ always better** — only parallelize when subtasks are truly independent
