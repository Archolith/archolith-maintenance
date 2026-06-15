"""Behavior-parity tests for the single-leader SchedulerLeaseStore."""

from __future__ import annotations

import time
from pathlib import Path

from archolith_maintenance.lease import SchedulerLeaseStore


def _store(tmp_path: Path) -> SchedulerLeaseStore:
    return SchedulerLeaseStore(db_path=tmp_path / "leases.db")


def test_acquire_free_lease(tmp_path):
    s = _store(tmp_path)
    assert s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60) is True


def test_second_owner_blocked_while_held(tmp_path):
    s = _store(tmp_path)
    assert s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60) is True
    assert s.try_acquire(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60) is False


def test_same_owner_reacquire_is_renew(tmp_path):
    s = _store(tmp_path)
    assert s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60) is True
    # Same owner can always (re)acquire — it is effectively a renew.
    assert s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60) is True


def test_expired_lease_can_be_taken_by_other(tmp_path):
    s = _store(tmp_path)
    # 1-second floor; acquire with a tiny duration, then wait it out.
    assert s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=0.0) is True
    time.sleep(1.2)
    assert s.try_acquire(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60) is True
    info = s.fetch(lease_name="L")
    assert info is not None and info["owner_id"] == "b"


def test_renew_only_by_owner(tmp_path):
    s = _store(tmp_path)
    s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60)
    assert s.renew(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60) is True
    assert s.renew(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60) is False


def test_release_frees_lease(tmp_path):
    s = _store(tmp_path)
    s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60)
    s.release(lease_name="L", owner_id="a")
    assert s.fetch(lease_name="L") is None
    assert s.try_acquire(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60) is True


def test_release_by_non_owner_is_noop(tmp_path):
    s = _store(tmp_path)
    s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60)
    s.release(lease_name="L", owner_id="b")  # not the owner
    info = s.fetch(lease_name="L")
    assert info is not None and info["owner_id"] == "a"


def test_force_acquire_takes_and_returns_previous(tmp_path):
    s = _store(tmp_path)
    s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=60)
    previous = s.force_acquire(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60)
    assert previous is not None and previous["owner_id"] == "a"
    info = s.fetch(lease_name="L")
    assert info is not None and info["owner_id"] == "b"


def test_force_acquire_on_free_lease_returns_none(tmp_path):
    s = _store(tmp_path)
    previous = s.force_acquire(lease_name="L", owner_id="b", owner_pid=2, lease_duration_s=60)
    assert previous is None
    assert s.fetch(lease_name="L")["owner_id"] == "b"


def test_fetch_reports_expired_flag(tmp_path):
    s = _store(tmp_path)
    s.try_acquire(lease_name="L", owner_id="a", owner_pid=1, lease_duration_s=0.0)
    time.sleep(1.2)
    info = s.fetch(lease_name="L")
    assert info is not None and info["expired"] is True


def test_distinct_lease_names_are_independent(tmp_path):
    s = _store(tmp_path)
    assert s.try_acquire(lease_name="L1", owner_id="a", owner_pid=1, lease_duration_s=60) is True
    assert s.try_acquire(lease_name="L2", owner_id="b", owner_pid=2, lease_duration_s=60) is True
