from __future__ import annotations

import tiktoken

_ENCODING = None


def _encoding():
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text or ""))


def count_message_tokens(messages: list[dict]) -> int:
    # +4 tokens/message overhead approximation (role/name/separator tokens),
    # following the OpenAI chat-format counting convention. This is an
    # approximation of whatever model is actually configured, not its exact
    # tokenizer — see hestia/domain/chat/context_budget.py for the safety
    # margin this is paired with.
    return sum(count_tokens(m.get("content", "")) + 4 for m in messages)
