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
        if "javascript" in content_type or response.text.strip().startswith("<script"):
            return f"[JS-rendered page — raw content returned, may be incomplete]\n\n{response.text}"
        return response.text
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP {e.response.status_code}: {url}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Request failed: {e}")


def web_search(args: dict, api_key: str = "") -> str:
    import httpx
    query = args["query"]
    count = int(args.get("count", 5))
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": count}
    try:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return "(no results)"
        lines = []
        for r in results:
            lines.append(f"[{r.get('title', '')}]({r.get('url', '')})")
            if r.get("description"):
                lines.append(r["description"])
            lines.append("")
        return "\n".join(lines).strip()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Brave Search API error: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Brave Search request failed: {e}")
