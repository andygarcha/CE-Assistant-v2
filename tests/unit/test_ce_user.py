import pytest

from Classes.CE_User import MUTELIST_CEIDS
from tests.conftest import make_game, make_objective, make_user, make_user_game, make_user_objective

GAME_ID_A = "game-aaa-0000-0000-000000000000"
GAME_ID_B = "game-bbb-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _user_game(ce_id: str, points: int) -> object:
    """User game whose single primary objective gives `points` user points."""
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=ce_id, user_points=points)
    return make_user_game(ce_id=ce_id, user_objectives=[uobj])


# ── rank_num ──────────────────────────────────────────────────────────────────


class TestRankNum:
    @pytest.mark.parametrize("total_points, expected_rank", [
        (0,     0),   # E
        (49,    0),   # E (just below D threshold)
        (50,    1),   # D
        (249,   1),   # D
        (250,   2),   # C
        (499,   2),   # C
        (500,   3),   # B
        (999,   3),   # B
        (1000,  4),   # A
        (2499,  4),   # A
        (2500,  5),   # S
        (4999,  5),   # S
        (5000,  6),   # SS
        (7499,  6),   # SS
        (7500,  7),   # SSS
        (9999,  7),   # SSS
        (10000, 8),   # EX
        (99999, 8),   # EX (no upper bound)
    ])
    def test_rank_boundaries(self, total_points, expected_rank):
        user = make_user(owned_games=[_user_game(GAME_ID_A, total_points)])
        assert user.rank_num() == expected_rank


# ── get_rank ──────────────────────────────────────────────────────────────────


class TestGetRank:
    @pytest.mark.parametrize("points, expected_str", [
        (0,     "E Rank"),
        (50,    "D Rank"),
        (250,   "C Rank"),
        (500,   "B Rank"),
        (1000,  "A Rank"),
        (2500,  "S Rank"),
        (5000,  "SS Rank"),
        (7500,  "SSS Rank"),
        (10000, "EX Rank"),
    ])
    def test_rank_strings(self, points, expected_str):
        user = make_user(owned_games=[_user_game(GAME_ID_A, points)])
        assert user.get_rank() == expected_str


# ── get_total_points ──────────────────────────────────────────────────────────


class TestGetTotalPoints:
    def test_sums_across_games(self):
        user = make_user(owned_games=[
            _user_game(GAME_ID_A, 100),
            _user_game(GAME_ID_B, 200),
        ])
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
