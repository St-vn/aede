import pytest
from aede.observability.redact import redact_value

SAMPLE_API_KEY = "sk-ant-abc123def456"
SAMPLE_EMAIL = "user@example.com"
SAMPLE_HOME_PATH = "~/Documents/project/file.txt"
SAMPLE_CREDIT_CARD = "4111-1111-1111-1111"
SAMPLE_SSN = "123-45-6789"


class TestRedactSecretPatterns:
    def test_api_key_redacted(self):
        result = redact_value(SAMPLE_API_KEY)
        assert result != SAMPLE_API_KEY
        assert "sk-ant" not in result

    def test_email_redacted(self):
        result = redact_value(SAMPLE_EMAIL)
        assert result != SAMPLE_EMAIL
        assert "@" not in result

    def test_home_path_redacted(self):
        result = redact_value(SAMPLE_HOME_PATH)
        assert result != SAMPLE_HOME_PATH
        assert "~/Documents" not in result

    def test_credit_card_redacted(self):
        result = redact_value(SAMPLE_CREDIT_CARD)
        assert result != SAMPLE_CREDIT_CARD

    def test_ssn_redacted(self):
        result = redact_value(SAMPLE_SSN)
        assert result != SAMPLE_SSN

    def test_short_safe_string_passes_through(self):
        val = "hello world"
        assert redact_value(val) == val

    def test_non_string_passes_through(self):
        assert redact_value(42) == 42
        assert redact_value(3.14) == 3.14
        assert redact_value(True) is True
        assert redact_value(None) is None


class TestRedactInDicts:
    def test_nested_dict_redacted(self):
        data = {"user": {"email": SAMPLE_EMAIL, "name": "Alice"}}
        result = redact_value(data)
        assert "@" not in str(result)
        assert result["user"]["name"] == "Alice"

    def test_list_of_strings_redacted(self):
        data = ["safe", SAMPLE_API_KEY, "also safe"]
        result = redact_value(data)
        assert result[0] == "safe"
        assert "sk-ant" not in str(result[1])
        assert result[2] == "also safe"

    def test_list_of_dicts_redacted(self):
        data = [{"key": SAMPLE_API_KEY}, {"key": "safe"}]
        result = redact_value(data)
        assert "sk-ant" not in str(result[0]["key"])
        assert result[1]["key"] == "safe"

    def test_mixed_depth(self):
        data = {
            "config": {
                "api_key": SAMPLE_API_KEY,
                "endpoint": "https://api.example.com",
                "users": [
                    {"email": SAMPLE_EMAIL, "role": "admin"},
                    {"email": "other@test.com", "role": "viewer"},
                ],
            },
            "metadata": {"version": "1.0"},
        }
        result = redact_value(data)
        assert "sk-ant" not in str(result)
        assert "@" not in str(result)
        assert result["metadata"]["version"] == "1.0"
        assert result["config"]["endpoint"] == "https://api.example.com"


class TestRedactAllowDenyLists:
    def test_allowlist_key_not_redacted(self):
        data = {"email": SAMPLE_EMAIL, "name": "Bob"}
        result = redact_value(data, allowlist=["email"])
        assert result["email"] == SAMPLE_EMAIL

    def test_denylist_key_always_redacted(self):
        data = {"title": "My API Key", "description": SAMPLE_API_KEY}
        result = redact_value(data, denylist=["description"])
        assert result["title"] == "My API Key"
        assert result["description"] != SAMPLE_API_KEY

    def test_allowlist_wins_over_heuristic(self):
        data = {"email": SAMPLE_EMAIL}
        result = redact_value(data, allowlist=["email"])
        assert result["email"] == SAMPLE_EMAIL


class TestRedactEdgeCases:
    def test_empty_dict(self):
        assert redact_value({}) == {}

    def test_empty_list(self):
        assert redact_value([]) == []

    def test_empty_string(self):
        assert redact_value("") == ""

    def test_very_long_string(self):
        long = "a" * 10000 + SAMPLE_API_KEY + "b" * 10000
        result = redact_value(long)
        assert result != long
        assert len(result) < len(long)

    def test_original_not_mutated(self):
        original = {"key": SAMPLE_API_KEY}
        copy_before = original["key"]
        redact_value(original)
        assert original["key"] == copy_before
