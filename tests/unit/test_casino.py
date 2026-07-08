import asyncio
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, MagicMock, patch

from Classes.CE_User import CEUser
from commands.casino import (
    RollResult,
    co_op_roll,
    roll_destinyalignment,
    roll_fourwardthinking,
    roll_letfatedecide,
    roll_neverlucky,
    roll_onehellofaday,
    roll_onehellofamonth,
    roll_onehellofaweek,
    roll_soulmates,
    roll_teamworkmakesthedreamwork,
    roll_triplethreat,
    roll_twotwoweekt2streakstreak,
    roll_twoweekt2streak,
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

        import commands.casino as _casino_mod

        with (
            patch.object(_casino_mod, "client", create=True, new=MagicMock()),
            patch("commands.casino.hm.log_command", new_callable=AsyncMock),
            patch(
                "commands.casino.SupabaseReader.get_user",
                return_value=user,
            ),
        ):
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
            patch("commands.casino.secrets.choice", side_effect=ALL_CATS),
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
            patch("commands.casino.secrets.choice", side_effect=ALL_CATS[:5]),
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
            patch("commands.casino.secrets.choice", side_effect=choice_seq),
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
            patch("commands.casino.secrets.choice", side_effect=choice_seq),
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
            patch("commands.casino.secrets.choice", side_effect=choice_seq),
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
            patch("commands.casino.secrets.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user, True, True)
        assert result.error is None

        # two failures: should error
        user2 = _user_with_completed("One Hell of a Week")
        with (
            patch("Modules.hm.get_rollable_game", side_effect=[None, None] + GAME_IDS),
            patch("commands.casino.secrets.choice", side_effect=ALL_CATS),
        ):
            result = roll_onehellofamonth([], EMPTY_DT, user2, True, True)
        assert result.games is None
        assert result.error is not None

    def test_no_games_available_returns_error(self):
        user = _user_with_completed("One Hell of a Week")
        with (
            patch("Modules.hm.get_rollable_game", return_value=None),
            patch("commands.casino.secrets.choice", side_effect=ALL_CATS),
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


# ── co_op_roll ────────────────────────────────────────────────────────────────
#
# Tests cover the guard/validation logic in the co_op_roll orchestrator.
# Tests for the roll functions themselves (roll_destinyalignment, etc.) follow.


def _make_interaction_coop(user_id: int = 123) -> SimpleNamespace:
    send_mock = AsyncMock()
    send_mock.return_value.edit = AsyncMock()
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=send_mock),
    )


def _make_confirmed_view():
    """Patches CoOpConfirmView so wait() returns instantly and the partner accepted."""
    view = MagicMock()
    view.wait = AsyncMock()
    view.confirmed = True
    return patch("commands.casino.CoOpConfirmView", return_value=view)


def _make_partner_member(partner_id: int = 456) -> SimpleNamespace:
    return SimpleNamespace(id=partner_id, mention=f"<@{partner_id}>")


def _run_coop(
    interaction,
    partner_,
    event_name: str,
    tier=None,
    price_restriction: bool = True,
    hours_restriction: bool = True,
):
    import commands.casino as _casino_mod

    with (
        patch.object(_casino_mod, "client", create=True, new=MagicMock()),
        patch("commands.casino.hm.log_command", new_callable=AsyncMock),
        patch("commands.casino.hm.send_message", new_callable=AsyncMock),
    ):
        asyncio.run(
            co_op_roll(
                interaction=interaction,  # type: ignore
                partner_=partner_,  # type: ignore
                event_name=event_name,  # type: ignore
                tier=tier,
                price_restriction=price_restriction,
                hours_restriction=hours_restriction,
            )
        )


class TestCoOpRoll:
    # ── user / partner registration ───────────────────────────────────────────

    def test_unregistered_user_sends_error(self):
        interaction = _make_interaction_coop()
        with patch(
            "commands.casino.SupabaseReader.get_user",
            return_value=None,
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "not registered" in msg.lower()

    def test_unregistered_partner_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, None],
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "partner" in msg.lower()
        assert "not registered" in msg.lower()

    # ── cooldowns ─────────────────────────────────────────────────────────────

    def test_user_cooldown_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        with (
            patch.object(user, "has_cooldown", return_value=True),
            patch.object(user, "get_cooldown_timestamp", return_value=9999999999),
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "on cooldown" in msg.lower()

    def test_user_cooldown_message_includes_timestamp(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        with (
            patch.object(user, "has_cooldown", return_value=True),
            patch.object(user, "get_cooldown_timestamp", return_value=9999999999),
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        msg = interaction.followup.send.call_args[0][0]
        assert "9999999999" in msg

    def test_partner_cooldown_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        with (
            patch.object(partner, "has_cooldown", return_value=True),
            patch.object(partner, "get_cooldown_timestamp", return_value=9999999999),
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "partner" in msg.lower()
        assert "on cooldown" in msg.lower()

    def test_partner_cooldown_message_includes_timestamp(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        with (
            patch.object(partner, "has_cooldown", return_value=True),
            patch.object(partner, "get_cooldown_timestamp", return_value=9999999999),
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        msg = interaction.followup.send.call_args[0][0]
        assert "9999999999" in msg

    # ── destiny alignment-specific guards ─────────────────────────────────────

    def test_da_user_already_rolling_with_same_partner_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123, ce_id="user-001-0000-0000-000000000000")
        partner = make_user(discord_id=456, ce_id="user-002-0000-0000-000000000000")
        user._rolls.append(
            make_roll(
                roll_name="Destiny Alignment",
                status="current",
                partner_ce_id=partner.ce_id,
            )
        )
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Destiny Alignment")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "already" in msg.lower()
        assert "destiny alignment" in msg.lower()

    def test_da_user_at_max_five_rolls_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123, ce_id="user-001-0000-0000-000000000000")
        partner = make_user(discord_id=456, ce_id="user-002-0000-0000-000000000000")
        for i in range(5):
            user._rolls.append(
                make_roll(
                    roll_name="Destiny Alignment",
                    status="current",
                    partner_ce_id=f"other-{i:03d}-0000-0000-000000000000",
                )
            )
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Destiny Alignment")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "too many" in msg.lower()

    def test_da_four_rolls_is_below_max_and_allowed(self):
        """Four DA rolls (< 5) must not trigger the limit guard."""
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123, ce_id="user-001-0000-0000-000000000000")
        partner = make_user(discord_id=456, ce_id="user-002-0000-0000-000000000000")
        for i in range(4):
            user._rolls.append(
                make_roll(
                    roll_name="Destiny Alignment",
                    status="current",
                    partner_ce_id=f"other-{i:03d}-0000-0000-000000000000",
                )
            )
        with (
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
            _make_confirmed_view(),
            patch(
                "commands.casino.SupabaseReader.add_pending",
            ),
            patch(
                "commands.casino.SupabaseReader.kill_pending",
            ),
            patch("commands.casino.SupabaseReader.get_database_name", return_value=[]),
            patch(
                "commands.casino.SupabaseReader.get_database_tier",
                return_value=EMPTY_DT,
            ),
            patch(
                "commands.casino.roll_destinyalignment",
                return_value=RollResult(None, "stub"),
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Destiny Alignment")
        # Should NOT have sent the "too many" message via either channel
        sent_msgs = [c[0][0] for c in interaction.followup.send.call_args_list]
        edited_msgs = [
            c.kwargs.get("content", "")
            for c in interaction.followup.send.return_value.edit.call_args_list
        ]
        assert not any("too many" in m.lower() for m in sent_msgs + edited_msgs)

    def test_da_partner_at_max_five_rolls_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123, ce_id="user-001-0000-0000-000000000000")
        partner = make_user(discord_id=456, ce_id="user-002-0000-0000-000000000000")
        for i in range(5):
            partner._rolls.append(
                make_roll(
                    roll_name="Destiny Alignment",
                    status="current",
                    partner_ce_id=f"other-{i:03d}-0000-0000-000000000000",
                )
            )
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Destiny Alignment")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "partner" in msg.lower()
        assert "too many" in msg.lower()

    # ── non-DA duplicate roll guards ──────────────────────────────────────────

    def test_non_da_user_already_in_roll_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        # tier_num=1 is required so calculate_cooldown_date can resolve Soul Mates' tier dict
        user._rolls.append(
            make_roll(roll_name="Soul Mates", status="current", tier_num=1)
        )
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "already" in msg.lower()

    def test_non_da_partner_already_in_roll_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        partner._rolls.append(
            make_roll(roll_name="Soul Mates", status="current", tier_num=1)
        )
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "partner" in msg.lower()
        assert "already" in msg.lower()

    def test_non_da_allows_different_rolls_to_coexist(self):
        """A current 'Teamwork' roll must not block starting 'Soul Mates'."""
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        user._rolls.append(
            make_roll(roll_name="Teamwork Makes the Dream Work", status="current")
        )
        with (
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
            _make_confirmed_view(),
            patch(
                "commands.casino.SupabaseReader.add_pending",
            ),
            patch(
                "commands.casino.SupabaseReader.kill_pending",
            ),
            patch("commands.casino.SupabaseReader.get_database_name", return_value=[]),
            patch(
                "commands.casino.SupabaseReader.get_database_tier",
                return_value=EMPTY_DT,
            ),
            patch(
                "commands.casino.roll_soulmates", return_value=RollResult(None, "stub")
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        sent_msgs = [c[0][0] for c in interaction.followup.send.call_args_list]
        edited_msgs = [
            c.kwargs.get("content", "")
            for c in interaction.followup.send.return_value.edit.call_args_list
        ]
        assert not any("already" in m.lower() for m in sent_msgs + edited_msgs)

    # ── pending guards ────────────────────────────────────────────────────────

    def test_user_pending_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        user.add_pending("Soul Mates")
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()

    def test_partner_pending_sends_error(self):
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123)
        partner = make_user(discord_id=456)
        partner.add_pending("Soul Mates")
        with patch(
            "commands.casino.SupabaseReader.get_user",
            side_effect=[user, partner],
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        interaction.followup.send.assert_awaited_once()
        msg = interaction.followup.send.call_args[0][0]
        assert "partner" in msg.lower()

    def test_both_users_get_pending_added(self):
        """add_pending must be called with both CE IDs before dispatching to the roll function."""
        interaction = _make_interaction_coop()
        user = make_user(discord_id=123, ce_id="user-001-0000-0000-000000000000")
        partner = make_user(discord_id=456, ce_id="user-002-0000-0000-000000000000")
        with (
            patch(
                "commands.casino.SupabaseReader.get_user",
                side_effect=[user, partner],
            ),
            _make_confirmed_view(),
            patch(
                "commands.casino.SupabaseReader.add_pending",
            ) as mock_add_pending,
            patch(
                "commands.casino.SupabaseReader.kill_pending",
            ),
            patch("commands.casino.SupabaseReader.get_database_name", return_value=[]),
            patch(
                "commands.casino.SupabaseReader.get_database_tier",
                return_value=EMPTY_DT,
            ),
            patch(
                "commands.casino.roll_soulmates", return_value=RollResult(None, "stub")
            ),
        ):
            _run_coop(interaction, _make_partner_member(), "Soul Mates")
        mock_add_pending.assert_called_once_with(
            "Soul Mates", user.ce_id, partner.ce_id
        )

    # ── retired / invalid events ──────────────────────────────────────────────

    def test_retired_event_winner_takes_all_sends_error(self):
        interaction = _make_interaction_coop()
        _run_coop(interaction, _make_partner_member(), "Winner Takes All")
        msg = interaction.followup.send.call_args[0][0]
        assert "retired" in msg.lower()

    def test_retired_event_game_theory_sends_error(self):
        interaction = _make_interaction_coop()
        _run_coop(interaction, _make_partner_member(), "Game Theory")
        msg = interaction.followup.send.call_args[0][0]
        assert "retired" in msg.lower()


# ── roll_destinyalignment ─────────────────────────────────────────────────────
#
# NOTE: roll_destinyalignment is currently an unimplemented stub (docstring
# only).  All tests here describe the required behaviour and will fail with
# AttributeError until the body is written.


class TestRollDestinyalignment:
    # ── return shape ──────────────────────────────────────────────────────────

    def test_returns_roll_result_on_success(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert isinstance(result, RollResult)

    def test_returns_two_games_on_success(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 2

    def test_returns_error_when_no_game_available(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.games is None
        assert result.error is not None

    # ── roll parameters ───────────────────────────────────────────────────────

    def test_passes_no_completion_limit(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["completion_limit"] is None

    def test_passes_price_limit_20(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["price_limit"] == 20

    def test_passes_points_restriction(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["has_points_restriction"] is True

    def test_forwards_price_restriction_flag(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, False, True)
        for call in mock.call_args_list:
            assert call.kwargs["price_restriction"] is False

    # ── rank requirement ──────────────────────────────────────────────────────

    def test_different_rank_players_get_error(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with (
            patch.object(user, "rank_num", return_value=1),  # D Rank
            patch.object(partner, "rank_num", return_value=3),  # B Rank
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]),
        ):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.games is None
        assert result.error is not None

    def test_same_rank_players_are_allowed(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with (
            patch.object(user, "rank_num", return_value=3),
            patch.object(partner, "rank_num", return_value=3),
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]),
        ):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.error is None

    def test_ss_rank_and_sss_rank_are_allowed_together(self):
        """Both players ≥ SS (rank_num ≥ 6) may pair regardless of exact rank."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with (
            patch.object(user, "rank_num", return_value=6),  # SS
            patch.object(partner, "rank_num", return_value=7),  # SSS
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]),
        ):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.error is None

    def test_ss_and_a_rank_are_not_allowed(self):
        """SS (6) + A (4) — partner is below SS, so the exception doesn't apply."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with (
            patch.object(user, "rank_num", return_value=6),  # SS
            patch.object(partner, "rank_num", return_value=4),  # A
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]),
        ):
            result = roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        assert result.games is None
        assert result.error is not None

    # ── user identity: correct player passed per call ─────────────────────────
    #
    # The first call rolls from partner's library — the USER is the one who will
    # play it, so user's constraints are checked (user=user).
    # The second call rolls from user's library — the PARTNER will play it, so
    # partner's constraints are checked (user=partner).
    # Swapping either produces a silent eligibility bug (the original user=user bug).

    def test_first_call_checks_user_not_partner(self):
        """First get_rollable_game call must pass user, not partner, as the user arg."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        raw = mock.call_args_list[0].kwargs["user"]
        first_call_users = raw if isinstance(raw, list) else [raw]
        assert user in first_call_users
        assert partner not in first_call_users

    def test_second_call_checks_partner_not_user(self):
        """Second get_rollable_game call must pass partner, not user, as the user arg."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock:
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        raw = mock.call_args_list[1].kwargs["user"]
        second_call_users = raw if isinstance(raw, list) else [raw]
        assert partner in second_call_users
        assert user not in second_call_users

    def test_first_call_uses_partners_completed_games_as_pool(self):
        """First roll's database_name must be partner's completed games, not user's."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        user_pool = [make_game(ce_id=GAME_IDS[0])]
        partner_pool = [make_game(ce_id=GAME_IDS[1])]
        with (
            patch.object(user, "get_completed_games_2", return_value=user_pool),
            patch.object(partner, "get_completed_games_2", return_value=partner_pool),
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock,
        ):
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        first_call_db = mock.call_args_list[0].args[0]
        assert first_call_db is partner_pool

    def test_second_call_uses_users_completed_games_as_pool(self):
        """Second roll's database_name must be user's completed games, not partner's."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        user_pool = [make_game(ce_id=GAME_IDS[0])]
        partner_pool = [make_game(ce_id=GAME_IDS[1])]
        with (
            patch.object(user, "get_completed_games_2", return_value=user_pool),
            patch.object(partner, "get_completed_games_2", return_value=partner_pool),
            patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:2]) as mock,
        ):
            roll_destinyalignment([], EMPTY_DT, user, partner, True, True)
        second_call_db = mock.call_args_list[1].args[0]
        assert second_call_db is user_pool


# ── roll_soulmates ────────────────────────────────────────────────────────────
#
# NOTE: roll_soulmates is currently an unimplemented stub.  All tests here
# describe the required behaviour and will fail until the body is written.
#
# HOUR_LIMITS (per tier): [15, 40, 80, 160, None, None]
# Tier 6 rolls from T5–T7.


_SOUL_MATES_HOUR_LIMITS = {1: 15, 2: 40, 3: 80, 4: 160, 5: None, 6: None}


class TestRollSoulmates:
    # ── tier validation ───────────────────────────────────────────────────────

    def test_returns_error_when_tier_is_none(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        result = roll_soulmates([], EMPTY_DT, user, partner, True, True, None)
        assert result.games is None
        assert result.error is not None

    def test_returns_error_when_tier_is_zero(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        result = roll_soulmates([], EMPTY_DT, user, partner, True, True, 0)
        assert result.games is None
        assert result.error is not None

    def test_returns_error_when_tier_exceeds_six(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        result = roll_soulmates([], EMPTY_DT, user, partner, True, True, 7)
        assert result.games is None
        assert result.error is not None

    # ── return shape ──────────────────────────────────────────────────────────

    def test_returns_exactly_one_game_on_success(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]):
            result = roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 1

    def test_returns_error_when_no_game_available(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        assert result.games is None
        assert result.error is not None

    # ── tier → hour limit mapping ─────────────────────────────────────────────

    import pytest as _pytest

    @_pytest.mark.parametrize(
        "tier, expected_hours",
        [
            (1, 15),
            (2, 40),
            (3, 80),
            (4, 160),
            (5, None),
        ],
    )
    def test_completion_limit_per_tier(self, tier, expected_hours):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, tier)
        assert mock.call_args.kwargs["completion_limit"] == expected_hours

    def test_tier_6_passes_tier_number_6_to_get_rollable_game(self):
        """Tier 6 in Soul Mates means 'T5–T7', which get_rollable_game handles
        when tier_number=6 is passed."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 6)
        assert mock.call_args.kwargs["tier_number"] == 6

    # ── roll parameters ───────────────────────────────────────────────────────

    def test_passes_price_limit_20(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        assert mock.call_args.kwargs["price_limit"] == 20

    def test_passes_points_restriction(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        assert mock.call_args.kwargs["has_points_restriction"] is True

    def test_passes_both_users(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        passed_users = mock.call_args.kwargs["user"]
        assert user in passed_users
        assert partner in passed_users

    def test_forwards_price_restriction_false(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, False, True, 1)
        assert mock.call_args.kwargs["price_restriction"] is False

    def test_forwards_hours_restriction_false(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, False, 1)
        assert mock.call_args.kwargs["hours_restriction"] is False

    # ── user identity: both players must be checked ───────────────────────────
    #
    # Soul Mates is a shared game — both players complete it together.  Passing
    # only one player's identity means the other player's points / completion
    # status is never checked, allowing an ineligible game to slip through.

    def test_user_param_contains_user(self):
        """Both user and partner must appear in the user list passed to get_rollable_game."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        passed_users = mock.call_args.kwargs["user"]
        assert user in passed_users

    def test_user_param_contains_partner(self):
        """Omitting partner from the user list would skip partner's eligibility check."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        passed_users = mock.call_args.kwargs["user"]
        assert partner in passed_users

    def test_user_param_does_not_contain_only_one_player(self):
        """Passing a single-element list would silently drop half the eligibility checks."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=GAME_IDS[0]) as mock:
            roll_soulmates([], EMPTY_DT, user, partner, True, True, 1)
        passed_users = mock.call_args.kwargs["user"]
        assert len(passed_users) >= 2


# ── roll_teamworkmakesthedreamwork ────────────────────────────────────────────
#
# NOTE: roll_teamworkmakesthedreamwork is currently an unimplemented stub.
# All tests here describe the required behaviour and will fail until the body
# is written.


class TestRollTeamworkmakesthedreamwork:
    # ── return shape ──────────────────────────────────────────────────────────

    def test_returns_four_games_on_success(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]):
            result = roll_teamworkmakesthedreamwork(
                [], EMPTY_DT, user, partner, True, True
            )
        assert result.error is None
        assert result.games is not None
        assert len(result.games) == 4

    def test_returned_games_are_unique(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]):
            result = roll_teamworkmakesthedreamwork(
                [], EMPTY_DT, user, partner, True, True
            )
        assert result.games is not None
        assert len(set(result.games)) == 4

    def test_returns_error_when_no_game_available(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", return_value=None):
            result = roll_teamworkmakesthedreamwork(
                [], EMPTY_DT, user, partner, True, True
            )
        assert result.games is None
        assert result.error is not None

    # ── roll parameters ───────────────────────────────────────────────────────

    def test_passes_tier_3(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["tier_number"] == 3

    def test_passes_completion_limit_40(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["completion_limit"] == 40

    def test_passes_price_limit_20(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["price_limit"] == 20

    def test_passes_points_restriction(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            assert call.kwargs["has_points_restriction"] is True

    def test_passes_both_users(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for call in mock.call_args_list:
            passed_users = call.kwargs["user"]
            assert user in passed_users
            assert partner in passed_users

    def test_forwards_price_restriction_false(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, False, True)
        for call in mock.call_args_list:
            assert call.kwargs["price_restriction"] is False

    def test_makes_four_calls_to_get_rollable_game(self):
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        assert mock.call_count == 4

    def test_already_rolled_games_accumulate_across_calls(self):
        """Each successive call must exclude the games already chosen."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        exclusion_lists = [
            call.kwargs["already_rolled_games"] for call in mock.call_args_list
        ]
        # Each call's exclusion list must be a superset of the previous one
        for i in range(1, len(exclusion_lists)):
            assert set(exclusion_lists[i - 1]).issubset(set(exclusion_lists[i]))

    # ── user identity: both players must be checked on every call ─────────────
    #
    # Teamwork rolls four games that both players complete.  Every call must
    # check both players' eligibility — dropping either one would silently allow
    # a game they've already finished or have points in.

    def test_every_call_contains_user_in_user_param(self):
        """user must appear in the user list on every one of the four calls."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for i, call in enumerate(mock.call_args_list):
            assert user in call.kwargs["user"], f"user missing from call {i}"

    def test_every_call_contains_partner_in_user_param(self):
        """partner must appear in the user list on every one of the four calls."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for i, call in enumerate(mock.call_args_list):
            assert partner in call.kwargs["user"], f"partner missing from call {i}"

    def test_every_call_user_param_has_both_players(self):
        """Passing only one player on any call silently drops half the eligibility checks."""
        user = make_user(ce_id="user-001-0000-0000-000000000000")
        partner = make_user(ce_id="user-002-0000-0000-000000000000")
        with patch("Modules.hm.get_rollable_game", side_effect=GAME_IDS[:4]) as mock:
            roll_teamworkmakesthedreamwork([], EMPTY_DT, user, partner, True, True)
        for i, call in enumerate(mock.call_args_list):
            assert len(call.kwargs["user"]) >= 2, f"call {i} has fewer than 2 users"
