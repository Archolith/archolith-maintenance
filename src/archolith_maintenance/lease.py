"""Cross-process SQLite lease for single-leader election.

Generic single-leader lease extracted from cth.mcp.memory's
``services/scheduler_lease.py`` (the proven reference). Behavior-identical SQLite
schema and semantics so a future convergence of cth.memory (-> archolith.memory)
onto this shared package is a drop-in. The only change from the reference is that
``db_path`` is required (no memory-telemetry default) so this package carries no
domain coupling.

A lease is identified by ``lease_name``; an owner is ``(owner_id, owner_pid)``.
``try_acquire`` succeeds when the lease is free, expired, or already owned by the
caller. ``renew`` extends an owned lease; ``release`` drops it; ``force_acquire``
takes it regardless of prior owner (operator override) and returns the displaced
owner. All timing is epoch seconds; ``lease_duration_s`` is clamped to >= 1.0.
"""

from __future__ import annotations

import socket
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SchedulerLeaseStoreProtocol(Protocol):
    """Structural contract for a single-leader lease store."""

    def try_acquire(self, *, lease_name: str, owner_id: str, owner_pid: int, lease_duration_s: float) -> bool:
        ...

    def renew(self, *, lease_name: str, owner_id: str, owner_pid: int, lease_duration_s: float) -> bool:
        ...

    def release(self, *, lease_name: str, owner_id: str) -> None:
        ...

    def fetch(self, *, lease_name: str) -> dict[str, object] | None:
        ...

    def force_acquire(
        self,
        *,
        lease_name: str,
        owner_id: str,
        owner_pid: int,
        lease_duration_s: float,
    ) -> dict[str, object] | None:
        ...


@dataclass
class SchedulerLeaseStore:
    """Cross-process SQLite lease ensuring only one leader runs per ``lease_name``."""

    db_path: Path
    _initialized: bool = field(default=False, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)

    def _ensure_ready(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scheduler_leases (
                        lease_name TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        owner_pid INTEGER NOT NULL,
                        hostname TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        heartbeat_at TEXT NOT NULL,
                        lease_expires_at REAL NOT NULL
                    )
                    """
                )
                conn.commit()
            self._initialized = True

    @staticmethod
    def _now_epoch() -> float:
        return time.time()

    @staticmethod
    def _hostname() -> str:
        return socket.gethostname()

    def try_acquire(self, *, lease_name: str, owner_id: str, owner_pid: int, lease_duration_s: float) -> bool:
        self._ensure_ready()
        now = self._now_epoch()
        expires_at = now + max(1.0, lease_duration_s)
        heartbeat_at = _utc_now_iso()
        hostname = self._hostname()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT owner_id, lease_expires_at
                FROM scheduler_leases
                WHERE lease_name = ?
                """,
                (lease_name,),
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO scheduler_leases (
                        lease_name, owner_id, owner_pid, hostname, started_at, heartbeat_at, lease_expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (lease_name, owner_id, owner_pid, hostname, heartbeat_at, heartbeat_at, expires_at),
                )
                conn.commit()
                return True
            existing_owner_id = str(row[0])
            existing_expires_at = float(row[1])
            if existing_owner_id == owner_id or existing_expires_at <= now:
                conn.execute(
                    """
                    UPDATE scheduler_leases
                    SET owner_id = ?,
                        owner_pid = ?,
                        hostname = ?,
                        started_at = ?,
                        heartbeat_at = ?,
                        lease_expires_at = ?
                    WHERE lease_name = ?
                    """,
                    (owner_id, owner_pid, hostname, heartbeat_at, heartbeat_at, expires_at, lease_name),
                )
                conn.commit()
                return True
            conn.rollback()
        return False

    def renew(self, *, lease_name: str, owner_id: str, owner_pid: int, lease_duration_s: float) -> bool:
        self._ensure_ready()
        now = self._now_epoch()
        heartbeat_at = _utc_now_iso()
        expires_at = now + max(1.0, lease_duration_s)
        with sqlite3.connect(self.db_path) as conn:
            updated = conn.execute(
                """
                UPDATE scheduler_leases
                SET owner_pid = ?,
                    heartbeat_at = ?,
                    lease_expires_at = ?
                WHERE lease_name = ?
                  AND owner_id = ?
                """,
                (owner_pid, heartbeat_at, expires_at, lease_name, owner_id),
            ).rowcount
            conn.commit()
            return updated > 0

    def release(self, *, lease_name: str, owner_id: str) -> None:
        self._ensure_ready()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM scheduler_leases
                WHERE lease_name = ?
                  AND owner_id = ?
                """,
                (lease_name, owner_id),
            )
            conn.commit()

    def fetch(self, *, lease_name: str) -> dict[str, object] | None:
        self._ensure_ready()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT lease_name, owner_id, owner_pid, hostname, started_at, heartbeat_at, lease_expires_at
                FROM scheduler_leases
                WHERE lease_name = ?
                """,
                (lease_name,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["expired"] = float(result["lease_expires_at"]) <= self._now_epoch()
            return result

    def force_acquire(
        self,
        *,
        lease_name: str,
        owner_id: str,
        owner_pid: int,
        lease_duration_s: float,
    ) -> dict[str, object] | None:
        """Acquire the lease regardless of prior owner/expiry; return displaced owner."""
        self._ensure_ready()
        now = self._now_epoch()
        expires_at = now + max(1.0, lease_duration_s)
        heartbeat_at = _utc_now_iso()
        hostname = self._hostname()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN IMMEDIATE")
            previous_row = conn.execute(
                """
                SELECT lease_name, owner_id, owner_pid, hostname, started_at, heartbeat_at, lease_expires_at
                FROM scheduler_leases
                WHERE lease_name = ?
                """,
                (lease_name,),
            ).fetchone()
            previous = dict(previous_row) if previous_row is not None else None
            if previous is not None:
                previous["expired"] = float(previous["lease_expires_at"]) <= now

            conn.execute(
                """
                INSERT INTO scheduler_leases (
                    lease_name, owner_id, owner_pid, hostname, started_at, heartbeat_at, lease_expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lease_name) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    owner_pid = excluded.owner_pid,
                    hostname = excluded.hostname,
                    started_at = excluded.started_at,
                    heartbeat_at = excluded.heartbeat_at,
                    lease_expires_at = excluded.lease_expires_at
                """,
                (lease_name, owner_id, owner_pid, hostname, heartbeat_at, heartbeat_at, expires_at),
            )
            conn.commit()
            return previous


__all__ = ["SchedulerLeaseStore", "SchedulerLeaseStoreProtocol"]
