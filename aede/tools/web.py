"""
Web tools for aede: HTTP fetch and DuckDuckGo search.

``fetch_url`` retrieves raw non-HTML content from a known URL (raises for
HTML/SPA responses so the model cannot accidentally dump a rendered page).
``web_search`` queries DuckDuckGo via the ``ddgs`` package without requiring
an API key.  Both functions raise ``RuntimeError`` on failure so errors are
returned to the model rather than silently suppressed.
"""
from __future__ import annotations

from aede.sandboxing.prompt_filter import filter_tool_output

_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB


def _validate_url(url: str) -> str:
    """Reject SSRF-vulnerable URLs before any request is made.

    Checks:
      - Only http / https schemes allowed.
      - Hostname resolves to a public IP (not private, loopback, link-local,
        reserved, multicast, or unspecified).

    Raises:
        RuntimeError: if the URL scheme or resolved IP is blocked.
    """
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)
    scheme = parsed.scheme
    if scheme not in ("http", "https"):
        raise RuntimeError(f"Blocked scheme: {scheme!r}. Only http and https are allowed.")

    host = parsed.hostname
    if not host:
        raise RuntimeError("URL has no hostname.")

    try:
        addrinfo = socket.getaddrinfo(host, None)
    except OSError as e:
        raise RuntimeError(f"Cannot resolve hostname {host!r}: {e}")

    for family, _type, _proto, _canonname, sockaddr in addrinfo:
        ip = sockaddr[0]
        if _is_private_ip(ip):
            raise RuntimeError(
                f"Blocked request to internal/private address {ip}. "
                "SSRF protection prevents fetching from non-public networks."
            )

    return host


def _is_private_ip(ip: str) -> bool:
    """Return True if *ip* is not a globally routable public address."""
    import ipaddress

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False

    if addr.version == 4:
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_site_local


def fetch_url(args: dict, sandbox_filter: bool = False) -> str:
    """HTTP GET a URL and return its body as plain text.

    Explicitly raises for HTML pages and Next.js RSC payloads so the model
    cannot read a rendered web page and quote it back at the user.

    Args:
        args: Must contain "url".

    Returns:
        Raw response body text.

    Raises:
        RuntimeError: for HTTP errors, network failures, or HTML/SPA responses.
    """
    import httpx
    url = args["url"]
    _validate_url(url)
    try:
        with httpx.stream("GET", url, timeout=30, follow_redirects=False, headers={
            "User-Agent": "Mozilla/5.0 (compatible; aede/0.1)"
        }) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            chunks = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise RuntimeError(f"Response exceeded 10 MiB size limit for URL: {url}")
                chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8", errors="replace")
        stripped_start = text.strip()[:50]
        is_html = "text/html" in content_type or stripped_start.startswith("<!")
        is_rsc = stripped_start.startswith("0:") or 'self.__next_f' in text[:500]
        if is_html or is_rsc:
            raise RuntimeError(f"URL returned a rendered page (HTML/SPA), not raw data. Use web_search to find a better URL: {url}")
        if sandbox_filter:
            filtered, _matches = filter_tool_output(text, source="fetch_url")
            return filtered
        return text
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP {e.response.status_code}: {url}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Request failed: {e}")


def web_search(args: dict, sandbox_filter: bool = False) -> str:
    """Search the web via DuckDuckGo and return titled results with snippets.

    Args:
        args: Must contain "query"; optionally "count" (default 5).

    Returns:
        Formatted Markdown-style list of [title](url) + snippet, or a
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
        raise RuntimeError(f"web_search backend failed: {e}") from e
    if not results:
        return f"(no results for query: {query!r})"
    lines = []
    for r in results:
        lines.append(f"[{r.get('title', '')}]({r.get('href', '')})")
        if r.get("body"):
            lines.append(r["body"])
        lines.append("")
    result = "\n".join(lines).strip()
    if sandbox_filter:
        filtered, _matches = filter_tool_output(result, source="web_search")
        return filtered
    return result
