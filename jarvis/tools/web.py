"""
Web tools for Jarvis: HTTP fetch and DuckDuckGo search.

``fetch_url`` retrieves raw non-HTML content from a known URL (raises for
HTML/SPA responses so the model cannot accidentally dump a rendered page).
``web_search`` queries DuckDuckGo via the ``ddgs`` package without requiring
an API key.  Both functions raise ``RuntimeError`` on failure so errors are
returned to the model rather than silently suppressed.
"""
from __future__ import annotations


def fetch_url(args: dict) -> str:
    """HTTP GET a URL and return its body as plain text.

    Explicitly raises for HTML pages and Next.js RSC payloads so the model
    cannot read a rendered web page and quote it back at the user.

    Args:
        args: Must contain ``"url"``.

    Returns:
        Raw response body text.

    Raises:
        RuntimeError: for HTTP errors, network failures, or HTML/SPA responses.
    """
    import httpx
    url = args["url"]
    try:
        response = httpx.get(url, timeout=30, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Jarvis/0.1)"
        })
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        text = response.text
        stripped_start = text.strip()[:50]
        is_html = "text/html" in content_type or stripped_start.startswith("<!")
        is_rsc = stripped_start.startswith("0:") or 'self.__next_f' in text[:500]
        if is_html or is_rsc:
            raise RuntimeError(f"URL returned a rendered page (HTML/SPA), not raw data. Use web_search to find a better URL: {url}")
        return text
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP {e.response.status_code}: {url}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Request failed: {e}")


def web_search(args: dict) -> str:
    """Search the web via DuckDuckGo and return titled results with snippets.

    Args:
        args: Must contain ``"query"``; optionally ``"count"`` (default 5).

    Returns:
        Formatted Markdown-style list of ``[title](url)`` + snippet, or a
        no-results message if the query returns nothing.

    Raises:
        RuntimeError: if the DuckDuckGo backend call fails.
    """
    from ddgs import DDGS
    query = args["query"]
    count = int(args.get("count", 5))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=count))
    except Exception as e:
        # Surface backend failure as an error result — never silently return
        # "(no results)", which the model cannot distinguish from a genuine
        # empty result set.
        raise RuntimeError(f"web_search backend failed: {e}") from e
    if not results:
        return f"(no results for query: {query!r})"
    lines = []
    for r in results:
        lines.append(f"[{r.get('title', '')}]({r.get('href', '')})")
        if r.get("body"):
            lines.append(r["body"])
        lines.append("")
    return "\n".join(lines).strip()
