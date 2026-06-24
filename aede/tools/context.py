"""P0.4 — select_context fans out to 4 sources; helpers are private."""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from aede.db import DB

_log = logging.getLogger(__name__)

_DOC_EXTS = ("*.md", "*.mdx", "*.txt")
_DOC_ROOTS = ("docs", "docs-internal")
_PREVIEW = 500


def _docs_indexer(query: str, k: int, project_dir: Path, db: "DB") -> list[str]:
    """Walk docs/ + docs-internal/, (re)build FTS5 index on (mtime,size) change, query top-k.

    Returns "[<path>] <content preview>" lines; [] if no docs dirs or no FTS hits.
    """
    project_dir = Path(project_dir)
    files: list[Path] = []
    for r in _DOC_ROOTS:
        root = project_dir / r
        if root.exists():
            for ext in _DOC_EXTS:
                files.extend(root.rglob(ext))

    if not files:
        return []

    current: dict[str, tuple[int, int]] = {}
    for f in files:
        try:
            st = f.stat()
        except OSError:
            continue
        current[str(f.relative_to(project_dir))] = (int(st.st_mtime), int(st.st_size))

    cached = {r["path"]: (int(r["mtime"]), int(r["size"]))
              for r in db.con.execute("SELECT path, mtime, size FROM docs").fetchall()}

    if current != cached:
        db.con.execute("DELETE FROM docs")
        for rel, (mtime, size) in current.items():
            try:
                content = (project_dir / rel).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            db.con.execute(
                "INSERT OR REPLACE INTO docs (path, mtime, size, content) VALUES (?,?,?,?)",
                (rel, mtime, size, content),
            )
        db.con.commit()

    safe_terms = " ".join(f'"{t}"' for t in query.split() if len(t.strip()) > 1)
    if not safe_terms:
        return []
    try:
        rows = db.con.execute(
            "SELECT d.path, d.content FROM docs d JOIN docs_fts f ON d.rowid=f.rowid "
            "WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe_terms, int(k)),
        ).fetchall()
    except Exception:
        _log.warning("docs FTS5 query failed", exc_info=True)
        return []
    return [f"[{r['path']}] {r['content'][:_PREVIEW]}" for r in rows]


def _docs_source(query: str, k: int, project_dir: Path, db: "DB") -> list[str]:
    """Return top-k doc hits via _docs_indexer."""
    return _docs_indexer(query=query, k=k, project_dir=project_dir, db=db)


def _learnings_source(query: str, k: int, db: "DB") -> list[str]:
    """Return top-k learnings as formatted blocks; relies on hybrid_retrieve's Ollama-down fallback."""
    from aede.memory.retrieval import hybrid_retrieve
    rows = hybrid_retrieve(query=query, db=db, k=k, trusted_only=True)
    return [f"[learning] {r['content']}" for r in rows]





def _sessions_source(query: str, k: int, db: "DB") -> list[str]:
    """Return top-k session-message groups as formatted multi-line blocks."""
    groups = db.search_messages(query=query, limit=k)
    if not groups:
        return []
    blocks: list[str] = []
    for i, g in enumerate(groups, 1):
        lines = [
            f"--- Result {i} | session: {g['session_id']} "
            f"| title: {g['session_title']!r} ---",
            "  [context window (\u00b15 messages around hit)]",
        ]
        for m in g["context"]:
            marker = " <-- HIT" if m["id"] == g["hit"]["id"] else ""
            lines.append(f"  [{m['role']}] {m['content']}{marker}")
        if g["bookends"]:
            lines.append("  [session bookends]")
            for m in g["bookends"]:
                lines.append(f"  [{m['role']}] {m['content']}")
        blocks.append("\n".join(lines))
    return blocks


def _files_source(query: str, k: int, project_dir: Path) -> list[str]:
    """Return top-k file matches via ripgrep; rg output -> list of file:line:content lines."""
    from aede.tools.search import search_files
    raw = search_files({"pattern": query, "path": str(project_dir)})
    if not raw or raw == "(no matches)":
        return []
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    return lines[:k]


import concurrent.futures

ALL_SOURCES: tuple[str, ...] = ("learnings", "sessions", "docs", "files")
DEFAULT_K: int = 5
MIN_K: int = 1
MAX_K: int = 20
_VALID_SOURCES: frozenset[str] = frozenset(ALL_SOURCES)


def select_context(
    args: dict, *, db: "DB", data_dir: Path, project_dir: Path,
) -> str:
    """Fan out to selected sources in parallel; return sectioned markdown.

    Returns '## Source: <name> (<n>)' per non-empty source in
    fixed order. '(no sources selected)' if sources=[] or all empty.
    """
    from aede.tools.router import ToolParamError

    query: str = args.get("query", "")
    sources_raw = args.get("sources")
    sources: list[str] = list(sources_raw) if sources_raw is not None else list(ALL_SOURCES)
    k: int = int(args.get("k", DEFAULT_K))

    bad = [s for s in sources if s not in _VALID_SOURCES]
    if bad:
        raise ToolParamError(f"select_context: invalid source(s) {bad}. Valid sources: {sorted(_VALID_SOURCES)}")
    if not (MIN_K <= k <= MAX_K):
        raise ToolParamError(f"select_context: invalid k={k}. Allowed range: {MIN_K}-{MAX_K}")

    if not sources:
        return "(no sources selected)"

    base = max(MIN_K, k // len(sources))
    per_source_k = [base] * len(sources)
    for i in range(k - base * len(sources)):
        per_source_k[i % len(sources)] += 1

    def _runner(src: str, n: int) -> tuple[str, list[str]]:
        try:
            if src == "learnings":   return src, _learnings_source(query, n, db)
            if src == "sessions":    return src, _sessions_source(query, n, db)
            if src == "docs":        return src, _docs_source(query, n, project_dir, db)
            if src == "files":       return src, _files_source(query, n, project_dir)
        except Exception as exc:
            return src, [f"[error: {exc}]"]
        return src, []

    results: dict[str, list[str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_runner, s, per_source_k[i]): s for i, s in enumerate(sources)}
        for fut in concurrent.futures.as_completed(futures):
            src, blocks = fut.result()
            results[src] = blocks

    parts: list[str] = []
    for src in ALL_SOURCES:
        if src not in sources:
            continue
        blocks = results.get(src, [])
        if blocks:
            parts.append(f"## Source: {src} ({len(blocks)})")
            parts.append("")
            parts.extend(blocks)
            parts.append("")

    if not parts:
        return "(no sources selected)"
    return "\n".join(parts).rstrip()
