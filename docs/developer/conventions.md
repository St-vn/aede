---
type: doc
tags: [docs, developer]
date_updated: 2026-06-10
---

# Code Conventions

## File Paths

All file paths use `pathlib.Path` — never string concatenation. This ensures cross-platform correctness and cleaner path manipulation.

## Lazy Imports

Heavy dependencies (`anthropic`, `pydantic`, `rich`) are imported inside functions, not at module level. This keeps startup time fast and prevents import errors when optional features are not used.

```python
# Good
def get_critic_provider(cfg):
    from aede.provider import get_provider
    return get_provider(cfg)

# Avoid
from aede.provider import get_provider  # at module top level
```

## Tool Errors

Tool errors are always returned to the model as `ToolResult(status="error")` — never hidden or swallowed. The model decides whether to retry or report failure.

## No Retry on Hallucinated Tool Names

If the model requests a tool that doesn't exist, the error is returned immediately without retry. An unknown name cannot become valid by retrying.

## Param Validation

Tool parameters are validated via Pydantic JSON schema matching. On failure, the agent gets one retry with the error injected into context.

## API Retries

Transient API errors (429, 500, 502, 503) are retried up to 3 times with exponential backoff (0.5s, 1s, 2s). Non-transient errors are surfaced immediately.

## Response Format

When the agent produces markdown code blocks, they follow these guidelines:

- Code blocks specify a language identifier
- Tool output is synthesized and summarized, not quoted verbatim
- HTML page content is extracted for relevant facts, not pasted back
