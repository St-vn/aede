# Conventions — moved

The canonical convention system lives at (gitignored, internal only):

> **`docs-internal/sdlc-engineer/conventions/`** — start at `index.md`

That is the path every sdlc-engineer skill (`/implement`, `/modify`,
`/execute-subagent`, `/review-spec`, `/finish-branch`) is pointed at via `CLAUDE.md`.
Kept in `docs-internal/` (not the public `docs/` folder) so it doesn't ship.

Reuse-first inventories (the anti-duplication docs):
- `docs-internal/sdlc-engineer/conventions/component-inventory.md` — UI components/hooks
- `docs-internal/sdlc-engineer/conventions/module-map.md` — backend class families

UI / design source of truth (read by `ui-ux-pro-max`):
- `docs-internal/brand-guidelines.md`
- `docs-internal/design-system.md`

`.sdlc/project.yml` remains the sdlc-engineer project config (tier, gates, tools).
