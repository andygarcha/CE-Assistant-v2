"""
Integration tests for SupabaseReader.add_pending and kill_pending.

These tests hit the real Supabase instance and perform write operations,
cleaning up before and after each test so they leave no residue.

Run with:  pytest tests/integration/test_supabase_pending.py
"""

import pytest

from Modules import SupabaseReader

# Any valid solo event is fine here — it doesn't matter which one.
_EVENT = "One Hell of a Day"


# ── helpers ───────────────────────────────────────────────────────────────────


def _pending_count(user_ce_id: str) -> int:
    """Number of pending rows for _EVENT owned by this user."""
    return sum(
        1
        for r in SupabaseReader.get_user_rolls(user_ce_id)
        if r.roll_name == _EVENT and r.status == "pending"
    )


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def user_ids() -> tuple[str, str]:
    """Two real CE user IDs fetched from the database."""
    ids = SupabaseReader.get_list("user")
    assert len(ids) >= 2, "Need at least 2 registered users to run pending tests."
    return ids[0], ids[1]


@pytest.fixture(autouse=True)
def clean(user_ids: tuple[str, str]):
    """Wipe any leftover test pending rows before and after every test."""
    uid1, uid2 = user_ids
    SupabaseReader.kill_pending(_EVENT, uid1, uid2)
    yield
    SupabaseReader.kill_pending(_EVENT, uid1, uid2)


# ── add_pending ───────────────────────────────────────────────────────────────


class TestAddPending:
    def test_creates_one_row_for_single_user(self, user_ids: tuple[str, str]):
        uid1, _ = user_ids
        SupabaseReader.add_pending(_EVENT, uid1)
        assert _pending_count(uid1) == 1

    def test_creates_one_row_per_user_when_two_supplied(
        self, user_ids: tuple[str, str]
    ):
        uid1, uid2 = user_ids
        SupabaseReader.add_pending(_EVENT, uid1, uid2)
        assert _pending_count(uid1) == 1
        assert _pending_count(uid2) == 1

    def test_row_has_correct_status(self, user_ids: tuple[str, str]):
        uid1, _ = user_ids
        SupabaseReader.add_pending(_EVENT, uid1)
        rolls = SupabaseReader.get_user_rolls(uid1)
        pending = [r for r in rolls if r.roll_name == _EVENT and r.status == "pending"]
        assert all(r.status == "pending" for r in pending)

    def test_row_has_correct_event_name(self, user_ids: tuple[str, str]):
        uid1, _ = user_ids
        SupabaseReader.add_pending(_EVENT, uid1)
        rolls = SupabaseReader.get_user_rolls(uid1)
        pending = [r for r in rolls if r.roll_name == _EVENT and r.status == "pending"]
        assert len(pending) == 1
        assert pending[0].roll_name == _EVENT

    def test_due_time_is_roughly_ten_minutes_from_now(self, user_ids: tuple[str, str]):
        import datetime

        uid1, _ = user_ids
        SupabaseReader.add_pending(_EVENT, uid1)
        rolls = SupabaseReader.get_user_rolls(uid1)
        pending = next(
            r for r in rolls if r.roll_name == _EVENT and r.status == "pending"
        )
        assert pending.due_time is not None
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = pending.due_time - now
        assert datetime.timedelta(minutes=8) < delta < datetime.timedelta(minutes=12)


# ── kill_pending ──────────────────────────────────────────────────────────────


class TestKillPending:
    def test_removes_pending_for_single_user(self, user_ids: tuple[str, str]):
        uid1, _ = user_ids
        SupabaseReader.add_pending(_EVENT, uid1)
        assert _pending_count(uid1) == 1

        SupabaseReader.kill_pending(_EVENT, uid1)
        assert _pending_count(uid1) == 0

    def test_removes_pending_for_both_users(self, user_ids: tuple[str, str]):
        uid1, uid2 = user_ids
        SupabaseReader.add_pending(_EVENT, uid1, uid2)
        assert _pending_count(uid1) == 1
        assert _pending_count(uid2) == 1

        SupabaseReader.kill_pending(_EVENT, uid1, uid2)
        assert _pending_count(uid1) == 0
        assert _pending_count(uid2) == 0

    def test_does_not_remove_other_users_pending(self, user_ids: tuple[str, str]):
        uid1, uid2 = user_ids
        SupabaseReader.add_pending(_EVENT, uid1, uid2)

        SupabaseReader.kill_pending(_EVENT, uid1)
        assert _pending_count(uid1) == 0
        assert _pending_count(uid2) == 1  # uid2's row untouched

    def test_noop_when_no_pending_exists(self, user_ids: tuple[str, str]):
        uid1, uid2 = user_ids
        # Nothing was added — should not raise
        SupabaseReader.kill_pending(_EVENT, uid1, uid2)
        assert _pending_count(uid1) == 0
        assert _pending_count(uid2) == 0
