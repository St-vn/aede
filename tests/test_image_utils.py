import pytest
from aede.image_utils import parse_image_content, normalize_messages_for_provider


# ── parse_image_content tests ─────────────────────────────────────────────


def test_pure_text_single_block():
    result = parse_image_content("Hello, world!")
    assert result == [{"type": "text", "text": "Hello, world!"}]


def test_single_image_with_alt_text():
    result = parse_image_content(
        "Look at this ![diagram](data:image/png;base64,iVBORw0KGgo=)"
    )
    assert result == [
        {"type": "text", "text": "Look at this "},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": "iVBORw0KGgo=",
            },
        },
    ]


def test_image_without_alt():
    result = parse_image_content(
        "![](data:image/jpeg;base64,/9j/4AAQSkZJRg=)"
    )
    assert result == [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": "/9j/4AAQSkZJRg=",
            },
        },
    ]


def test_text_before_and_after_image():
    result = parse_image_content(
        "Before\n![img](data:image/gif;base64,R0lGODlhAQAB=)\nAfter"
    )
    assert result == [
        {"type": "text", "text": "Before\n"},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/gif",
                "data": "R0lGODlhAQAB=",
            },
        },
        {"type": "text", "text": "\nAfter"},
    ]


def test_multiple_images():
    result = parse_image_content(
        "A ![one](data:image/png;base64,AAAA) B ![two](data:image/png;base64,BBBB) C"
    )
    assert result == [
        {"type": "text", "text": "A "},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": "AAAA",
            },
        },
        {"type": "text", "text": " B "},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": "BBBB",
            },
        },
        {"type": "text", "text": " C"},
    ]


def test_no_images_in_input():
    result = parse_image_content("[link](https://example.com) plain text")
    assert result == [
        {"type": "text", "text": "[link](https://example.com) plain text"}
    ]


def test_mixed_image_and_non_image_links():
    result = parse_image_content(
        "[docs](https://docs.example.com) ![pic](data:image/webp;base64,UklGRg==) [more](https://more.example.com)"
    )
    assert result == [
        {"type": "text", "text": "[docs](https://docs.example.com) "},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/webp",
                "data": "UklGRg==",
            },
        },
        {"type": "text", "text": " [more](https://more.example.com)"},
    ]


def test_malformed_data_url_missing_base64():
    result = parse_image_content("![bad](data:image/png,fake)")
    assert result == [{"type": "text", "text": "![bad](data:image/png,fake)"}]


def test_empty_input():
    result = parse_image_content("")
    assert result == []


# ── normalize_messages_for_provider tests ──────────────────────────────────


def test_normalize_string_content_to_blocks():
    messages = [{"role": "user", "content": "Hello ![img](data:image/png;base64,AAAA)"}]
    result = normalize_messages_for_provider(messages)
    assert result == [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello "},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}},
        ]
    }]


def test_normalize_pure_text_stays_as_text_block():
    messages = [{"role": "user", "content": "Hello world"}]
    result = normalize_messages_for_provider(messages)
    assert result == [{"role": "user", "content": [{"type": "text", "text": "Hello world"}]}]


def test_normalize_list_content_passthrough():
    messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
    result = normalize_messages_for_provider(messages)
    assert result == messages


def test_normalize_does_not_mutate_input():
    messages = [{"role": "user", "content": "original"}]
    result = normalize_messages_for_provider(messages)
    assert result is not messages
    assert messages[0]["content"] == "original"  # input unchanged


def test_normalize_empty_string():
    messages = [{"role": "user", "content": ""}]
    result = normalize_messages_for_provider(messages)
    assert result == [{"role": "user", "content": [{"type": "text", "text": ""}]}]
