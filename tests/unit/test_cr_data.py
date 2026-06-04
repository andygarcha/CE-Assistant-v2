from Classes.CE_Objective import CEObjective
from Classes.CE_User_Game import CEUserGame
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
GAME_ID_D = "game-ddd-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _po(points: int, game_id: str = GAME_ID_A) -> CEObjective:
    return make_objective(
        ce_id=OBJ_ID, point_value=points, obj_type="Primary", game_ce_id=game_id
    )


def _completed_ug(game_id: str, points: int) -> CEUserGame:
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
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[])
        assert cr.total_cr == 0

    def test_zero_point_game_contributes_nothing(self):
        game = make_game(ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(0)])
        ug = _completed_ug(GAME_ID_A, 0)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 0
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

    def test_category_cr_is_order_independent(self):
        # Per-category CR sorts its games list, so input order in owned_games
        # does not affect the result.
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
        assert cr_desc.action_cr == cr_asc.action_cr

    def test_higher_value_game_sorted_first(self):
        # The higher-value game always occupies position 0 (multiplier 1.0),
        # giving a higher total than the reverse. Explicitly verify the math.
        # calculate_cr([100, 10]) = 100 + 0.9*10 = 109
        game_a = make_game(
            ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(100, GAME_ID_A)]
        )
        game_b = make_game(
            ce_id=GAME_ID_B, categories=["Action"], objectives=[_po(10, GAME_ID_B)]
        )
        ug_a = _completed_ug(GAME_ID_A, 100)
        ug_b = _completed_ug(GAME_ID_B, 10)
        cr = CRData(owned_games=[ug_a, ug_b], database_name=[game_a, game_b])
        assert cr.action_cr == 109.0

    def test_points_cap_at_1000(self):
        # A game worth 1500 points can only contribute 1000 to CR.
        game = make_game(ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(1500)])
        ug = _completed_ug(GAME_ID_A, 1500)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 1000.0
        assert cr.total_cr == 1000.0

    def test_points_exactly_at_cap(self):
        game = make_game(ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(1000)])
        ug = _completed_ug(GAME_ID_A, 1000)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 1000.0


# ── dual-category behaviour ───────────────────────────────────────────────────


class TestCRDataDualCategory:
    def test_dual_category_game_counted_in_both_categories(self):
        # A dual-cat game appears in both category CRs.
        game = make_game(
            ce_id=GAME_ID_A, categories=["Action", "Strategy"], objectives=[_po(100)]
        )
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.action_cr == 100.0
        assert cr.strategy_cr == 100.0

    def test_dual_category_total_counts_once(self):
        # Total CR uses max-per-game, so a dual-cat game contributes only once
        # (not once per category).
        game = make_game(
            ce_id=GAME_ID_A, categories=["Action", "Strategy"], objectives=[_po(100)]
        )
        ug = _completed_ug(GAME_ID_A, 100)
        cr = CRData(owned_games=[ug], database_name=[game])
        assert cr.total_cr == 100.0

    def test_dual_category_advances_both_power_counters(self):
        # A dual-cat game at 200pts advances BOTH Action and Strategy power
        # counters, so subsequent games in either category use multiplier 0.9.
        #
        # Processing order (DESC): A(200, dual), B(100, Action), C(100, Strategy)
        # total_cr:
        #   A → Action power 0→1, Strategy power 0→1, max=200  → total=200
        #   B → Action power 1, contrib=90                      → total=290
        #   C → Strategy power 1, contrib=90                    → total=380
        game_a = make_game(
            ce_id=GAME_ID_A,
            categories=["Action", "Strategy"],
            objectives=[_po(200, GAME_ID_A)],
        )
        game_b = make_game(
            ce_id=GAME_ID_B, categories=["Action"], objectives=[_po(100, GAME_ID_B)]
        )
        game_c = make_game(
            ce_id=GAME_ID_C, categories=["Strategy"], objectives=[_po(100, GAME_ID_C)]
        )
        cr = CRData(
            owned_games=[
                _completed_ug(GAME_ID_A, 200),
                _completed_ug(GAME_ID_B, 100),
                _completed_ug(GAME_ID_C, 100),
            ],
            database_name=[game_a, game_b, game_c],
        )
        assert cr.total_cr == 380.0
        # per-category still counts the dual-cat game in both
        assert cr.action_cr == 200 + 0.9 * 100  # 290
        assert cr.strategy_cr == 200 + 0.9 * 100  # 290

    def test_dual_category_picks_best_contribution(self):
        # With two Action games already ahead of it, the dual-cat game's
        # Action multiplier (0.9^2=0.81) is lower than its Strategy multiplier
        # (0.9^0=1.0), so Strategy wins.
        #
        # Processing order: A(200,Action), B(200,Action), C(100,dual)
        # total_cr:
        #   A → Action 0→1, contrib=200   → total=200
        #   B → Action 1→2, contrib=180   → total=380
        #   C → Action power=2 (81), Strategy power=0 (100), max=Strategy(100)
        #         Action 2→3, Strategy 0→1
        #                                 → total=480
        game_a = make_game(
            ce_id=GAME_ID_A, categories=["Action"], objectives=[_po(200, GAME_ID_A)]
        )
        game_b = make_game(
            ce_id=GAME_ID_B, categories=["Action"], objectives=[_po(200, GAME_ID_B)]
        )
        game_c = make_game(
            ce_id=GAME_ID_C,
            categories=["Action", "Strategy"],
            objectives=[_po(100, GAME_ID_C)],
        )
        cr = CRData(
            owned_games=[
                _completed_ug(GAME_ID_A, 200),
                _completed_ug(GAME_ID_B, 200),
                _completed_ug(GAME_ID_C, 100),
            ],
            database_name=[game_a, game_b, game_c],
        )
        assert cr.total_cr == 480.0

    def test_two_dual_category_games_same_categories(self):
        # Two dual-cat [Action, Strategy] games.
        # Processing order: A(200), B(100)
        # total_cr:
        #   A → Action 0→1 (200), Strategy 0→1 (200), max=200   → total=200
        #   B → Action 1→2 (90),  Strategy 1→2 (90),  max=90    → total=290
        game_a = make_game(
            ce_id=GAME_ID_A,
            categories=["Action", "Strategy"],
            objectives=[_po(200, GAME_ID_A)],
        )
        game_b = make_game(
            ce_id=GAME_ID_B,
            categories=["Action", "Strategy"],
            objectives=[_po(100, GAME_ID_B)],
        )
        cr = CRData(
            owned_games=[
                _completed_ug(GAME_ID_A, 200),
                _completed_ug(GAME_ID_B, 100),
            ],
            database_name=[game_a, game_b],
        )
        assert cr.total_cr == 290.0
        # per-category: both games in both lists
        assert cr.action_cr == 200 + 0.9 * 100  # 290
        assert cr.strategy_cr == 200 + 0.9 * 100  # 290

    def test_total_cr_is_not_sum_of_category_crs(self):
        # With dual-cat games, total_cr < sum of all category CRs because
        # each game only contributes its max once to total.
        game_a = make_game(
            ce_id=GAME_ID_A,
            categories=["Action", "Strategy"],
            objectives=[_po(200, GAME_ID_A)],
        )
        game_b = make_game(
            ce_id=GAME_ID_B,
            categories=["Action", "Strategy"],
            objectives=[_po(100, GAME_ID_B)],
        )
        cr = CRData(
            owned_games=[
                _completed_ug(GAME_ID_A, 200),
                _completed_ug(GAME_ID_B, 100),
            ],
            database_name=[game_a, game_b],
        )
        category_sum = cr.action_cr + cr.strategy_cr  # 580
        assert cr.total_cr < category_sum
        assert cr.total_cr == 290.0
