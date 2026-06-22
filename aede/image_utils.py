import re

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((data:image/([^;]+);base64,([^)]+))\)")


def parse_image_content(user_input: str) -> list[dict]:
    if not user_input:
        return []

    blocks = []
    last_end = 0

    for m in _IMAGE_RE.finditer(user_input):
        start = m.start()
        end = m.end()

        text_before = user_input[last_end:start]
        if text_before:
            blocks.append({"type": "text", "text": text_before})

        data_uri = m.group(2)
        media_type = m.group(3)
        b64_data = m.group(4)

        if ";base64," not in data_uri or not media_type or not b64_data:
            blocks.append({"type": "text", "text": m.group(0)})
        else:
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{media_type}",
                        "data": b64_data,
                    },
                }
            )

        last_end = end

    if last_end == 0:
        blocks.append({"type": "text", "text": user_input})
    else:
        remaining = user_input[last_end:]
        if remaining:
            blocks.append({"type": "text", "text": remaining})

    return blocks


def normalize_messages_for_provider(messages: list[dict]) -> list[dict]:
    """Convert message content from plain strings to content blocks.
    
    For each message in *messages*, if ``content`` is a string call
    :func:`parse_image_content` to produce a list of text/image blocks.
    Messages with list content are passed through unchanged.
    
    Returns a new list — does not mutate the input.
    """
    result = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            blocks = parse_image_content(content)
            if not blocks:
                blocks = [{"type": "text", "text": content}]
            result.append({"role": m["role"], "content": blocks})
        else:
            result.append(m)
    return result
