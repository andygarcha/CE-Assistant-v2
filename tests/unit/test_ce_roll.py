import datetime

import pytest

from Classes.CE_Roll import relative
from tests.conftest import make_game, make_roll

PAST = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
FUTURE = datetime.datetime(2099, 1, 1, tzinfo=datetime.UTC)
INIT = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


# ── module-level relative() ───────────────────────────────────────────────────


class TestRelative:
    @pytest.mark.parametrize(
        "tier, expected",
        [
            (1, 1),
            (2, 2),
            (3, 4),
            (4, 8),
            (5, 20),
            (6, 20),
            (99, 20),
        ],
    )
    def test_known_tiers(self, tier, expected):
        assert relative(tier) == expected


# ── is_co_op ──────────────────────────────────────────────────────────────────


class TestIsCoop:
    def test_solo_roll_without_partner_is_not_coop(self):
        assert (
            make_roll(roll_name="One Hell of a Day", partner_ce_id=None).is_co_op
            is False
        )

    def test_roll_with_partner_id_is_coop(self):
        assert make_roll(partner_ce_id="partner-ce-id").is_co_op is True

    @pytest.mark.parametrize(
        "name",
        [
            "Destiny Alignment",
            "Soul Mates",
            "Teamwork Makes the Dream Work",
        ],
    )
    def test_coop_roll_names_are_coop(self, name):
        assert make_roll(roll_name=name).is_co_op is True


# ── is_expired ────────────────────────────────────────────────────────────────


class TestIsExpired:
    def test_no_due_time_never_expires(self):
        assert make_roll(due_time=None).is_expired is False

    def test_past_due_time_is_expired(self):
        assert make_roll(due_time=PAST).is_expired is True

    def test_future_due_time_not_expired(self):
        assert make_roll(due_time=FUTURE).is_expired is False

    def test_past_unix_timestamp_is_expired(self):
        roll = make_roll()
        roll._due_time = PAST
        assert roll.is_expired is True

    def test_future_unix_timestamp_not_expired(self):
        roll = make_roll()
        roll._due_time = FUTURE
        assert roll.is_expired is False

    def test_past_iso_string_is_expired(self):
        roll = make_roll()
        roll._due_time = "2000-01-01T00:00:00+00:00"  # type: ignore[assignment]
        assert roll.is_expired is True

    def test_future_iso_string_not_expired(self):
        roll = make_roll()
        roll._due_time = "2099-01-01T00:00:00+00:00"  # type: ignore[assignment]
        assert roll.is_expired is False

    def test_ce_timestamp_string_is_expired(self):
        # ".000Z" suffix: fromisoformat may accept it but the ce-format fallback
        # also handles it — either way the string branch is exercised.
        roll = make_roll()
        roll._due_time = "2000-01-01T00:00:00.000Z"  # type: ignore[assignment]
        assert roll.is_expired is True

    def test_unparseable_string_returns_false(self):
        roll = make_roll()
        roll._due_time = "not-a-timestamp"  # type: ignore[assignment]
        assert roll.is_expired is False

    def test_unsupported_type_returns_false(self):
        roll = make_roll()
        roll._due_time = [1, 2, 3]  # type: ignore[assignment]
        assert roll.is_expired is False

    def test_naive_past_datetime_is_expired(self):
        roll = make_roll()
        roll._due_time = datetime.datetime(2000, 1, 1)  # noqa: DTZ001 -- intentionally naive, testing naive-input handling
        assert roll.is_expired is True

    def test_naive_future_datetime_not_expired(self):
        roll = make_roll()
        roll._due_time = datetime.datetime(2099, 1, 1)  # noqa: DTZ001 -- intentionally naive, testing naive-input handling
        assert roll.is_expired is False


# ── is_completed ──────────────────────────────────────────────────────────────


class TestIsCompleted:
    def test_no_completed_time_is_not_completed(self):
        assert make_roll(completed_time=None).is_completed is False

    def test_with_completed_time_is_completed(self):
        assert make_roll(completed_time=PAST).is_completed is True


# ── ends / ready_for_next ─────────────────────────────────────────────────────


class TestEnds:
    def test_roll_with_due_time_ends(self):
        assert make_roll(due_time=FUTURE).ends is True

    def test_roll_without_due_time_does_not_end(self):
        assert make_roll(due_time=None).ends is False


class TestReadyForNext:
    def test_non_multi_stage_not_ready(self):
        assert make_roll(roll_name="One Hell of a Day").ready_for_next is False

    def test_multi_stage_with_no_due_time_is_ready(self):
        roll = make_roll(roll_name="Two Week T2 Streak", due_time=None)
        assert roll.ready_for_next is True

    def test_multi_stage_with_due_time_not_ready(self):
        roll = make_roll(roll_name="Two Week T2 Streak", due_time=FUTURE)
        assert roll.ready_for_next is False


# ── is_multi_stage ────────────────────────────────────────────────────────────


class TestIsMultiStage:
    @pytest.mark.parametrize(
        "name",
        [
            "Two Week T2 Streak",
            'Two "Two Week T2 Streak" Streak',
            "Fourward Thinking",
        ],
    )
    def test_multi_stage_roll_names(self, name):
        assert make_roll(roll_name=name).is_multi_stage is True

    def test_non_multi_stage(self):
        assert make_roll(roll_name="One Hell of a Day").is_multi_stage is False


# ── is_rerollable ─────────────────────────────────────────────────────────────


class TestIsRerollable:
    def test_fourward_thinking_is_rerollable(self):
        assert make_roll(roll_name="Fourward Thinking").is_rerollable is True

    def test_other_rolls_not_rerollable(self):
        assert make_roll(roll_name="Triple Threat").is_rerollable is False


# ── winner ────────────────────────────────────────────────────────────────────


class TestWinner:
    def test_won_status_is_winner(self):
        assert make_roll(status="won").winner is True

    def test_current_status_not_winner(self):
        assert make_roll(status="current").winner is False

    def test_failed_status_not_winner(self):
        assert make_roll(status="failed").winner is False


# ── in_final_stage ────────────────────────────────────────────────────────────


class TestInFinalStage:
    def test_non_multi_stage_returns_false(self):
        assert make_roll(roll_name="One Hell of a Week").in_final_stage is False

    def test_two_week_t2_streak_final_stage_at_2_games(self):
        roll = make_roll(roll_name="Two Week T2 Streak", games=["g1", "g2"])
        assert roll.in_final_stage is True

    def test_two_week_t2_streak_not_final_at_1_game(self):
        roll = make_roll(roll_name="Two Week T2 Streak", games=["g1"])
        assert roll.in_final_stage is False

    def test_fourward_thinking_final_stage_at_4_games(self):
        roll = make_roll(roll_name="Fourward Thinking", games=["g1", "g2", "g3", "g4"])
        assert roll.in_final_stage is True

    def test_fourward_thinking_not_final_at_2_games(self):
        roll = make_roll(roll_name="Fourward Thinking", games=["g1", "g2"])
        assert roll.in_final_stage is False

    def test_two_two_week_streak_final_stage_at_4_games(self):
        roll = make_roll(
            roll_name='Two "Two Week T2 Streak" Streak',
            games=["g1", "g2", "g3", "g4"],
        )
        assert roll.in_final_stage is True

    def test_two_two_week_streak_not_final_at_2_games(self):
        roll = make_roll(
            roll_name='Two "Two Week T2 Streak" Streak',
            games=["g1", "g2"],
        )
        assert roll.in_final_stage is False


# ── add_game / remove_game_last ───────────────────────────────────────────────


class TestGameMutation:
    def test_add_game_appends(self):
        roll = make_roll(games=["g1"])
        roll.add_game("g2")
        assert roll.games == ["g1", "g2"]

    def test_remove_game_last_pops_and_returns(self):
        roll = make_roll(games=["g1", "g2"])
        removed = roll.remove_game_last()
        assert removed == "g2"
        assert roll.games == ["g1"]


# ── increase_rerolls ──────────────────────────────────────────────────────────


class TestIncreaseRerolls:
    def test_increments_by_given_amount(self):
        roll = make_roll(rerolls=2)
        roll.increase_rerolls(3)
        assert roll.rerolls == 5


# ── increase_due_time ─────────────────────────────────────────────────────────


class TestIncreaseDueTime:
    def test_increases_due_time_by_seconds(self):
        roll = make_roll(due_time=FUTURE)
        roll.increase_due_time(3600)
        assert roll.due_time == FUTURE + datetime.timedelta(seconds=3600)

    def test_none_due_time_stays_none(self):
        roll = make_roll(due_time=None)
        roll.increase_due_time(3600)
        assert roll.due_time is None


# ── _to_timestamp ─────────────────────────────────────────────────────────────


class TestToTimestamp:
    def test_datetime_to_int(self):
        roll = make_roll()
        result = roll._to_timestamp(INIT)
        assert result == int(INIT.timestamp())

    def test_int_passthrough(self):
        roll = make_roll()
        assert roll._to_timestamp(1234567890) == 1234567890

    def test_float_truncated(self):
        roll = make_roll()
        assert roll._to_timestamp(1234567890.9) == 1234567890

    def test_none_returns_none(self):
        assert make_roll()._to_timestamp(None) is None


# ── _normalize_datetime ───────────────────────────────────────────────────────


class TestNormalizeDatetime:
    def test_none_returns_none(self):
        assert make_roll()._normalize_datetime(None) is None

    def test_naive_datetime_becomes_utc(self):
        naive = datetime.datetime(2024, 6, 1, 12, 0, 0)  # noqa: DTZ001 -- intentionally naive, testing naive-input handling
        result = make_roll()._normalize_datetime(naive)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None

    def test_aware_datetime_unchanged(self):
        result = make_roll()._normalize_datetime(FUTURE)
        assert result == FUTURE

    def test_iso_string_parsed(self):
        result = make_roll()._normalize_datetime("2024-06-01T12:00:00")
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo is not None


# ── calculate_cooldown_date ───────────────────────────────────────────────────


class TestCalculateCooldownDate:
    def test_none_cooldown_rolls_return_none(self):
        for name in [
            "Two Week T2 Streak",
            'Two "Two Week T2 Streak" Streak',
            "Fourward Thinking",
        ]:
            # Non-Fourward rolls with None cooldown return None
            if name != "Fourward Thinking":
                roll = make_roll(roll_name=name, init_time=INIT)
                assert roll.calculate_cooldown_date() is None

    def test_one_hell_of_a_day_cooldown_7_days_from_init(self):
        roll = make_roll(roll_name="One Hell of a Day", init_time=INIT)
        result = roll.calculate_cooldown_date()
        expected = INIT + datetime.timedelta(days=7)
        assert result == expected

    def test_fourward_thinking_cooldown_based_on_games_and_rerolls(self):
        # 2 games, 0 rerolls used (rerolls=0 means 1 allowed, 1 used = rerolls_used = 2 - (0+1) = 1)
        roll = make_roll(
            roll_name="Fourward Thinking", games=["g1", "g2"], rerolls=0, init_time=INIT
        )
        result = roll.calculate_cooldown_date()
        assert isinstance(result, datetime.datetime)
        # days = 2*14 + months_to_days(1) = 28 + ~30
        assert result > INIT + datetime.timedelta(days=28)


class TestCooldownTimestamp:
    def test_none_cooldown_rolls_return_none(self):
        for name in [
            "Two Week T2 Streak",
            'Two "Two Week T2 Streak" Streak',
        ]:
            roll = make_roll(roll_name=name, init_time=INIT)
            assert roll.calculate_cooldown_timestamp() is None

    def test_one_hell_of_a_day_cooldown_7_days_from_init(self):
        roll = make_roll(roll_name="One Hell of a Day", init_time=INIT)
        result = roll.calculate_cooldown_timestamp()
        expected = int((INIT + datetime.timedelta(days=7)).timestamp())
        assert result == expected

    def test_fourward_thinking_cooldown_based_on_games_and_rerolls(self):
        # 2 games, 0 rerolls used (rerolls=0 means 1 allowed, 1 used = rerolls_used = 2 - (0+1) = 1)
        roll = make_roll(
            roll_name="Fourward Thinking", games=["g1", "g2"], rerolls=0, init_time=INIT
        )
        result = roll.calculate_cooldown_timestamp()
        assert isinstance(result, int)
        # days = 2*14 + months_to_days(1) = 28 + ~30
        assert result > int((INIT + datetime.timedelta(days=28)).timestamp())


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCERollToDict:
    def test_returns_dict(self):
        assert isinstance(make_roll().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_roll().to_dict()
        for key in ("name", "due_time", "init_time", "games", "user_ce_id", "status"):
            assert key in result


# ── rolled_categories ─────────────────────────────────────────────────────────

GAME_A: str = "game-aaa-0000-0000-000000000000"
GAME_B: str = "game-bbb-0000-0000-000000000000"
GAME_C: str = "game-ccc-0000-0000-000000000000"


class TestRolledCategories:
    def test_returns_list(self):
        game = make_game(ce_id=GAME_A, categories=["Action"])
        roll = make_roll(games=[GAME_A])
        assert isinstance(roll.rolled_categories([game]), list)

    def test_empty_games_returns_empty(self):
        roll = make_roll(games=[])
        assert roll.rolled_categories([]) == []

    def test_single_game_single_category(self):
        game = make_game(ce_id=GAME_A, categories=["Action"])
        roll = make_roll(games=[GAME_A])
        assert roll.rolled_categories([game]) == ["Action"]

    def test_single_game_multiple_categories(self):
        game = make_game(ce_id=GAME_A, categories=["Action", "Puzzle"])
        roll = make_roll(games=[GAME_A])
        result = roll.rolled_categories([game])
        assert set(result) == {"Action", "Puzzle"}

    def test_two_games_different_categories(self):
        game_a = make_game(ce_id=GAME_A, categories=["Action"])
        game_b = make_game(ce_id=GAME_B, categories=["Strategy"])
        roll = make_roll(games=[GAME_A, GAME_B])
        result = roll.rolled_categories([game_a, game_b])
        assert set(result) == {"Action", "Strategy"}

    def test_duplicate_categories_across_games_deduplicated(self):
        game_a = make_game(ce_id=GAME_A, categories=["Action"])
        game_b = make_game(ce_id=GAME_B, categories=["Action"])
        roll = make_roll(games=[GAME_A, GAME_B])
        result = roll.rolled_categories([game_a, game_b])
        assert result.count("Action") == 1

    def test_three_games_overlapping_categories(self):
        game_a = make_game(ce_id=GAME_A, categories=["Action", "Puzzle"])
        game_b = make_game(ce_id=GAME_B, categories=["Puzzle", "Strategy"])
        game_c = make_game(ce_id=GAME_C, categories=["Strategy"])
        roll = make_roll(games=[GAME_A, GAME_B, GAME_C])
        result = roll.rolled_categories([game_a, game_b, game_c])
        assert set(result) == {"Action", "Puzzle", "Strategy"}

    def test_game_not_in_database_raises(self):
        roll = make_roll(games=[GAME_A])
        with pytest.raises(ValueError, match="Could not find game"):
            roll.rolled_categories([])

    def test_extra_database_games_not_in_roll_ignored(self):
        game_a = make_game(ce_id=GAME_A, categories=["Action"])
        game_b = make_game(ce_id=GAME_B, categories=["Strategy"])
        roll = make_roll(games=[GAME_A])
        result = roll.rolled_categories([game_a, game_b])
        assert "Strategy" not in result
        assert "Action" in result
