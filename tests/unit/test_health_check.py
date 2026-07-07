from tests.conftest import make_roll, make_game, make_objective
from Modules.HealthCheck import (
    check_roll_game_counts,
    check_uncategorized_games,
    check_orphaned_objectives,
)
from Modules import hm


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


class TestCheckUncategorizedGames:
    def test_flags_game_with_no_categories(self):
        game = make_game(categories=[])
        warnings = check_uncategorized_games([game])
        assert len(warnings) == 1
        assert ":hospital:" in warnings[0]

    def test_does_not_flag_game_with_categories(self):
        game = make_game(categories=["Action"])
        assert check_uncategorized_games([game]) == []

    def test_does_not_flag_challenge_enthusiasts_game(self):
        game = make_game(ce_id=hm.GAME_ID_CHALLENGE_ENTHUSIASTS, categories=[])
        assert check_uncategorized_games([game]) == []

    def test_does_not_flag_clown_town_game(self):
        game = make_game(ce_id=hm.GAME_ID_CLOWN_TOWN, categories=[])
        assert check_uncategorized_games([game]) == []


class TestCheckOrphanedObjectives:
    def test_flags_objective_with_no_requirements_or_achievements(self):
        obj = make_objective()  # requirements=None, achievement_ce_ids=None by default
        game = make_game(objectives=[obj])
        warnings = check_orphaned_objectives([game])
        assert len(warnings) == 1
        assert ":hospital:" in warnings[0]
        assert obj.name in warnings[0]

    def test_does_not_flag_objective_with_requirements(self):
        obj = make_objective(requirements="Beat the final boss.")
        game = make_game(objectives=[obj])
        assert check_orphaned_objectives([game]) == []

    def test_does_not_flag_objective_with_achievement_ids(self):
        obj = make_objective(achievement_ce_ids=["ach-0001"])
        game = make_game(objectives=[obj])
        assert check_orphaned_objectives([game]) == []
