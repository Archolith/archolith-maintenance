# archolith-maintenance — Data Models

## Entities

### `scheduler_leases` Table (SQLite)

SQLite table holding active leases. One row per `lease_name`.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `lease_name` | TEXT | PRIMARY KEY | Unique lease identifier (e.g., `"curator-worker"`) |
| `owner_id` | TEXT | NOT NULL | Consumer-provided owner identifier (e.g., process/worker name) |
| `owner_pid` | INTEGER | NOT NULL | Process ID of the owner |
| `hostname` | TEXT | NOT NULL | Hostname where the owner runs (from `socket.gethostname()`) |
| `started_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp when lease was first acquired |
| `heartbeat_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp of last renewal (or acquisition) |
| `lease_expires_at` | REAL | NOT NULL | Epoch seconds (float) when lease expires; <= now means expired |

A lease is considered **expired** when `lease_expires_at <= time.time()` (epoch seconds).

## DTOs

### Lease Record (returned by `fetch()` and `force_acquire()`)

Returned as a dict with the above columns plus a computed `expired` boolean:

```python
{
    "lease_name": str,
    "owner_id": str,
    "owner_pid": int,
    "hostname": str,
    "started_at": str,        # ISO 8601 UTC
    "heartbeat_at": str,      # ISO 8601 UTC
    "lease_expires_at": float, # epoch seconds
    "expired": bool            # computed: lease_expires_at <= now
}
```

Returns `None` if the lease does not exist.

## Enums

None.

## Repository Reference

All data is stored in a single SQLite database file at the path provided to `SchedulerLeaseStore(db_path=...)`. The table is created lazily on first access via `_ensure_ready()`. All reads and writes use standard `sqlite3` transactions with `BEGIN IMMEDIATE` for serialization under concurrent access.
