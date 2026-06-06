from __future__ import annotations


def fetch_url(args: dict) -> str:
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
