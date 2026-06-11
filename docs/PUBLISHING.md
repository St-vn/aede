---
type: doc
tags: [docs, publishing]
date_updated: 2026-06-10
---

# Publishing docs to GitHub Pages

## Current setup (zero build step)

This repo uses GitHub Pages with the `/docs` folder on `main` branch as source:

1. **GitHub repo → Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, folder: `/docs`
4. URL: `https://<org>.github.io/aede/`

No build step needed — markdown renders natively via GitHub's built-in Pages support. Relative links (`[link](features/tools.md)`) work automatically.

## MkDocs (future polish)

When you want a sidebar, search, and dark mode:

```bash
pip install mkdocs mkdocs-material
mkdocs new .
# Edit mkdocs.yml with nav structure
# Deploy via GitHub Action: mhausenblend/mkdocs-deploy-gh-pages
```

Add `mkdocs.yml` at repo root, a GitHub Action to `deploy.yml`, and switch Pages source to "GitHub Actions".

## Notes

- `llms.txt` and `llms-full.txt` are for LLM context ingestion — they must be regenerated when docs change
- Internal docs in `docs-internal/` are **not** published (only `docs/` is)
- `docs/adr/`, `docs/kaizen/`, `docs/plans/`, `docs/sdlc-engineer/` are internal — they publish because they live under `docs/`, but aren't linked from the index
