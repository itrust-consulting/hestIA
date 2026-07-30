from __future__ import annotations

from hestia.domain.chat.tokens import count_message_tokens, count_tokens


class TestCountTokens:

    def test_empty_string_is_zero(self):
        assert count_tokens("") == 0

    def test_none_is_zero(self):
        assert count_tokens(None) == 0

    def test_nonempty_string_is_positive(self):
        assert count_tokens("hello world") > 0

    def test_longer_text_has_more_tokens(self):
        short = count_tokens("hello")
        long = count_tokens("hello " * 50)
        assert long > short


class TestCountMessageTokens:

    def test_empty_list_is_zero(self):
        assert count_message_tokens([]) == 0

    def test_includes_per_message_overhead(self):
        one = count_message_tokens([{"role": "user", "content": ""}])
        two = count_message_tokens([{"role": "user", "content": ""}, {"role": "assistant", "content": ""}])
        # each empty-content message still costs the fixed per-message overhead
        assert one == 4
        assert two == 8

    def test_sums_content_plus_overhead(self):
        messages = [{"role": "user", "content": "hello world"}]
        assert count_message_tokens(messages) == count_tokens("hello world") + 4
