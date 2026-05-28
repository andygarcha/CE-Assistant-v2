import pytest

from Classes.CE_Roll import CASINO_POINTS, relative
from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import (
    make_game,
    make_objective,
    make_roll,
    make_user,
    make_user_game,
    make_user_objective,
)

GAME_ID_A = "game-aaa-0000-0000-000000000000"
GAME_ID_B = "game-bbb-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _user_game(ce_id: str, points: int) -> object:
    """User game whose single primary objective gives `points` user points."""
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=ce_id, user_points=points)
    return make_user_game(ce_id=ce_id, user_objectives=[uobj])


# ── rank_num ──────────────────────────────────────────────────────────────────


class TestRankNum:
    @pytest.mark.parametrize(
        "total_points, expected_rank",
        [
            (0, 0),  # E
            (49, 0),  # E (just below D threshold)
            (50, 1),  # D
            (249, 1),  # D
            (250, 2),  # C
            (499, 2),  # C
            (500, 3),  # B
            (999, 3),  # B
            (1000, 4),  # A
            (2499, 4),  # A
            (2500, 5),  # S
            (4999, 5),  # S
            (5000, 6),  # SS
            (7499, 6),  # SS
            (7500, 7),  # SSS
            (9999, 7),  # SSS
            (10000, 8),  # EX
            (99999, 8),  # EX (no upper bound)
        ],
    )
    def test_rank_boundaries(self, total_points, expected_rank):
        user = make_user(owned_games=[_user_game(GAME_ID_A, total_points)])
        assert user.rank_num() == expected_rank


# ── get_rank ──────────────────────────────────────────────────────────────────


class TestGetRank:
    @pytest.mark.parametrize(
        "points, expected_str",
        [
            (0, "E Rank"),
            (50, "D Rank"),
            (250, "C Rank"),
            (500, "B Rank"),
            (1000, "A Rank"),
            (2500, "S Rank"),
            (5000, "SS Rank"),
            (7500, "SSS Rank"),
            (10000, "EX Rank"),
        ],
    )
    def test_rank_strings(self, points, expected_str):
        user = make_user(owned_games=[_user_game(GAME_ID_A, points)])
        assert user.get_rank() == expected_str


# ── get_total_points ──────────────────────────────────────────────────────────


class TestGetTotalPoints:
    def test_sums_across_games(self):
        user = make_user(
            owned_games=[
                _user_game(GAME_ID_A, 100),
                _user_game(GAME_ID_B, 200),
            ]
        )
        assert user.get_total_points() == 300

    def test_no_games_zero_points(self):
        assert make_user(owned_games=[]).get_total_points() == 0


# ── owns_game ─────────────────────────────────────────────────────────────────


class TestOwnsGame:
    def test_owned_game_found(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.owns_game(GAME_ID_A) is True

    def test_unowned_game_not_found(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.owns_game(GAME_ID_B) is False

    def test_empty_games_returns_false(self):
        assert make_user(owned_games=[]).owns_game(GAME_ID_A) is False


# ── has_points ────────────────────────────────────────────────────────────────


class TestHasPoints:
    def test_game_with_points_returns_true(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.has_points(GAME_ID_A) is True

    def test_game_with_zero_points_returns_false(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 0)])
        assert user.has_points(GAME_ID_A) is False

    def test_unowned_game_returns_false(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.has_points(GAME_ID_B) is False


# ── get_owned_game ────────────────────────────────────────────────────────────


class TestGetOwnedGame:
    def test_returns_matching_game(self):
        ug = _user_game(GAME_ID_A, 10)
        user = make_user(owned_games=[ug])
        assert user.get_owned_game(GAME_ID_A) is ug

    def test_returns_none_when_not_found(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.get_owned_game(GAME_ID_B) is None


# ── remove_owned_game ─────────────────────────────────────────────────────────


class TestRemoveOwnedGame:
    def test_removes_existing_game(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        result = user.remove_owned_game(GAME_ID_A)
        assert result is True
        assert user.owns_game(GAME_ID_A) is False

    def test_returns_false_for_missing_game(self):
        user = make_user(owned_games=[])
        assert user.remove_owned_game(GAME_ID_A) is False


# ── replace_owned_game ────────────────────────────────────────────────────────


class TestReplaceOwnedGame:
    def test_replaces_existing_game(self):
        old = _user_game(GAME_ID_A, 10)
        new = _user_game(GAME_ID_A, 99)
        user = make_user(owned_games=[old])
        result = user.replace_owned_game(new)
        assert result is True
        assert user.get_owned_game(GAME_ID_A) is new

    def test_returns_false_when_no_match(self):
        user = make_user(owned_games=[_user_game(GAME_ID_A, 10)])
        assert user.replace_owned_game(_user_game(GAME_ID_B, 10)) is False


# ── on_mutelist ───────────────────────────────────────────────────────────────


class TestOnMutelist:
    def test_mutelist_id_returns_true(self):
        muted_id = MUTELIST_CEIDS[0]
        user = make_user(ce_id=muted_id)
        assert user.on_mutelist() is True

    def test_regular_id_returns_false(self):
        assert make_user(ce_id="not-on-mutelist-000000000000").on_mutelist() is False


# ── mention ───────────────────────────────────────────────────────────────────


class TestMention:
    def test_mention_format(self):
        user = make_user(discord_id=123456789)
        assert user.mention() == "<@123456789>"


# ── completions ───────────────────────────────────────────────────────────────


def _completed_ug(game_id: str, points: int = 100):
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=game_id, user_points=points)
    return make_user_game(ce_id=game_id, user_objectives=[uobj])


def _db_game(game_id: str, points: int = 100):
    obj = make_objective(ce_id=OBJ_ID, point_value=points, game_ce_id=game_id)
    return make_game(ce_id=game_id, objectives=[obj])


class TestCompletions:
    def test_no_games_returns_zero(self):
        user = make_user(owned_games=[])
        assert user.completions([]) == 0

    def test_one_completed_game_returns_one(self):
        game = _db_game(GAME_ID_A)
        user = make_user(owned_games=[_completed_ug(GAME_ID_A)])
        assert user.completions([game]) == 1

    def test_incomplete_game_not_counted(self):
        game = _db_game(GAME_ID_A)
        ug = make_user_game(ce_id=GAME_ID_A, user_objectives=[])
        user = make_user(owned_games=[ug])
        assert user.completions([game]) == 0

    def test_two_completed_one_incomplete(self):
        game_a = _db_game(GAME_ID_A)
        game_b = _db_game(GAME_ID_B)
        ug_incomplete = make_user_game(ce_id=GAME_ID_B, user_objectives=[])
        user = make_user(owned_games=[_completed_ug(GAME_ID_A), ug_incomplete])
        assert user.completions([game_a, game_b]) == 1


# ── get_completed_games_2 ─────────────────────────────────────────────────────


class TestGetCompletedGames2:
    def test_returns_list(self):
        user = make_user(owned_games=[])
        assert isinstance(user.get_completed_games_2([]), list)

    def test_empty_games_returns_empty_list(self):
        user = make_user(owned_games=[])
        assert user.get_completed_games_2([]) == []

    def test_completed_game_appears_in_result(self):
        game = _db_game(GAME_ID_A)
        user = make_user(owned_games=[_completed_ug(GAME_ID_A)])
        result = user.get_completed_games_2([game])
        assert len(result) == 1
        assert result[0].ce_id == GAME_ID_A

    def test_incomplete_game_excluded(self):
        game = _db_game(GAME_ID_A)
        ug = make_user_game(ce_id=GAME_ID_A, user_objectives=[])
        user = make_user(owned_games=[ug])
        assert user.get_completed_games_2([game]) == []

    def test_returns_cegame_objects(self):
        from Classes.CE_Game import CEGame

        game = _db_game(GAME_ID_A)
        user = make_user(owned_games=[_completed_ug(GAME_ID_A)])
        result = user.get_completed_games_2([game])
        assert all(isinstance(g, CEGame) for g in result)

    def test_game_not_in_database_excluded(self):
        user = make_user(owned_games=[_completed_ug(GAME_ID_A)])
        assert user.get_completed_games_2([]) == []

    def test_raises_on_none_database(self):
        user = make_user(owned_games=[])
        with pytest.raises(ValueError):
            user.get_completed_games_2(None)

    def test_raises_on_database_containing_none(self):
        user = make_user(owned_games=[])
        with pytest.raises(ValueError):
            user.get_completed_games_2([None])


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEUserToDict:
    def test_returns_dict(self):
        assert isinstance(make_user().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_user().to_dict()
        for key in ("ce_id", "discord_id", "owned_games", "rolls"):
            assert key in result


# ── casino_score ──────────────────────────────────────────────────────────────


class TestCasinoScore:
    # ── baseline ──────────────────────────────────────────────────────────────

    def test_no_rolls_returns_zero(self):
        assert make_user().casino_score([]) == 0

    def test_returns_int(self):
        assert isinstance(make_user().casino_score([]), int)

    # ── non-terminal statuses are ignored ────────────────────────────────────

    @pytest.mark.parametrize("status", ["current", "pending", "waiting", "removed"])
    def test_non_terminal_status_not_counted(self, status):
        roll = make_roll(roll_name="One Hell of a Week", status=status)
        assert make_user().casino_score([roll]) == 0

    # ── won rolls add casino_increase() ──────────────────────────────────────

    @pytest.mark.parametrize(
        "roll_name, expected_increase",
        [
            ("One Hell of a Day", CASINO_POINTS["One Hell of a Day"][0]),
            ("One Hell of a Week", CASINO_POINTS["One Hell of a Week"][0]),
            ("One Hell of a Month", CASINO_POINTS["One Hell of a Month"][0]),
            ("Never Lucky", CASINO_POINTS["Never Lucky"][0]),
            ("Triple Threat", CASINO_POINTS["Triple Threat"][0]),
            ("Let Fate Decide", CASINO_POINTS["Let Fate Decide"][0]),
            ("Fourward Thinking", CASINO_POINTS["Fourward Thinking"][0]),
            ("Game Theory", CASINO_POINTS["Game Theory"][0]),
            ("Teamwork Makes the Dream Work", CASINO_POINTS["Teamwork Makes the Dream Work"][0]),
        ],
    )
    def test_won_fixed_roll_adds_correct_increase(self, roll_name, expected_increase):
        roll = make_roll(roll_name=roll_name, status="won")
        assert make_user().casino_score([roll]) == expected_increase

    # ── failed rolls add casino_decrease() ───────────────────────────────────

    @pytest.mark.parametrize(
        "roll_name, expected_decrease",
        [
            ("One Hell of a Day", CASINO_POINTS["One Hell of a Day"][1]),
            ("One Hell of a Week", CASINO_POINTS["One Hell of a Week"][1]),
            ("One Hell of a Month", CASINO_POINTS["One Hell of a Month"][1]),
            ("Never Lucky", CASINO_POINTS["Never Lucky"][1]),
            ("Triple Threat", CASINO_POINTS["Triple Threat"][1]),
            ("Let Fate Decide", CASINO_POINTS["Let Fate Decide"][1]),
            ("Fourward Thinking", CASINO_POINTS["Fourward Thinking"][1]),
            ("Game Theory", CASINO_POINTS["Game Theory"][1]),
            ("Teamwork Makes the Dream Work", CASINO_POINTS["Teamwork Makes the Dream Work"][1]),
        ],
    )
    def test_failed_fixed_roll_adds_correct_decrease(self, roll_name, expected_decrease):
        roll = make_roll(roll_name=roll_name, status="failed")
        assert make_user().casino_score([roll]) == expected_decrease

    # ── One Hell of a Day: decrease is 0 (special case) ──────────────────────

    def test_one_hell_of_a_day_failed_no_penalty(self):
        roll = make_roll(roll_name="One Hell of a Day", status="failed")
        assert make_user().casino_score([roll]) == 0

    # ── Game Theory: symmetric penalty ───────────────────────────────────────

    def test_game_theory_won_and_failed_cancel(self):
        won = make_roll(roll_name="Game Theory", status="won")
        lost = make_roll(roll_name="Game Theory", status="failed")
        assert make_user().casino_score([won, lost]) == 0

    # ── relative rolls (tier-based) ───────────────────────────────────────────

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_winner_takes_all_won_equals_relative(self, tier):
        roll = make_roll(roll_name="Winner Takes All", status="won", tier_num=tier)
        assert make_user().casino_score([roll]) == relative(tier)

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_winner_takes_all_failed_equals_negative_relative(self, tier):
        roll = make_roll(roll_name="Winner Takes All", status="failed", tier_num=tier)
        assert make_user().casino_score([roll]) == int(-1 * relative(tier))

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_destiny_alignment_won_equals_relative(self, tier):
        roll = make_roll(roll_name="Destiny Alignment", status="won", tier_num=tier)
        assert make_user().casino_score([roll]) == relative(tier)

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_destiny_alignment_failed_is_one_third_penalty(self, tier):
        roll = make_roll(roll_name="Destiny Alignment", status="failed", tier_num=tier)
        assert make_user().casino_score([roll]) == int(-1 * relative(tier) / 3)

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_soul_mates_won_equals_relative(self, tier):
        roll = make_roll(roll_name="Soul Mates", status="won", tier_num=tier)
        assert make_user().casino_score([roll]) == relative(tier)

    @pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
    def test_soul_mates_failed_is_half_penalty(self, tier):
        roll = make_roll(roll_name="Soul Mates", status="failed", tier_num=tier)
        assert make_user().casino_score([roll]) == int(-1 * relative(tier) / 2)

    # ── multiple rolls accumulate correctly ───────────────────────────────────

    def test_multiple_won_rolls_sum(self):
        r1 = make_roll(roll_name="One Hell of a Day", status="won")    # +1
        r2 = make_roll(roll_name="One Hell of a Week", status="won")   # +7
        assert make_user().casino_score([r1, r2]) == 8

    def test_multiple_failed_rolls_sum(self):
        r1 = make_roll(roll_name="One Hell of a Week", status="failed")   # -2
        r2 = make_roll(roll_name="One Hell of a Month", status="failed")  # -5
        assert make_user().casino_score([r1, r2]) == -7

    def test_mixed_won_failed_current_accumulates(self):
        won = make_roll(roll_name="One Hell of a Month", status="won")     # +18
        failed = make_roll(roll_name="One Hell of a Month", status="failed")  # -5
        current = make_roll(roll_name="One Hell of a Month", status="current")  # 0
        assert make_user().casino_score([won, failed, current]) == 13

    def test_only_won_and_failed_contribute_not_others(self):
        won = make_roll(roll_name="Let Fate Decide", status="won")       # +8
        pending = make_roll(roll_name="Let Fate Decide", status="pending")
        waiting = make_roll(roll_name="Let Fate Decide", status="waiting")
        removed = make_roll(roll_name="Let Fate Decide", status="removed")
        assert make_user().casino_score([won, pending, waiting, removed]) == 8
