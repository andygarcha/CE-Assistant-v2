from unittest.mock import patch

from tests.conftest import make_roll, make_game, make_objective
from Modules.HealthCheck import (
    check_roll_game_counts,
    check_uncategorized_games,
    check_orphaned_objectives,
    format_integrity_report,
    run_cheap_checks,
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
        roll = make_roll(roll_name="Two Week T2 Streak", status="won", games=["a", "b"])
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


class TestFormatIntegrityReport:
    def test_no_issues(self):
        summary = format_integrity_report({"synced": [], "removed": [], "schema": []})
        assert (
            summary
            == ":hospital: Integrity check passed — local cache in sync with Supabase"
        )

    def test_synced_only(self):
        summary = format_integrity_report(
            {"synced": ["games: 2"], "removed": [], "schema": []}
        )
        assert summary == ":hospital: Integrity check: synced [games: 2]"

    def test_all_three_sections(self):
        summary = format_integrity_report(
            {
                "synced": ["games: 2"],
                "removed": ["users: 1"],
                "schema": ["added column x"],
            }
        )
        assert summary == (
            ":hospital: Integrity check: synced [games: 2], "
            "removed [users: 1], schema [added column x]"
        )


class TestRunCheapChecks:
    def test_combines_warnings_from_all_checks(self):
        bad_game = make_game(ce_id="game-a", categories=[])
        bad_roll = make_roll(roll_name="One Hell of a Day", games=["x", "y"])

        with (
            patch(
                "Modules.HealthCheck.SupabaseReader.get_database_name",
                return_value=[bad_game],
            ),
            patch(
                "Modules.HealthCheck.SupabaseReader.get_all_rolls",
                return_value=[bad_roll],
            ),
        ):
            warnings = run_cheap_checks()

        assert len(warnings) == 2
        assert all(":hospital:" in w for w in warnings)

    def test_no_warnings_when_everything_is_clean(self):
        good_game = make_game(categories=["Action"])
        good_roll = make_roll(roll_name="One Hell of a Day", games=["x"])

        with (
            patch(
                "Modules.HealthCheck.SupabaseReader.get_database_name",
                return_value=[good_game],
            ),
            patch(
                "Modules.HealthCheck.SupabaseReader.get_all_rolls",
                return_value=[good_roll],
            ),
        ):
            assert run_cheap_checks() == []

    def test_one_failing_check_does_not_block_the_others(self):
        good_roll = make_roll(roll_name="One Hell of a Day", games=["x"])

        with (
            patch(
                "Modules.HealthCheck.SupabaseReader.get_database_name",
                side_effect=RuntimeError("supabase down"),
            ),
            patch(
                "Modules.HealthCheck.SupabaseReader.get_all_rolls",
                return_value=[good_roll],
            ),
        ):
            warnings = run_cheap_checks()

        # both game-based checks fail (2 failure messages), roll check succeeds clean
        assert len(warnings) == 2
        assert all("check failed" in w for w in warnings)
