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
        # JS-rendered SPA: returns 200 with HTML even for missing routes
        if "text/html" in content_type or text.strip().startswith("<!"):
            # Try to extract visible text — return first 2000 chars as hint
            import re
            stripped = re.sub(r"<[^>]+>", " ", text)
            stripped = re.sub(r"\s+", " ", stripped).strip()
            if len(stripped) < 200:
                raise RuntimeError(f"Page returned HTML with no useful content (likely JS-rendered or error page): {url}")
            return f"[HTML page — JS-rendered or static HTML, extracting visible text]\n\n{stripped[:3000]}"
        return text
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
