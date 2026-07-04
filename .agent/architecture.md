# archolith-maintenance — Architecture

## Overview

`archolith-maintenance` owns shared, domain-agnostic helper surfaces used across Archolith projects.

`SchedulerLeaseStore` implements cross-process single-leader election backed by SQLite. Only one process per `lease_name` holds an active lease at a time; other processes wait, retry, or defer work. A lease is identified by `lease_name`; an owner is `(owner_id, owner_pid)`. Used by the curator worker to guarantee idempotent, non-concurrent maintenance scheduling.

`token_accounting` owns canonical tokenizer selection and fallback token-count policy. Consumers may layer surface-specific semantics around it: `archolith-context` adds structural request framing and gate floors, `archolith-filter` uses it for shrink/truncate budgets, `archolith-bench` uses it for benchmark text/message metrics, and `archolith-mcp-audit` uses it inside its richer audit `TokenCount` reporting shape.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Persistence | SQLite 3 (stdlib `sqlite3`) |
| Concurrency | `threading.Lock` (lazy init guard) |
| Timing | epoch seconds (float) for expiry; ISO 8601 UTC for timestamps |
| Token counting | Optional `tiktoken` lazy import with shape-aware stdlib fallback |

## Data Flow

1. Consumer creates `SchedulerLeaseStore(db_path=<path>)`.
2. On first use, `_ensure_ready()` lazily creates `scheduler_leases` table and acquires thread lock.
3. Consumer calls `try_acquire(lease_name=..., owner_id=..., owner_pid=..., lease_duration_s=...)`.
4. If lease is free, expired, or already owned by caller, acquisition succeeds (INSERT or UPDATE).
5. Holder periodically calls `renew()` to extend expiry. On shutdown, calls `release()` to drop the lease.
6. If holder crashes, next caller's `try_acquire()` succeeds once expiry time is reached.
7. Operator can call `force_acquire()` to override any holder (returns the displaced owner).

## Key Components

### `SchedulerLeaseStore`
- **Purpose:** Manages SQLite-backed leases for single-leader election.
- **Lazy init:** Thread-safe `_ensure_ready()` creates the table on first access.
- **Public API:**
  - `try_acquire(lease_name, owner_id, owner_pid, lease_duration_s) -> bool` — acquires if free/expired/already-owned; succeeds once per acquisition window.
  - `renew(lease_name, owner_id, owner_pid, lease_duration_s) -> bool` — extends expiry only if caller is current owner; false if ownership lost.
  - `release(lease_name, owner_id) -> None` — deletes lease row; idempotent.
  - `fetch(lease_name) -> dict | None` — returns lease record with computed `expired` boolean; None if not found.
  - `force_acquire(lease_name, owner_id, owner_pid, lease_duration_s) -> dict | None` — overrides any holder; returns the prior owner (with `expired` flag) or None.
- **Semantics:**
  - `lease_duration_s` is clamped to >= 1.0 to prevent zero/negative durations.
  - Expiry is checked as `lease_expires_at <= now` (epoch seconds).
  - All SQL operations use `BEGIN IMMEDIATE` for serialization under concurrent writes.
  - Hostname and timestamps are recorded for diagnostics.

### `SchedulerLeaseStoreProtocol`
Structural contract (Protocol) for any object implementing the lease store interface. Enables polymorphism and mocking in consumers.

### `token_accounting`
- **Purpose:** Shared text-token primitive for Archolith projects.
- **Public API:**
  - `count_text_tokens(text, encoding="cl100k_base", minimum=0, mode="auto") -> int` — counts via `tiktoken` when available, otherwise falls back to canonical heuristics.
  - `count_message_content_tokens(messages, minimum=0, mode="auto") -> int` — counts OpenAI-style message content without structural framing.
  - `token_counts_are_estimated(encoding="cl100k_base", mode="auto") -> bool` — reports whether a count is heuristic-backed.
  - `estimate_tokens_fallback(text) -> int` — direct fallback estimator for tests and diagnostics.
  - `looks_code_like(text) -> bool` — fallback signal for code/config-heavy text.
- **Mode options:** `mode="auto"` preserves default behavior; `mode="fallback"` forces heuristic counts; `mode="tiktoken"` requires tiktoken and raises if unavailable.
- **Fallback policy:** Prose keeps the historical ~4 chars/token heuristic. Code/config-heavy text uses a more conservative ~3.2 chars/token estimate. Consumers should not duplicate this policy locally.

## Configuration / Environment Variables

None. The only required lease input is `db_path` (file path to SQLite database). Token accounting has no configuration; callers choose encoding and surface-specific floors/margins.

## External Dependencies

- **Python 3.11+** (f-strings, match statements, modern type hints).
- **Core runtime:** stdlib modules including `sqlite3`, `socket`, `threading`, `time`, `dataclasses`, `pathlib`, `datetime`, `functools`, and `re`.
- **Optional tokenizer:** `tiktoken` is lazy-imported when available. The package remains installable without it.
