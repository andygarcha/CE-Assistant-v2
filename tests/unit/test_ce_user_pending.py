from tests.conftest import make_roll, make_user

# ── has_pending ───────────────────────────────────────────────────────────────


class TestHasPending:
    def test_true_for_pending_roll(self):
        pending = make_roll(roll_name="Never Lucky", status="pending")
        user = make_user(rolls=[pending])
        assert user.has_pending("Never Lucky")

    def test_false_on_fresh_user(self):
        user = make_user()
        assert not user.has_pending("Never Lucky")

    def test_false_for_current_roll_with_same_name(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        assert not user.has_pending("Never Lucky")

    def test_false_for_different_event(self):
        pending = make_roll(roll_name="Never Lucky", status="pending")
        user = make_user(rolls=[pending])
        assert not user.has_pending("Let Fate Decide")


# ── pending_rolls ─────────────────────────────────────────────────────────────


class TestPendingRolls:
    def test_empty_on_fresh_user(self):
        user = make_user()
        assert user.pending_rolls == []

    def test_contains_pending_roll(self):
        pending = make_roll(roll_name="Never Lucky", status="pending")
        user = make_user(rolls=[pending])
        assert len(user.pending_rolls) == 1

    def test_excludes_current_rolls(self):
        current = make_roll(roll_name="Never Lucky", status="current")
        user = make_user(rolls=[current])
        assert user.pending_rolls == []

    def test_returns_all_pending_rolls(self):
        p1 = make_roll(roll_name="Never Lucky", status="pending")
        p2 = make_roll(roll_name="Let Fate Decide", status="pending")
        user = make_user(rolls=[p1, p2])
        assert len(user.pending_rolls) == 2
