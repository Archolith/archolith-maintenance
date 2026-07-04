"""archolith-maintenance — shared background-maintenance substrate.

Generic, domain-agnostic machinery extracted from cth.mcp.memory's proven
scheduler: single-leader leasing (and, in later slices, a leased periodic loop
skeleton + backoff/queue-health helpers). Consumed by archolith-context's curator
worker; cth.memory will converge onto it at the archolith.memory rename.
"""

from __future__ import annotations

from archolith_maintenance.lease import SchedulerLeaseStore, SchedulerLeaseStoreProtocol
from archolith_maintenance.token_accounting import (
    TokenCountingMode,
    count_message_content_tokens,
    count_text_tokens,
    estimate_tokens_fallback,
    looks_code_like,
    token_counts_are_estimated,
)

__all__ = [
    "SchedulerLeaseStore",
    "SchedulerLeaseStoreProtocol",
    "TokenCountingMode",
    "count_message_content_tokens",
    "count_text_tokens",
    "estimate_tokens_fallback",
    "looks_code_like",
    "token_counts_are_estimated",
]
