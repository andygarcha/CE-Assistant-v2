import datetime

from tests.conftest import make_roll, make_user

# ── add_pending ───────────────────────────────────────────────────────────────


class TestAddPending:
    def test_user_has_pending_after_add(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert user.has_pending("Never Lucky")

    def test_pending_roll_has_correct_event_name(self):
        user = make_user()
        user.add_pending("Never Lucky")
        roll = user.get_pending("Never Lucky")
        assert roll is not None
        assert roll.roll_name == "Never Lucky"

    def test_pending_roll_has_pending_status(self):
        user = make_user()
        user.add_pending("Never Lucky")
        roll = user.get_pending("Never Lucky")
        assert roll is not None
        assert roll.status == "pending"

    def test_pending_roll_due_time_is_in_future(self):
        user = make_user()
        user.add_pending("Never Lucky")
        roll = user.get_pending("Never Lucky")
        assert roll is not None
        assert roll.due_time is not None
        assert roll.due_time > datetime.datetime.now(datetime.UTC)

    def test_does_not_affect_other_event_names(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert not user.has_pending("Let Fate Decide")

    def test_can_add_pending_for_multiple_events(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.add_pending("Let Fate Decide")
        assert user.has_pending("Never Lucky")
        assert user.has_pending("Let Fate Decide")

    def test_does_not_disturb_existing_rolls(self):
        existing = make_roll(roll_name="One Hell of a Day", status="current")
        user = make_user(rolls=[existing])
        user.add_pending("Never Lucky")
        assert len(user.rolls) == 2


# ── remove_pending ────────────────────────────────────────────────────────────


class TestRemovePending:
    def test_pending_gone_after_remove(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.remove_pending("Never Lucky")
        assert not user.has_pending("Never Lucky")

    def test_no_op_when_no_pending_exists(self):
        user = make_user()
        user.remove_pending("Never Lucky")  # must not raise
        assert not user.has_pending("Never Lucky")

    def test_does_not_remove_pending_for_different_event(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.add_pending("Let Fate Decide")
        user.remove_pending("Never Lucky")
        assert not user.has_pending("Never Lucky")
        assert user.has_pending("Let Fate Decide")

    def test_does_not_remove_non_pending_roll_with_same_name(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        user.remove_pending("Never Lucky")
        assert len(user.rolls) == 1

    def test_removes_only_first_when_duplicates_exist(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.add_pending("Never Lucky")
        user.remove_pending("Never Lucky")
        assert user.has_pending("Never Lucky")


# ── get_pending ───────────────────────────────────────────────────────────────


class TestGetPending:
    def test_returns_correct_roll(self):
        user = make_user()
        user.add_pending("Never Lucky")
        roll = user.get_pending("Never Lucky")
        assert roll is not None
        assert roll.roll_name == "Never Lucky"
        assert roll.status == "pending"

    def test_returns_none_when_no_pending(self):
        user = make_user()
        assert user.get_pending("Never Lucky") is None

    def test_returns_none_for_wrong_event(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert user.get_pending("Let Fate Decide") is None

    def test_returns_none_for_current_roll_with_same_name(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        assert user.get_pending("Never Lucky") is None

    def test_returns_none_after_remove(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.remove_pending("Never Lucky")
        assert user.get_pending("Never Lucky") is None

    def test_rolls_for_different_events_have_distinct_ids(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.add_pending("Let Fate Decide")
        r1 = user.get_pending("Never Lucky")
        r2 = user.get_pending("Let Fate Decide")
        assert r1 is not None
        assert r2 is not None
        assert r1._id != r2._id


# ── has_pending ───────────────────────────────────────────────────────────────


class TestHasPending:
    def test_true_after_add(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert user.has_pending("Never Lucky")

    def test_false_on_fresh_user(self):
        user = make_user()
        assert not user.has_pending("Never Lucky")

    def test_false_after_remove(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.remove_pending("Never Lucky")
        assert not user.has_pending("Never Lucky")

    def test_false_for_current_roll_with_same_name(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        assert not user.has_pending("Never Lucky")

    def test_false_for_different_event(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert not user.has_pending("Let Fate Decide")


# ── pending_rolls ─────────────────────────────────────────────────────────────


class TestPendingRolls:
    def test_empty_on_fresh_user(self):
        user = make_user()
        assert user.pending_rolls == []

    def test_contains_added_pending(self):
        user = make_user()
        user.add_pending("Never Lucky")
        assert len(user.pending_rolls) == 1

    def test_excludes_current_rolls(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        assert user.pending_rolls == []

    def test_returns_all_pending_rolls(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.add_pending("Let Fate Decide")
        assert len(user.pending_rolls) == 2

    def test_excludes_removed_pending(self):
        user = make_user()
        user.add_pending("Never Lucky")
        user.remove_pending("Never Lucky")
        assert user.pending_rolls == []
