# aede — Python House-Style Conventions

> Source of truth: `CLAUDE.md` (project root). This doc expands each rule with
> rationale, examples, and patterns discovered in the codebase.
> UI primitive bypass tracked in: https://github.com/St-vn/aede/issues/29

---

## 1. File Paths — always `pathlib.Path`

**Rule (CLAUDE.md):** "All file paths via `pathlib.Path` — no string concatenation"

Use `Path` for every filesystem reference. Never use `os.path.join()`, f-strings, or plain
string concatenation to build paths.

```python
# WRONG
config_path = data_dir + "/config.json"
config_path = os.path.join(data_dir, "config.json")

# CORRECT
config_path = data_dir / "config.json"
path = Path(args["path"])
content = path.read_text(encoding="utf-8")
```

When receiving a path from the LLM tool-call input dict, always wrap it immediately:

```python
def my_tool(args: dict) -> str:
    path = Path(args["path"])          # wrap at entry point
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")
```

---

## 2. Lazy Heavy Imports

**Rule (CLAUDE.md):** "Heavy imports (`anthropic`, `pydantic`, `rich`) are lazy — inside
functions, not module level"

The `anthropic`, `openai`, `pydantic` (for model definitions), and `rich` packages are
expensive to import. They MUST be imported inside functions or `_get_client()`-style lazy
accessors, not at module level.

```python
# WRONG — slows startup for every subcommand
import anthropic

class AnthropicProvider:
    ...

# CORRECT — imported once, on first use
class AnthropicProvider:
    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client
```

For type annotations that refer to heavy types, use `TYPE_CHECKING`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic   # only at type-check time, not runtime
```

Use `from __future__ import annotations` in every non-trivial module. This defers all
annotation evaluation and avoids circular imports without runtime cost.

---

## 3. Tool Errors Return to the Model

**Rule (CLAUDE.md):** "Tool errors return to the model as results — never hide them"

Tool implementations MUST raise stdlib exceptions on failure. The `ToolRouter` catches all
exceptions and wraps them into `ToolResult(status="error", output=str(e))`, which flows back
to the LLM as an `is_error` tool result. The model reads the error and decides what to do.

```python
# WRONG — hiding errors
def read_file(args: dict) -> str:
    try:
        return Path(args["path"]).read_text()
    except Exception:
        return ""   # silent failure — model never knows

# CORRECT — raise, let ToolRouter surface it
def read_file(args: dict) -> str:
    path = Path(args["path"])
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")
```

Never call `sys.exit()` from a tool. Never swallow exceptions silently.

---

## 4. Tool Name Validation — No Retry on Hallucinated Names

**Rule (CLAUDE.md):** "No retry on hallucinated tool names — reject immediately, re-prompt
with valid list"

When the LLM requests a tool name not in the registry, `ToolRouter.validate_name()` raises
`UnknownToolError`. The agent loop surfaces this immediately without retry and re-prompts the
model with the valid tool list.

```python
# In ToolRouter:
def validate_name(self, name: str) -> None:
    if name not in self._registry:
        raise UnknownToolError(
            f"Unknown tool: {name!r}. Valid tools: {self.tool_names()}"
        )
```

The agent loop then re-injects the error as a user-turn message with the valid list — it does
NOT retry the same turn or call the nearest-match tool as a substitute.

---

## 5. Param Validation — Retry Once

**Rule (CLAUDE.md):** "Retry once on param validation failures with error injected into context"

When required parameters are missing or wrong-typed, `ToolRouter.validate_args()` raises
`ToolParamError`. The agent loop injects this as an `is_error` tool result and allows the model
to retry the same tool call exactly ONCE. A second identical failure aborts the tool call.

Implementation detail (see `agent.py`):

```python
validation_retry: dict[str, int] = {}   # keyed by (tool_name, call_id)

# On ToolParamError:
validation_retry[val_key] = validation_retry.get(val_key, 0) + 1
if validation_retry[val_key] > 1:
    # Abort — model failed twice on the same params
    break
# Otherwise, inject error as tool result and continue
```

---

## 6. Transient API Errors — Retry Up to 3x with Exponential Backoff

**Rule (CLAUDE.md):** "Retry up to 3x on transient API errors (429/500) with exponential
backoff"

The provider layer retries HTTP status codes `{429, 500, 502, 503}` up to 3 attempts total,
with `BACKOFF_BASE = 0.5` seconds and exponential delay between attempts. Non-transient errors
(400, 401, 403, etc.) surface immediately without retry.

```python
BACKOFF_BASE: float = 0.5
_MAX_ATTEMPTS: int = 3
_TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503})

# Attempt N, wait = BACKOFF_BASE * (2 ** (N-1))
# attempt 1 → 0.5s, attempt 2 → 1.0s, attempt 3 → surface error
```

`BACKOFF_BASE` is a module-level constant (not hardcoded) so tests can monkeypatch
`asyncio.sleep` or set it to `0`.

---

## 7. Module-Level Conventions

### `from __future__ import annotations`

Required in every non-trivial module. Enables PEP 563 deferred annotation evaluation —
annotations are stored as strings, not evaluated at import time. Removes need for
string-quoted forward references.

### `if TYPE_CHECKING:` for annotation-only imports

Imports used only in type hints go under `if TYPE_CHECKING:`. This prevents circular imports
and keeps startup fast.

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from aede.db import DB
```

### Module docstrings

Every non-trivial module MUST have a module-level docstring explaining what the module does,
what its main class/function is, and any important invariants.

---

## 8. Math Notation

**Rule (CLAUDE.md):** "Always use `$$` for display math and `$` for inline math via standard
LaTeX delimiters."

When generating output that contains mathematical notation, use KaTeX/MathJax conventions:

- Inline math: `$x^2 + y^2 = r^2$`
- Display math: `$$\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}$$`

The UI renders KaTeX — assume it works unless told otherwise.

---

## 9. Error Classes

The codebase defines two tool-error exception types in `aede/tools/router.py`:

| Exception | When to raise | Agent behaviour |
|-----------|--------------|-----------------|
| `UnknownToolError` | Tool name not in registry | Reject, no retry, re-prompt |
| `ToolParamError` | Required param missing/wrong type | Inject as error result, retry once |

All other tool errors use stdlib exceptions (`FileNotFoundError`, `ValueError`, `OSError`,
`PermissionError`, etc.) — these get caught by `ToolRouter.execute_sync()` and wrapped into
`ToolResult(status="error")`.

---

## 10. UI Primitives (TypeScript/React)

> This section covers the front-end conventions audited in holistic audit WP-2.

**Rule:** Use shadcn/ui primitives from `ui/components/ui/` for all interactive elements.
Never use raw HTML elements when a primitive exists.

| Raw element | Primitive | Import |
|-------------|-----------|--------|
| `<button>` | `<Button>` | `@/components/ui/button` |
| `<input>` (text/password/email) | `<Input>` | `@/components/ui/input` |
| `<input type="checkbox">` | `<Checkbox>` | `@/components/ui/checkbox` |
| `<input type="radio">` | `<RadioGroup>` | `@/components/ui/radio-group` |
| `<dialog>` | `<Dialog>` | `@/components/ui/dialog` |

**Exceptions:**
- `<input type="file">` with `className="hidden"` (programmatically triggered) — no visual
  primitive applies.
- Buttons passed as `render=` prop to Base UI triggers can use `<Button render={...}>` — the
  Button primitive accepts arbitrary render props.
- Buttons inside `<CommandEmpty>` need `<CommandItem>` semantics, not `<Button>`.

**Button variants** (`ui/components/ui/button.tsx`):

| Variant | Use case |
|---------|----------|
| `default` | Primary action (submit, save) |
| `outline` | Secondary action, toggled state |
| `secondary` | Muted primary (less emphasis than default) |
| `ghost` | Icon buttons, toolbar actions, list-row actions |
| `destructive` | Delete / irreversible actions |
| `link` | Inline text links within prose |

**Button sizes:**

| Size | px height | Use case |
|------|-----------|----------|
| `default` | 32px | Standard |
| `sm` | 28px | Settings panels, compact lists |
| `xs` | 24px | Dense UI, badges |
| `lg` | 36px | Prominent CTAs |
| `icon` | 32px square | Icon-only buttons |
| `icon-sm` | 28px square | Common icon action buttons |
| `icon-xs` | 24px square | Chip remove buttons, mini icons |
| `icon-lg` | 36px square | Large icon buttons |
