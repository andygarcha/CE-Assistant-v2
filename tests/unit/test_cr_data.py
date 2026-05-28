from Classes.OtherClasses import CRData
from tests.conftest import (
    make_game,
    make_objective,
    make_user_game,
    make_user_objective,
)

GAME_ID_A = "game-aaa-0000-0000-000000000000"
GAME_ID_B = "game-bbb-0000-0000-000000000000"
GAME_ID_C = "game-ccc-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _po(points: int, game_id: str = GAME_ID_A) -> object:
    return make_objective(
        ce_id=OBJ_ID, point_value=points, obj_type="Primary", game_ce_id=game_id
    )


def _completed_ug(game_id: str, points: int) -> object:
    """User game whose single PO gives the user `points` points."""
    uobj = make_user_objective(ce_id=OBJ_ID, game_ce_id=game_id, user_points=points)
    return make_user_game(ce_id=game_id, user_objectives=[uobj])


# ── zero-game baseline ────────────────────────────────────────────────────────


class TestCRDataEmpty:
    def test_all_category_crs_zero(self):
        cr = CRData(owned_games=[], database_name=[])
        for attr in (
            "action_cr",
            "arcade_cr",
            "bullethell_cr",
            "firstperson_cr",
            "platformer_cr",
            "strategy_cr",
        ):
            assert getattr(cr, attr) == 0

    def test_total_cr_zero(self):
        assert CRData(owned_games=[], database_name=[]).total_cr == 0


# ── single-game allocation ────────────────────────────────────────────────────


class TestCRDataSingleGame:
    def test_action_game_goes_to_action_cr(self):
        game = make_game(ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(100)])
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 100.0

    def test_action_game_does_not_affect_other_categories(self):
        game = make_game(ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(100)])
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.arcade_cr == 0
        assert cr.strategy_cr == 0

    def test_total_cr_matches_single_category(self):
        game = make_game(ce_id=GAME_ID_A, categories=["Strategy"], objectives=[_po(50)])
        ug = _completed_ug(GAME_ID_A, 50)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.total_cr == cr.strategy_cr

    def test_game_not_in_database_skipped(self):
        # owned_games references GAME_ID_A, but database_name is empty
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[])
        assert cr.total_cr == 0


# ── multiplier and ordering ───────────────────────────────────────────────────


class TestCRDataMultiplier:
    def test_two_action_games_use_multiplier(self):
        # calculate_cr([100, 100]) = 100 + 0.9*100 = 190
        game_a = make_game(
            ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(100, GAME_ID_A)]
        )
        game_b = make_game(
            ce_id=GAME_ID_B, categories=["Action"], objectives=[_po(100, GAME_ID_B)]
        )
        ug_a = _completed_ug(GAME_ID_A, 100)
        ug_b = _completed_ug(GAME_ID_B, 100)
        cr = CRData(owned_games=[ug_a, ug_b], database_name=[game_a, game_b])
        assert cr.action_cr == 190.0

    def test_order_in_owned_games_affects_cr(self):
        # Putting the higher-value game first gives a higher CR.
        game_a = make_game(
            ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(100, GAME_ID_A)]
        )
        game_b = make_game(
            ce_id=GAME_ID_B, categories=["Action"], objectives=[_po(10, GAME_ID_B)]
        )
        ug_a = _completed_ug(GAME_ID_A, 100)
        ug_b = _completed_ug(GAME_ID_B, 10)
        cr_desc = CRData(owned_games=[ug_a, ug_b], database_name=[game_a, game_b])
        cr_asc = CRData(owned_games=[ug_b, ug_a], database_name=[game_a, game_b])
        assert cr_desc.action_cr > cr_asc.action_cr


# ── dual-category double-counting ─────────────────────────────────────────────


class TestCRDataDualCategory:
    def test_dual_category_game_counted_in_both(self):
        # A game with ["Action", "Strategy"] and 100 user points:
        # action_cr = calculate_cr([100]) = 100
        # strategy_cr = calculate_cr([100]) = 100
        game = make_game(
            ce_id=GAME_ID_A, categories=["Action", "Strategy"], objectives=[_po(100)]
        )
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 100.0
        assert cr.strategy_cr == 100.0

    def test_dual_category_total_double_counts(self):
        # Because each category is summed independently, a dual-category game
        # contributes to the total CR twice.
        game = make_game(
            ce_id=GAME_ID_A, categories=["Action", "Strategy"], objectives=[_po(100)]
        )
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.total_cr == 200.0
