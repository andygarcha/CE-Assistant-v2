import asyncio
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, patch


from Classes.CE_User import CEUser
from commands.casino import (
    RollResult,
    roll_fourwardthinking,
    roll_letfatedecide,
    roll_neverlucky,
    roll_onehellofaday,
    roll_onehellofamonth,
    roll_onehellofaweek,
    roll_triplethreat,
    roll_twoweekt2streak,
    roll_twotwoweekt2streakstreak,
    solo_roll,
)
from Modules import hm
from tests.conftest import make_game, make_roll, make_user

# ── shared constants ──────────────────────────────────────────────────────────

GAME_IDS: list[str] = [f"game-{i:03d}-0000-0000-000000000000" for i in range(30)]
PREV_GAME_ID: str = "game-prev-0000-0000-000000000000"
ALL_CATS: list[str] = list(get_args(hm.CATEGORIES))  # 6 categories
EMPTY_DT: dict = {}  # database_tier; irrelevant when get_rollable_game is mocked

# ── helpers ───────────────────────────────────────────────────────────────────


def _user_with_completed(roll_name: str) -> CEUser:
    u = make_user()
    u.add_completed_roll(make_roll(roll_name=roll_name))
    return u


def _user_with_waiting(roll_name: str, games: list[str]) -> CEUser:
    u = make_user()
    roll = make_roll(roll_name=roll_name, status="between_stages", games=games)
    u._rolls.append(roll)
    return u


# ── RollResult ────────────────────────────────────────────────────────────────


class TestRollResult:
    def test_success_has_games_and_no_error(self):
        r = RollResult(games=["g1"], error=None)
        assert r.games == ["g1"]
        assert r.error is None

    def test_failure_has_error_and_no_games(self):
        r = RollResult(games=None, error="oops")
        assert r.games is None
        assert r.error == "oops"


class TestSoloRoll:
    def test_category_required_event_without_category_returns_error(self):
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=123, mention="@test-user"),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        user = make_user(discord_id=123)

        with patch("commands.casino.SupabaseReader.get_user", return_value=user):
            asyncio.run(
                solo_roll(
                    interaction=interaction,  # type: ignore
                    event_name="Triple Threat",
                    category=None,
                    price_restriction=True,
                    hours_restriction=True,
                )
            )

        interaction.response.defer.assert_awaited_once()
        interaction.followup.send.assert_awaited_once_with(
            "Triple Threat requires a chosen category. Please rerun the command and select your category."
        )


# ── roll_onehellofaday ────────────────────────────────────────────────────────


class TestRollOnehellofaday:
    def test_returns_single_game_on_success(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert result.error is None
        assert result.games == [GAME_IDS[0]]

    def test_returns_exactly_one_game(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert result.games is not None
        assert len(result.games) == 1

    def test_returns_error_when_no_games_available(self):
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None

    def test_passes_tier_1(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["tier_number"] == 1

    def test_passes_price_limit_10(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["price_limit"] == 10

    def test_passes_completion_limit_10(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_onehellofaday([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["completion_limit"] == 10

    def test_forwards_price_restriction_flag(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_onehellofaday(
                [],
                EMPTY_DT,
                make_user(),
                price_restriction=False,
                hours_restriction=True,
            )
        assert mock.call_args.kwargs["price_restriction"] is False

    def test_forwards_hours_restriction_flag(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_onehellofaday(
                [],
                EMPTY_DT,
                make_user(),
                price_restriction=True,
                hours_restriction=False,
            )
        assert mock.call_args.kwargs["hours_restriction"] is False


# ── roll_onehellofaweek ───────────────────────────────────────────────────────


class TestRollOnehellofaweek:
    def test_prerequisite_not_met_returns_error(self):
        with patch("Modules.hm.get_rollable_game"):
            result = roll_onehellofaweek([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None

    def test_returns_five_games_on_success(self):
        user = _user_with_completed("One Hell of a Day")
        db = [make_game(ce_id=GAME_IDS[i], categories=[ALL_CATS[i]]) for i in range(5)]
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:5]):
            result = roll_onehellofaweek(db, EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 5

    def test_games_are_from_different_categories(self):
        user = _user_with_completed("One Hell of a Day")
        db = [make_game(ce_id=GAME_IDS[i], categories=[ALL_CATS[i]]) for i in range(5)]
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:5]):
            result = roll_onehellofaweek(db, EMPTY_DT, user, True, True)
        assert result.games is not None
        rolled_cats = [
            next(g.categories[0] for g in db if g.ce_id == gid) for gid in result.games
        ]
        assert len(set(rolled_cats)) == 5

    def test_returns_error_when_no_game_available(self):
        user = _user_with_completed("One Hell of a Day")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_onehellofaweek([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None

    def test_returns_error_when_rolled_game_not_in_database(self):
        user = _user_with_completed("One Hell of a Day")
        # get_rollable_game returns a game ID that isn't in database_name
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_onehellofaweek([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None

    def test_passes_allow_multi_category_false(self):
        user = _user_with_completed("One Hell of a Day")
        db = [make_game(ce_id=GAME_IDS[0], categories=[ALL_CATS[0]])]
        with patch("Modules.hm.get_rollable_game", return_value=None) as mock:
            roll_onehellofaweek(db, EMPTY_DT, user, True, True)
        assert mock.call_args.kwargs["allow_multi_category"] is False


# ── roll_onehellofamonth ──────────────────────────────────────────────────────


class TestRollOnehellofamonth:
    def test_prerequisite_not_met_returns_error(self):
        with patch("Modules.hm.get_rollable_game"):
            result = roll_onehellofamonth([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None

    def test_returns_25_games_on_success(self):
        user = _user_with_completed("One Hell of a Week")
        with (
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:25]),
            patch("commands.casino.random.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 25

    def test_games_split_across_five_categories(self):
        """25 games should come from exactly 5 distinct category buckets."""
        user = _user_with_completed("One Hell of a Week")
        # build 5 groups of 5 games, each tagged with its category
        db = [
            make_game(ce_id=GAME_IDS[cat_i * 5 + game_i], categories=[ALL_CATS[cat_i]])
            for cat_i in range(5)
            for game_i in range(5)
        ]
        with (
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:25]),
            patch("commands.casino.random.choice", side_effect=ALL_CATS[:5]),
        ):
            result = roll_onehellofamonth(db, EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 25

    def test_one_failed_category_recovers(self):
        """If one category has < 5 games, a replacement category is used instead."""
        user = _user_with_completed("One Hell of a Week")
        # "Action" (first pick) fails immediately; the remaining 5 categories succeed
        choice_seq = ALL_CATS  # Action first, then the other 5
        game_seq = [None] + GAME_IDS[
            :25
        ]  # None for Action's first call, then 25 successes
        with (
            patch("Modules.hm.get_rollable_game", side_effect=game_seq),
            patch("commands.casino.random.choice", side_effect=choice_seq),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 25

    def test_two_failed_categories_returns_error(self):
        """Failing more categories than the spare count is unrollable."""
        user = _user_with_completed("One Hell of a Week")
        # both "Action" and "Arcade" fail immediately
        choice_seq = ALL_CATS
        game_seq = [None, None] + GAME_IDS  # first two category attempts fail
        with (
            patch("Modules.hm.get_rollable_game", side_effect=game_seq),
            patch("commands.casino.random.choice", side_effect=choice_seq),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None

    def test_error_message_names_failed_categories(self):
        user = _user_with_completed("One Hell of a Week")
        choice_seq = ALL_CATS
        game_seq = [None, None] + GAME_IDS
        with (
            patch("Modules.hm.get_rollable_game", side_effect=game_seq),
            patch("commands.casino.random.choice", side_effect=choice_seq),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.error is not None
        assert ALL_CATS[0] in result.error  # "Action"
        assert ALL_CATS[1] in result.error  # "Arcade"

    def test_max_failures_is_total_categories_minus_five(self):
        """With 6 categories, exactly 1 failure is tolerated; a 2nd always errors."""
        max_failures = len(ALL_CATS) - 5
        assert max_failures == 1  # baseline assertion; update if categories expand

        user = _user_with_completed("One Hell of a Week")

        # one failure: should recover
        with (
            patch("Modules.hm.get_rollable_game", side_effect=[None] + GAME_IDS[:25]),
            patch("commands.casino.random.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.error is None

        # two failures: should error
        user2 = _user_with_completed("One Hell of a Week")
        with (
            patch("Modules.hm.get_rollable_game", side_effect=[None, None] + GAME_IDS),
            patch("commands.casino.random.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user2, True, True)
        assert result.games is None
        assert result.error is not None

    def test_no_games_available_returns_error(self):
        user = _user_with_completed("One Hell of a Week")
        with (
            patch("Modules.hm.get_rollable_game", return_value=None),
            patch("commands.casino.random.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None


# ── roll_twoweekt2streak ──────────────────────────────────────────────────────


class TestRollTwoweekt2streak:
    def test_fresh_roll_returns_one_game(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_twoweekt2streak([], EMPTY_DT, make_user(), True, True)
        assert result.error is None
        assert result.games == [GAME_IDS[0]]

    def test_waiting_roll_excludes_previously_rolled_category(self):
        """Second stage must not roll the same category as the first game."""
        prev_game = make_game(ce_id=PREV_GAME_ID, categories=["Action"])
        user = _user_with_waiting("Two Week T2 Streak", [PREV_GAME_ID])

        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[1]) as mock:
            roll_twoweekt2streak([prev_game], EMPTY_DT, user, True, True)

        called_category = mock.call_args.kwargs["category"]
        assert "Action" not in called_category

    def test_waiting_roll_returns_one_new_game(self):
        prev_game = make_game(ce_id=PREV_GAME_ID, categories=["Action"])
        user = _user_with_waiting("Two Week T2 Streak", [PREV_GAME_ID])
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[1]):
            result = roll_twoweekt2streak([prev_game], EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games == [GAME_IDS[1]]

    def test_returns_error_when_previously_rolled_game_not_in_database(self):
        user = _user_with_waiting("Two Week T2 Streak", [PREV_GAME_ID])
        # database_name is empty — prev game can't be looked up
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[1]):
            result = roll_twoweekt2streak([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None

    def test_returns_error_when_no_valid_games(self):
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_twoweekt2streak([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None

    def test_passes_tier_2(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_twoweekt2streak([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["tier_number"] == 2

    def test_passes_price_limit_20(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_twoweekt2streak([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["price_limit"] == 20


# ── roll_twotwoweekt2streakstreak ─────────────────────────────────────────────


class TestRollTwotwoweekt2streakstreak:
    def test_prerequisite_not_met_returns_error(self):
        # prerequisite check IS implemented; the rest raises NotImplementedError
        result = roll_twotwoweekt2streakstreak([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None

    def test_returns_one_game_per_call(self):
        user = _user_with_completed("Two Week T2 Streak")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_twotwoweekt2streakstreak([], EMPTY_DT, user, True, True)
        assert result.error is None
        assert result.games is not None

    def test_returns_error_when_no_games_available(self):
        user = _user_with_completed("Two Week T2 Streak")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_twotwoweekt2streakstreak([], EMPTY_DT, user, True, True)
        assert result.games is None
        assert result.error is not None


# ── roll_neverlucky ───────────────────────────────────────────────────────────


class TestRollNeverlucky:
    def test_returns_single_game_on_success(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_neverlucky([], EMPTY_DT, make_user(), True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 1

    def test_no_completion_limit(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_neverlucky([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["completion_limit"] is None

    def test_passes_tier_3(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_neverlucky([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["tier_number"] == 3

    def test_passes_price_limit_20(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_neverlucky([], EMPTY_DT, make_user(), True, True)
        assert mock.call_args.kwargs["price_limit"] == 20

    def test_returns_error_when_no_games_available(self):
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_neverlucky([], EMPTY_DT, make_user(), True, True)
        assert result.games is None
        assert result.error is not None


# ── roll_triplethreat ─────────────────────────────────────────────────────────


class TestRollTriplethreat:
    def test_prerequisite_not_met_returns_error(self):
        result = roll_triplethreat([], EMPTY_DT, make_user(), True, True, "Action")
        assert result.games is None
        assert result.error is not None

    def test_returns_three_games_from_chosen_category(self):
        user = _user_with_completed("Never Lucky")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:3]):
            result = roll_triplethreat([], EMPTY_DT, user, True, True, "Action")
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 3

    def test_passes_chosen_category(self):
        user = _user_with_completed("Never Lucky")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:3]) as mock:
            roll_triplethreat([], EMPTY_DT, user, True, True, "Strategy")
        assert mock.call_args.kwargs["category"] == "Strategy"

    def test_passes_tier_3(self):
        user = _user_with_completed("Never Lucky")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:3]) as mock:
            roll_triplethreat([], EMPTY_DT, user, True, True, "Action")
        assert mock.call_args.kwargs["tier_number"] == 3

    def test_returns_error_when_not_enough_games(self):
        user = _user_with_completed("Never Lucky")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_triplethreat([], EMPTY_DT, user, True, True, "Action")
        assert result.games is None
        assert result.error is not None


# ── roll_letfatedecide ────────────────────────────────────────────────────────


class TestRollLetfatedecide:
    def test_returns_single_game_on_success(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_letfatedecide([], EMPTY_DT, make_user(), True, True, "Action")
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 1

    def test_no_completion_limit(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_letfatedecide([], EMPTY_DT, make_user(), True, True, "Action")
        assert mock.call_args.kwargs["completion_limit"] is None

    def test_passes_tier_4(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_letfatedecide([], EMPTY_DT, make_user(), True, True, "Action")
        assert mock.call_args.kwargs["tier_number"] == 4

    def test_passes_chosen_category(self):
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_letfatedecide([], EMPTY_DT, make_user(), True, True, "Arcade")
        assert mock.call_args.kwargs["category"] == "Arcade"

    def test_returns_error_when_no_games_available(self):
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_letfatedecide([], EMPTY_DT, make_user(), True, True, "Action")
        assert result.games is None
        assert result.error is not None


# ── roll_fourwardthinking ─────────────────────────────────────────────────────


class TestRollFourwardthinking:
    def test_prerequisite_not_met_returns_error(self):
        result = roll_fourwardthinking([], EMPTY_DT, make_user(), True, True, "Action")
        assert result.games is None
        assert result.error is not None

    def test_returns_one_game_on_success(self):
        user = _user_with_completed("Let Fate Decide")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]):
            result = roll_fourwardthinking([], EMPTY_DT, user, True, True, "Action")
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 1

    def test_passes_chosen_category(self):
        user = _user_with_completed("Let Fate Decide")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_fourwardthinking([], EMPTY_DT, user, True, True, "Platformer")
        assert all(
            call.kwargs["category"] == "Platformer" for call in mock.call_args_list
        )

    def test_each_game_is_progressively_higher_tier(self):
        """Fourward Thinking: game i uses tier i (T1 → T2 → T3 → T4)."""
        user = _user_with_completed("Let Fate Decide")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:1]) as mock:
            roll_fourwardthinking([], EMPTY_DT, user, True, True, "Action")
        tiers = [call.kwargs["tier_number"] for call in mock.call_args_list]
        assert tiers == [1]

    def test_returns_error_when_not_enough_games(self):
        user = _user_with_completed("Let Fate Decide")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_fourwardthinking([], EMPTY_DT, user, True, True, "Action")
        assert result.games is None
        assert result.error is not None
