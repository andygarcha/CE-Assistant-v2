from tests.conftest import make_roll
from Modules.HealthCheck import check_roll_game_counts


class TestCheckRollGameCounts:
    def test_flags_wrong_fixed_count(self):
        roll = make_roll(roll_name="One Hell of a Day", games=["a", "b"])
        warnings = check_roll_game_counts([roll])
        assert len(warnings) == 1
        assert ":hospital:" in warnings[0]
        assert roll.id in warnings[0]

    def test_does_not_flag_correct_fixed_count(self):
        roll = make_roll(roll_name="One Hell of a Day", games=["a"])
        assert check_roll_game_counts([roll]) == []

    def test_flags_out_of_range_count(self):
        roll = make_roll(roll_name="Fourward Thinking", games=[])
        warnings = check_roll_game_counts([roll])
        assert len(warnings) == 1

    def test_does_not_flag_in_range_count(self):
        roll = make_roll(roll_name="Fourward Thinking", games=["a", "b"])
        assert check_roll_game_counts([roll]) == []

    def test_flags_won_roll_with_wrong_won_count(self):
        roll = make_roll(roll_name="Two Week T2 Streak", status="won", games=["a"])
        warnings = check_roll_game_counts([roll])
        assert len(warnings) == 1

    def test_does_not_flag_won_roll_with_correct_won_count(self):
        roll = make_roll(
            roll_name="Two Week T2 Streak", status="won", games=["a", "b"]
        )
        assert check_roll_game_counts([roll]) == []

    def test_ignores_won_legacy_rolls(self):
        roll = make_roll(
            roll_name="One Hell of a Day", status="won_legacy", games=["a", "b"]
        )
        assert check_roll_game_counts([roll]) == []

    def test_ignores_unknown_roll_names(self):
        roll = make_roll(roll_name="Not A Real Roll", games=[])
        assert check_roll_game_counts([roll]) == []
