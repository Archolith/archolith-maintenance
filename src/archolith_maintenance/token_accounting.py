"""Shared token accounting helpers for Archolith projects.

This module owns the canonical text-token fallback policy. Consumers may layer
surface-specific framing, floors, margins, or telemetry around these helpers,
but should not reimplement tokenizer selection or char-heuristic fallback.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Literal

TokenCountingMode = Literal["auto", "tiktoken", "fallback"]

_PROSE_CHARS_PER_TOKEN = 4.0
_CODE_CHARS_PER_TOKEN = 3.2
_CODE_KEYWORD_RE = re.compile(
    r"\b(?:class|def|function|const|let|var|import|from|return|if|else|for|while|try|except|async|await)\b"
)
_CODE_SYMBOLS = frozenset("{}[]();=<>|&")


@lru_cache(maxsize=8)
def _get_encoding(encoding: str):
    """Return a cached tiktoken encoding, or None when unavailable."""
    try:
        import tiktoken

        return tiktoken.get_encoding(encoding)
    except Exception:
        return None


def token_counts_are_estimated(
    encoding: str = "cl100k_base",
    *,
    mode: TokenCountingMode = "auto",
) -> bool:
    """Return True when token counts for ``encoding`` use the fallback heuristic."""
    if mode == "fallback":
        return True
    if mode == "tiktoken":
        if _get_encoding(encoding) is None:
            raise RuntimeError(f"tiktoken encoding {encoding!r} is required but unavailable")
        return False
    if mode != "auto":
        raise ValueError(f"unknown token counting mode: {mode!r}")
    return _get_encoding(encoding) is None


def looks_code_like(text: str) -> bool:
    """Return True for code/config-heavy text that needs a tighter fallback ratio."""
    if not text:
        return False
    newline_count = text.count("\n")
    symbol_count = sum(1 for ch in text if ch in _CODE_SYMBOLS)
    symbol_ratio = symbol_count / max(1, len(text))
    return (
        (newline_count >= 2 and bool(_CODE_KEYWORD_RE.search(text)))
        or symbol_ratio >= 0.08
        or "```" in text
    )


def estimate_tokens_fallback(text: str | None) -> int:
    """Estimate tokens without tiktoken.

    Prose keeps the historical 4 chars/token heuristic. Code and
    punctuation-heavy content use a more conservative 3.2 chars/token estimate
    to reduce over-budget errors in standalone installs.
    """
    if not text:
        return 0
    if looks_code_like(text):
        return max(1, math.ceil(len(text) / _CODE_CHARS_PER_TOKEN))
    return max(1, len(text) // int(_PROSE_CHARS_PER_TOKEN))


def count_text_tokens(
    text: str | None,
    *,
    encoding: str = "cl100k_base",
    minimum: int = 0,
    mode: TokenCountingMode = "auto",
) -> int:
    """Count text tokens with tiktoken, falling back to the shared heuristic.

    ``minimum`` lets callers preserve surface-specific floors without changing
    the canonical tokenizer/fallback policy. ``mode`` controls tokenizer
    selection:

    - ``"auto"`` uses tiktoken when available, else the fallback heuristic.
    - ``"tiktoken"`` requires tiktoken and raises if unavailable.
    - ``"fallback"`` always uses the heuristic.
    """
    if not text:
        return max(0, minimum)
    if mode == "fallback":
        return max(minimum, estimate_tokens_fallback(text))
    enc = _get_encoding(encoding)
    if mode == "tiktoken" and enc is None:
        raise RuntimeError(f"tiktoken encoding {encoding!r} is required but unavailable")
    if mode != "auto" and mode != "tiktoken":
        raise ValueError(f"unknown token counting mode: {mode!r}")
    if enc is None:
        return max(minimum, estimate_tokens_fallback(text))
    return max(minimum, len(enc.encode(text)))


def count_message_content_tokens(
    messages: list[dict],
    *,
    minimum: int = 0,
    mode: TokenCountingMode = "auto",
) -> int:
    """Count OpenAI-style message content tokens, excluding structural framing."""
    total = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total += count_text_tokens(content, mode=mode)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += count_text_tokens(part.get("text", ""), mode=mode)
    return max(minimum, total)


__all__ = [
    "TokenCountingMode",
    "count_message_content_tokens",
    "count_text_tokens",
    "estimate_tokens_fallback",
    "looks_code_like",
    "token_counts_are_estimated",
]
