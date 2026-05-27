import datetime
import pytest

from tests.conftest import make_game, make_objective, make_roll, make_user, make_user_game, make_user_objective

GAME_ID_A = "game-aaa-0000-0000-000000000000"
GAME_ID_B = "game-bbb-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"

_PAST = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)


def _db_game(game_id: str, points: int = 100):
    obj = make_objective(ce_id=OBJ_ID, point_value=points, obj_type="Primary", game_ce_id=game_id)
    return make_game(ce_id=game_id, objectives=[obj])


def _completed_user(game_id: str, points: int = 100):
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=game_id, user_points=points)
    ug = make_user_game(ce_id=game_id, user_objectives=[uobj])
    return make_user(owned_games=[ug])


def _incomplete_user(game_id: str):
    ug = make_user_game(ce_id=game_id, user_objectives=[])
    return make_user(owned_games=[ug])


# ── is_won: solo rolls ────────────────────────────────────────────────────────


class TestIsWonSolo:
    def test_completed_game_wins(self):
        game = _db_game(GAME_ID_A)
        user = _completed_user(GAME_ID_A)
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID_A])
        assert roll.is_won([game], user) is True

    def test_incomplete_game_does_not_win(self):
        game = _db_game(GAME_ID_A)
        user = _incomplete_user(GAME_ID_A)
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID_A])
        assert roll.is_won([game], user) is False

    def test_expired_roll_does_not_win(self):
        game = _db_game(GAME_ID_A)
        user = _completed_user(GAME_ID_A)
        roll = make_roll(roll_name="One Hell of a Day", games=[GAME_ID_A], due_time=_PAST)
        assert roll.is_won([game], user) is False

    def test_multi_game_roll_all_completed_wins(self):
        game_a = _db_game(GAME_ID_A)
        game_b = _db_game(GAME_ID_B)
        uobj_a = make_user_objective(ce_id=OBJ_ID, game_ce_id=GAME_ID_A, user_points=100)
        uobj_b = make_user_objective(ce_id=OBJ_ID, game_ce_id=GAME_ID_B, user_points=100)
        ug_a = make_user_game(ce_id=GAME_ID_A, user_objectives=[uobj_a])
        ug_b = make_user_game(ce_id=GAME_ID_B, user_objectives=[uobj_b])
        user = make_user(owned_games=[ug_a, ug_b])
        roll = make_roll(roll_name="One Hell of a Week", games=[GAME_ID_A, GAME_ID_B])
        assert roll.is_won([game_a, game_b], user) is True

    def test_multi_game_roll_one_incomplete_loses(self):
        game_a = _db_game(GAME_ID_A)
        game_b = _db_game(GAME_ID_B)
        uobj_a = make_user_objective(ce_id=OBJ_ID, game_ce_id=GAME_ID_A, user_points=100)
        ug_a = make_user_game(ce_id=GAME_ID_A, user_objectives=[uobj_a])
        ug_b = make_user_game(ce_id=GAME_ID_B, user_objectives=[])
        user = make_user(owned_games=[ug_a, ug_b])
        roll = make_roll(roll_name="One Hell of a Week", games=[GAME_ID_A, GAME_ID_B])
        assert roll.is_won([game_a, game_b], user) is False


# ── is_won: co-op rolls ───────────────────────────────────────────────────────


class TestIsWonCoop:
    def test_destiny_alignment_both_done_wins(self):
        game_a = _db_game(GAME_ID_A)
        game_b = _db_game(GAME_ID_B)
        user = _completed_user(GAME_ID_A)
        partner = _completed_user(GAME_ID_B)
        roll = make_roll(roll_name="Destiny Alignment", games=[GAME_ID_A, GAME_ID_B])
        assert roll.is_won([game_a, game_b], user, partner) is True

    def test_destiny_alignment_only_user_done_loses(self):
        game_a = _db_game(GAME_ID_A)
        game_b = _db_game(GAME_ID_B)
        user = _completed_user(GAME_ID_A)
        partner = _incomplete_user(GAME_ID_B)
        roll = make_roll(roll_name="Destiny Alignment", games=[GAME_ID_A, GAME_ID_B])
        assert roll.is_won([game_a, game_b], user, partner) is False

    def test_soul_mates_both_done_wins(self):
        game = _db_game(GAME_ID_A)
        user = _completed_user(GAME_ID_A)
        partner = _completed_user(GAME_ID_A)
        roll = make_roll(roll_name="Soul Mates", games=[GAME_ID_A])
        assert roll.is_won([game], user, partner) is True

    def test_soul_mates_only_user_done_loses(self):
        game = _db_game(GAME_ID_A)
        user = _completed_user(GAME_ID_A)
        partner = _incomplete_user(GAME_ID_A)
        roll = make_roll(roll_name="Soul Mates", games=[GAME_ID_A])
        assert roll.is_won([game], user, partner) is False

    def test_winner_takes_all_user_wins(self):
        game = _db_game(GAME_ID_A)
        user = _completed_user(GAME_ID_A)
        partner = _incomplete_user(GAME_ID_A)
        roll = make_roll(roll_name="Winner Takes All", games=[GAME_ID_A])
        assert roll.is_won([game], user, partner) is True

    def test_winner_takes_all_partner_wins(self):
        game = _db_game(GAME_ID_A)
        user = _incomplete_user(GAME_ID_A)
        partner = _completed_user(GAME_ID_A)
        roll = make_roll(roll_name="Winner Takes All", games=[GAME_ID_A])
        assert roll.is_won([game], user, partner) is True

    def test_winner_takes_all_neither_done_loses(self):
        game = _db_game(GAME_ID_A)
        user = _incomplete_user(GAME_ID_A)
        partner = _incomplete_user(GAME_ID_A)
        roll = make_roll(roll_name="Winner Takes All", games=[GAME_ID_A])
        assert roll.is_won([game], user, partner) is False


# ── casino_increase ───────────────────────────────────────────────────────────


class TestCasinoIncrease:
    @pytest.mark.parametrize("roll_name, expected", [
        ("One Hell of a Day",            1),
        ("One Hell of a Week",           7),
        ("One Hell of a Month",         18),
        ("Never Lucky",                  4),
        ("Triple Threat",               15),
        ("Fourward Thinking",           18),
        ("Teamwork Makes the Dream Work", 10),
        ("Game Theory",                  4),
    ])
    def test_fixed_rolls(self, roll_name, expected):
        assert make_roll(roll_name=roll_name).casino_increase() == expected

    @pytest.mark.parametrize("points, expected", [
        (10,  1),   # T1
        (20,  2),   # T2
        (50,  4),   # T3
        (100, 8),   # T4
        (200, 20),  # T5+
    ])
    def test_destiny_alignment_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Destiny Alignment", games=[GAME_ID_A])
        assert roll.casino_increase([game]) == expected

    @pytest.mark.parametrize("points, expected", [
        (10,  1),
        (100, 8),
        (200, 20),
    ])
    def test_soul_mates_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Soul Mates", games=[GAME_ID_A])
        assert roll.casino_increase([game]) == expected

    @pytest.mark.parametrize("points, expected", [
        (10,  1),
        (100, 8),
        (200, 20),
    ])
    def test_winner_takes_all_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Winner Takes All", games=[GAME_ID_A])
        assert roll.casino_increase([game]) == expected


# ── casino_decrease ───────────────────────────────────────────────────────────


class TestCasinoDecrease:
    @pytest.mark.parametrize("roll_name, expected", [
        ("One Hell of a Day",            0),
        ("One Hell of a Week",          -2),
        ("One Hell of a Month",         -5),
        ("Never Lucky",                 -1),
        ("Triple Threat",               -3),
        ("Game Theory",                 -4),
        ("Teamwork Makes the Dream Work", -2),
    ])
    def test_fixed_rolls(self, roll_name, expected):
        assert make_roll(roll_name=roll_name).casino_decrease() == expected

    @pytest.mark.parametrize("points, expected", [
        (10,   0),   # T1: int(-1 * 1 / 3) = 0
        (50,  -1),   # T3: int(-1 * 4 / 3) = -1
        (100, -2),   # T4: int(-1 * 8 / 3) = -2
        (200, -6),   # T5+: int(-1 * 20 / 3) = -6
    ])
    def test_destiny_alignment_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Destiny Alignment", games=[GAME_ID_A])
        assert roll.casino_decrease([game]) == expected

    @pytest.mark.parametrize("points, expected", [
        (10,   0),   # T1: int(-1 * 1 / 2) = 0
        (50,  -2),   # T3: int(-1 * 4 / 2) = -2
        (100, -4),   # T4: int(-1 * 8 / 2) = -4
        (200, -10),  # T5+: int(-1 * 20 / 2) = -10
    ])
    def test_soul_mates_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Soul Mates", games=[GAME_ID_A])
        assert roll.casino_decrease([game]) == expected

    @pytest.mark.parametrize("points, expected", [
        (10,   -1),   # T1: int(-1 * 1) = -1
        (50,   -4),   # T3: int(-1 * 4) = -4
        (100,  -8),   # T4: int(-1 * 8) = -8
        (200, -20),   # T5+: int(-1 * 20) = -20
    ])
    def test_winner_takes_all_relative_tiers(self, points, expected):
        game = _db_game(GAME_ID_A, points)
        roll = make_roll(roll_name="Winner Takes All", games=[GAME_ID_A])
        assert roll.casino_decrease([game]) == expected
