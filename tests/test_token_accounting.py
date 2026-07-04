"""Tests for shared token-accounting helpers."""

from __future__ import annotations

import pytest

from archolith_maintenance import count_message_content_tokens, count_text_tokens
from archolith_maintenance import token_accounting


def test_count_text_tokens_matches_tiktoken_when_available():
    enc = token_accounting._get_encoding("cl100k_base")
    text = "hello world"

    tokens = count_text_tokens(text)

    if enc is None:
        assert tokens == token_accounting.estimate_tokens_fallback(text)
    else:
        assert tokens == len(enc.encode(text))


def test_count_text_tokens_preserves_surface_minimum():
    assert count_text_tokens("", minimum=1) == 1
    assert count_text_tokens("hello", minimum=500) == 500


def test_count_text_tokens_can_force_fallback_even_when_tiktoken_exists():
    text = "def run(value: int) -> int:\n    return value + 1\n"

    assert count_text_tokens(text, mode="fallback") == token_accounting.estimate_tokens_fallback(text)
    assert token_accounting.token_counts_are_estimated(mode="fallback") is True


def test_count_text_tokens_can_require_tiktoken_when_available():
    enc = token_accounting._get_encoding("cl100k_base")
    text = "hello world"

    if enc is None:
        with pytest.raises(RuntimeError):
            count_text_tokens(text, mode="tiktoken")
    else:
        assert count_text_tokens(text, mode="tiktoken") == len(enc.encode(text))
        assert token_accounting.token_counts_are_estimated(mode="tiktoken") is False


def test_count_text_tokens_rejects_unknown_mode():
    with pytest.raises(ValueError):
        count_text_tokens("hello", mode="bad")


def test_fallback_estimator_is_more_conservative_for_code(monkeypatch):
    monkeypatch.setattr(token_accounting, "_get_encoding", lambda encoding: None)
    code = "def run(value: int) -> int:\n    return value + 1\n"
    prose = "This is a normal sentence with simple English words."

    assert count_text_tokens(code) > len(code) // 4
    assert count_text_tokens(prose) == len(prose) // 4
    assert token_accounting.token_counts_are_estimated() is True


def test_count_message_content_tokens_counts_strings_and_parts(monkeypatch):
    monkeypatch.setattr(token_accounting, "_get_encoding", lambda encoding: None)
    messages = [
        {"role": "user", "content": "abcd"},
        {"role": "assistant", "content": [{"type": "text", "text": "abcdefgh"}]},
        {"role": "tool", "content": None},
    ]

    assert count_message_content_tokens(messages) == 3
