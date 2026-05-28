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


# ── get_user_points ───────────────────────────────────────────────────────────


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
        assert ug.get_user_points() == 30

    def test_empty_objectives_zero_points(self):
        assert make_user_game(user_objectives=[]).get_user_points() == 0

    def test_single_objective(self):
        assert (
            make_user_game(
                user_objectives=[make_user_objective(user_points=15)]
            ).get_user_points()
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


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEUserGameToDict:
    def test_returns_dict(self):
        assert isinstance(make_user_game().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_user_game().to_dict()
        for key in ("name", "ce_id", "objectives"):
            assert key in result
