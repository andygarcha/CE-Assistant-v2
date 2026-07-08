from Classes.CE_Objective import CEObjective
from Classes.CE_User_Objective import CEUserObjective
from tests.conftest import (
    make_game,
    make_objective,
    make_user_game,
    make_user_objective,
)

GAME_ID = "game-001-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


def _po(points: int, obj_id: str = OBJ_ID) -> CEObjective:
    """Game primary objective with given points."""
    return make_objective(
        ce_id=obj_id, point_value=points, obj_type="Primary", game_ce_id=GAME_ID
    )


def _uncleared_po(obj_id: str = "obj-uncleared-000000000000") -> CEObjective:
    """Uncleared primary objective (0 points)."""
    return make_objective(
        ce_id=obj_id,
        point_value=0,
        obj_type="Primary",
        name="PO (UNCLEARED)",
        game_ce_id=GAME_ID,
    )


def _upo(points: int, obj_id: str = OBJ_ID) -> CEUserObjective:
    """User primary objective with given points."""
    return make_user_objective(
        ce_id=obj_id, game_ce_id=GAME_ID, obj_type="Primary", user_points=points
    )


def _so(points: int, obj_id: str) -> CEObjective:
    """Game secondary objective with given points."""
    return make_objective(
        ce_id=obj_id, point_value=points, obj_type="Secondary", game_ce_id=GAME_ID
    )


def _uso(points: int, obj_id: str) -> CEUserObjective:
    """User secondary objective with given points."""
    return make_user_objective(
        ce_id=obj_id, game_ce_id=GAME_ID, obj_type="Secondary", user_points=points
    )


# ── user_points ───────────────────────────────────────────────────────────


class TestGetUserPoints:
    def test_sums_all_user_objectives(self):
        ug = make_user_game(
            user_objectives=[
                make_user_objective(user_points=10),
                make_user_objective(
                    ce_id="obj-0002-0000-0000-000000000000", user_points=20
                ),
            ]
        )
        assert ug.user_points == 30

    def test_empty_objectives_zero_points(self):
        assert make_user_game(user_objectives=[]).user_points == 0

    def test_single_objective(self):
        assert (
            make_user_game(
                user_objectives=[make_user_objective(user_points=15)]
            ).user_points
            == 15
        )


# ── has_completed_objective ───────────────────────────────────────────────────


class TestHasCompletedObjective:
    def test_found_by_id_and_points(self):
        ug = make_user_game(user_objectives=[_upo(10)])
        assert ug.has_completed_objective(OBJ_ID, 10) is True

    def test_wrong_points_returns_false(self):
        ug = make_user_game(user_objectives=[_upo(10)])
        assert ug.has_completed_objective(OBJ_ID, 5) is False

    def test_wrong_id_returns_false(self):
        ug = make_user_game(user_objectives=[_upo(10)])
        assert ug.has_completed_objective("wrong-id", 10) is False

    def test_empty_objectives_returns_false(self):
        assert (
            make_user_game(user_objectives=[]).has_completed_objective(OBJ_ID, 10)
            is False
        )


# ── is_completed ──────────────────────────────────────────────────────────────


class TestIsCompleted:
    def test_completed_game_direct_cegame(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed(game) is True

    def test_completed_game_via_database_list(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed([game]) is True

    def test_no_user_pos_not_completed(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[])
        assert ug.is_completed(game) is False

    def test_user_po_count_mismatch_not_completed(self):
        # game has 2 POs, user has 1
        game = make_game(
            ce_id=GAME_ID,
            objectives=[
                _po(10, "obj-a"),
                _po(20, "obj-b"),
            ],
        )
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "obj-a")])
        assert ug.is_completed(game) is False

    def test_wrong_user_points_not_completed(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(5)])
        assert ug.is_completed(game) is False

    def test_game_not_in_database_list_returns_false(self):
        other_game = make_game(
            ce_id="other-00-0000-0000-000000000000", objectives=[_po(10)]
        )
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed([other_game]) is False

    def test_completed_with_uncleared_po_included(self):
        # Game has 1 normal PO + 1 uncleared PO; user mirrors both
        obj_id2 = "obj-0002-0000-0000-000000000000"
        game = make_game(ce_id=GAME_ID, objectives=[_po(10), _uncleared_po(obj_id2)])
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[
                _upo(10),
                make_user_objective(
                    ce_id=obj_id2, game_ce_id=GAME_ID, obj_type="Primary", user_points=0
                ),
            ],
        )
        assert ug.is_completed(game) is True

    def test_secondary_objectives_do_not_count(self):
        # Only POs should count; adding a SO shouldn't affect completion
        game = make_game(
            ce_id=GAME_ID,
            objectives=[
                _po(10),
                make_objective(
                    ce_id="obj-so",
                    point_value=50,
                    obj_type="Secondary",
                    game_ce_id=GAME_ID,
                ),
            ],
        )
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed(game) is True

    def test_completed_via_mapping(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed({GAME_ID: game}) is True

    def test_game_not_in_mapping_returns_false(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10)])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10)])
        assert ug.is_completed({"wrong-id-0000-0000-000000000000": game}) is False


# ── is_overcompleted ─────────────────────────────────────────────────────────
#
# Overcompletion = all POs completed AND all SOs completed.
# Tests mirror is_completed's structure and then add SO-specific cases.


class TestIsOvercompleted:
    # ── true cases ────────────────────────────────────────────────────────────

    def test_all_pos_and_all_sos_completed(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID, user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")]
        )
        assert ug.is_overcompleted(game) is True

    def test_multiple_pos_and_sos_all_completed(self):
        game = make_game(
            ce_id=GAME_ID,
            objectives=[
                _po(10, "po-a"),
                _po(20, "po-b"),
                _so(30, "so-a"),
                _so(40, "so-b"),
            ],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[
                _upo(10, "po-a"),
                _upo(20, "po-b"),
                _uso(30, "so-a"),
                _uso(40, "so-b"),
            ],
        )
        assert ug.is_overcompleted(game) is True

    def test_all_pos_completed_no_sos_in_game(self):
        """A game with no SOs is overcompleted once all POs are done."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted(game) is False

    def test_overcompleted_via_database_list(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID, user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")]
        )
        assert ug.is_overcompleted([game]) is True

    def test_overcompleted_via_mapping(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID, user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")]
        )
        assert ug.is_overcompleted({GAME_ID: game}) is True

    def test_game_not_in_mapping_returns_false(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID, user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")]
        )
        assert ug.is_overcompleted({"wrong-id-0000-0000-000000000000": game}) is False

    # ── user-supplied starter cases ───────────────────────────────────────────

    def test_all_sos_but_no_pos(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_uso(20, "so-a")])
        assert ug.is_overcompleted(game) is False

    def test_all_sos_and_all_but_one_po(self):
        game = make_game(
            ce_id=GAME_ID,
            objectives=[_po(10, "po-a"), _po(20, "po-b"), _so(30, "so-a")],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[_upo(10, "po-a"), _uso(30, "so-a")],  # po-b missing
        )
        assert ug.is_overcompleted(game) is False

    def test_partial_pos_and_partial_sos(self):
        """2/4 SOs and 2/4 POs done → not overcompleted."""
        game = make_game(
            ce_id=GAME_ID,
            objectives=[
                _po(10, "po-a"),
                _po(20, "po-b"),
                _po(30, "po-c"),
                _po(40, "po-d"),
                _so(10, "so-a"),
                _so(20, "so-b"),
                _so(30, "so-c"),
                _so(40, "so-d"),
            ],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[
                _upo(10, "po-a"),
                _upo(20, "po-b"),
                _uso(10, "so-a"),
                _uso(20, "so-b"),
            ],
        )
        assert ug.is_overcompleted(game) is False

    def test_all_but_one_so_and_all_pos(self):
        game = make_game(
            ce_id=GAME_ID,
            objectives=[_po(10, "po-a"), _so(20, "so-a"), _so(30, "so-b")],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")],  # so-b missing
        )
        assert ug.is_overcompleted(game) is False

    # ── additional edge cases ─────────────────────────────────────────────────

    def test_all_pos_but_game_has_sos_user_has_none(self):
        """Completing all POs is not enough when SOs exist but are untouched."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(50, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted(game) is False

    def test_all_pos_and_partial_so_points(self):
        """Full POs + partial SO points (e.g. 25 of 50) → not overcompleted."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(50, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[_upo(10, "po-a"), _uso(25, "so-a")],
        )
        assert ug.is_overcompleted(game) is False

    def test_nothing_completed(self):
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[])
        assert ug.is_overcompleted(game) is False

    def test_game_not_in_database_list_returns_false(self):
        other = make_game(
            ce_id="other-00-0000-0000-000000000000", objectives=[_po(10, "po-a")]
        )
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted([other]) is False

    def test_wrong_so_points_not_overcompleted(self):
        """SO exists, user has it but with wrong point total → not overcompleted."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(50, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[_upo(10, "po-a"), _uso(40, "so-a")],
        )
        assert ug.is_overcompleted(game) is False

    def test_overcompleted_with_uncleared_po(self):
        """Uncleared PO (0 pts) + normal PO + all SOs → still overcompleted."""
        unc_id = "obj-uncleared-000000000000"
        game = make_game(
            ce_id=GAME_ID,
            objectives=[_po(10, "po-a"), _uncleared_po(unc_id), _so(20, "so-a")],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[
                _upo(10, "po-a"),
                make_user_objective(
                    ce_id=unc_id, game_ce_id=GAME_ID, obj_type="Primary", user_points=0
                ),
                _uso(20, "so-a"),
            ],
        )
        assert ug.is_overcompleted(game) is True

    def test_community_objectives_do_not_affect_overcompletion(self):
        """Community objectives are irrelevant — only POs and SOs matter."""
        game = make_game(
            ce_id=GAME_ID,
            objectives=[
                _po(10, "po-a"),
                _so(20, "so-a"),
                make_objective(
                    ce_id="co-a",
                    point_value=100,
                    obj_type="Community",
                    game_ce_id=GAME_ID,
                ),
            ],
        )
        ug = make_user_game(
            ce_id=GAME_ID,
            user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")],
        )
        assert ug.is_overcompleted(game) is True

    def test_completed_not_enough_for_overcompletion(self):
        """A completed game (all POs done) with an uncompleted SO is not overcompleted."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(50, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_completed(game) is True
        assert ug.is_overcompleted(game) is False

    # ── dispatch-discriminating tests ─────────────────────────────────────────
    #
    # These tests are structured so that calling the wrong internal helper
    # (e.g. __is_completed_helper instead of __is_overcompleted_helper) would
    # produce the wrong answer. The existing happy-path dispatch tests above
    # pass even with the wrong helper because the user has both POs and SOs
    # fully done — a state that satisfies both helpers.

    def test_pos_done_sos_missing_via_list_returns_false(self):
        """All POs done but SOs untouched, passed as list → False.
        Wrong helper (__is_completed_helper) would return True here."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted([game]) is False

    def test_pos_done_sos_missing_via_mapping_returns_false(self):
        """Same scenario via mapping."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted({GAME_ID: game}) is False

    def test_zero_pos_all_sos_is_overcompleted_direct(self):
        """Game with no POs: all SOs done → overcompleted.
        Wrong helper (without ignore_zero_pos=True) sees no user POs and returns False."""
        game = make_game(ce_id=GAME_ID, objectives=[_so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_uso(20, "so-a")])
        assert ug.is_overcompleted(game) is True

    def test_zero_pos_all_sos_is_overcompleted_via_list(self):
        """Same 0-PO scenario via list — the branch where the dispatch bug lived."""
        game = make_game(ce_id=GAME_ID, objectives=[_so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_uso(20, "so-a")])
        assert ug.is_overcompleted([game]) is True

    def test_zero_pos_all_sos_is_overcompleted_via_mapping(self):
        """Same 0-PO scenario via mapping."""
        game = make_game(ce_id=GAME_ID, objectives=[_so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_uso(20, "so-a")])
        assert ug.is_overcompleted({GAME_ID: game}) is True

    def test_all_dispatch_paths_agree_when_overcompleted(self):
        """CEGame, list, and mapping branches must all return True for the same state."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(
            ce_id=GAME_ID, user_objectives=[_upo(10, "po-a"), _uso(20, "so-a")]
        )
        assert ug.is_overcompleted(game) is True
        assert ug.is_overcompleted([game]) is True
        assert ug.is_overcompleted({GAME_ID: game}) is True

    def test_all_dispatch_paths_agree_when_sos_incomplete(self):
        """CEGame, list, and mapping branches must all return False when SOs are unfinished."""
        game = make_game(ce_id=GAME_ID, objectives=[_po(10, "po-a"), _so(20, "so-a")])
        ug = make_user_game(ce_id=GAME_ID, user_objectives=[_upo(10, "po-a")])
        assert ug.is_overcompleted(game) is False
        assert ug.is_overcompleted([game]) is False
        assert ug.is_overcompleted({GAME_ID: game}) is False


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEUserGameToDict:
    def test_returns_dict(self):
        assert isinstance(make_user_game().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_user_game().to_dict()
        for key in ("name", "ce_id", "objectives"):
            assert key in result
