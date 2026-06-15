from __future__ import annotations
import base64
import re
from typing import Any

INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions|commands|directions)", re.IGNORECASE),
    re.compile(r"(?m)^\s*system:"),
    re.compile(r"(?m)^\s*assistant:"),
    re.compile(r"now you are a helpful assistant", re.IGNORECASE),
    re.compile(r"you are now (a different agent|an? (ai )?assistant)", re.IGNORECASE),
    re.compile(r"with no restrictions|without (any )?restrictions", re.IGNORECASE),
    re.compile(r"disregard (all )?previous", re.IGNORECASE),
    re.compile(r"do not follow|do not obey", re.IGNORECASE),
    re.compile(r"print\s+(pwned|hacked|owned)", re.IGNORECASE),
]

BASE64_THRESHOLD = 120


def _looks_like_base64(s: str) -> bool:
    if len(s) < BASE64_THRESHOLD:
        return False
    non_alnum = sum(1 for c in s if not c.isalnum() and c not in "+/=")
    return non_alnum / max(len(s), 1) < 0.15


def _extract_text_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            fence = line.strip()
            lang = fence[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({"type": "code", "lang": lang, "content": "\n".join(code_lines)})
            i += 1
        else:
            text_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                text_lines.append(lines[i])
                i += 1
            blocks.append({"type": "text", "content": "\n".join(text_lines)})
    if not blocks and text.strip():
        blocks.append({"type": "text", "content": text})
    return blocks


def filter_content(text: str | None, return_log: bool = False) -> str | tuple[str, list[str]]:
    if not text:
        return ("" if not return_log else ("", [])) if not return_log else ("" if not return_log else ("", []))
    log: list[str] = []
    blocks = _extract_text_blocks(text)
    filtered_blocks: list[str] = []
    for block in blocks:
        content = block["content"]
        if block["type"] == "code":
            content_stripped = content.strip()
            for pat in INJECTION_PATTERNS:
                if pat.search(content_stripped):
                    summary = content_stripped[:80].replace("\n", " ")
                    log.append(f"removed injection code block: {summary!r}")
                    content = ""
                    break
        if content:
            for pat in INJECTION_PATTERNS:
                match = pat.search(content)
                if match:
                    log.append(f"injection pattern matched: {pat.pattern!r}")
                    content = pat.sub("", content)
            content_lines: list[str] = []
            for line in content.splitlines():
                stripped = line.strip()
                if _looks_like_base64(stripped):
                    log.append(f"removed base64 blob ({len(stripped)} chars)")
                    continue
                content_lines.append(line)
            content = "\n".join(content_lines)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()
        if content:
            filtered_blocks.append(content)
    result = "\n\n".join(filtered_blocks) if filtered_blocks else ""
    if return_log:
        return result, log
    return result
