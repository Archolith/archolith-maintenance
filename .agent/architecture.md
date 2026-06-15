# archolith-maintenance — Architecture

## Overview

`SchedulerLeaseStore` implements cross-process single-leader election backed by SQLite. Only one process per `lease_name` holds an active lease at a time; other processes wait, retry, or defer work. A lease is identified by `lease_name`; an owner is `(owner_id, owner_pid)`. Used by the curator worker to guarantee idempotent, non-concurrent maintenance scheduling.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Persistence | SQLite 3 (stdlib `sqlite3`) |
| Concurrency | `threading.Lock` (lazy init guard) |
| Timing | epoch seconds (float) for expiry; ISO 8601 UTC for timestamps |

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

## Configuration / Environment Variables

None. The only required input is `db_path` (file path to SQLite database).

## External Dependencies

- **Python 3.11+** (f-strings, match statements, modern type hints).
- **stdlib only:** `sqlite3`, `socket`, `threading`, `time`, `dataclasses`, `pathlib`, `datetime`.
- No external package dependencies.
