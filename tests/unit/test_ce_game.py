import pytest

from Classes.CE_Game import CEGame
from tests.conftest import make_game, make_objective


# ── helpers ───────────────────────────────────────────────────────────────────

def _po(points: int, name: str = "Test PO") -> object:
    """Primary objective with the given point value."""
    return make_objective(point_value=points, obj_type="Primary", name=name)


def _so(points: int) -> object:
    """Secondary objective with the given point value."""
    return make_objective(point_value=points, obj_type="Secondary")


def _uncleared_po() -> object:
    """An uncleared primary objective (0 points)."""
    return make_objective(point_value=0, obj_type="Primary", name="Uncleared PO (UNCLEARED)")


def _game_with_po_points(points: int) -> CEGame:
    """Game whose Primary Objective total equals `points`."""
    return make_game(objectives=[_po(points)])


# ── tier_num ──────────────────────────────────────────────────────────────────


class TestTierNum:
    @pytest.mark.parametrize("points, expected_tier", [
        (0,   0),   # below T1 threshold
        (4,   0),   # still below T1 (threshold is 5)
        (5,   1),
        (19,  1),
        (20,  2),
        (39,  2),
        (40,  3),
        (79,  3),
        (80,  4),
        (199, 4),
        (200, 5),
        (399, 5),
        (400, 6),
        (799, 6),
        (800, 7),
        (9999, 7),
    ])
    def test_tier_boundaries(self, points, expected_tier):
        assert _game_with_po_points(points).tier_num == expected_tier

    def test_tier_string_matches_num(self):
        game = _game_with_po_points(20)
        assert game.tier == f"Tier {game.tier_num}"

    def test_uncleared_po_not_counted_in_tier(self):
        # Uncleared PO has 0 points, should not push game above T0
        game = make_game(objectives=[_uncleared_po()])
        assert game.tier_num == 0


# ── is_t0 ─────────────────────────────────────────────────────────────────────


class TestIsT0:
    def test_no_objectives_is_t0(self):
        assert make_game(objectives=[]).is_t0 is True

    def test_zero_point_objective_is_t0(self):
        # get_total_points includes uncleareds, but uncleared = 0 pts
        game = make_game(objectives=[_uncleared_po()])
        assert game.is_t0 is True

    def test_nonzero_points_not_t0(self):
        assert _game_with_po_points(10).is_t0 is False


# ── is_role_t4 ────────────────────────────────────────────────────────────────


class TestIsRoleT4:
    def test_t4_with_150_or_more_points_is_role_t4(self):
        # T4 range: 80-199; role_t4 requires >= 150
        assert _game_with_po_points(150).is_role_t4 is True
        assert _game_with_po_points(199).is_role_t4 is True

    def test_t4_below_150_not_role_t4(self):
        assert _game_with_po_points(80).is_role_t4 is False
        assert _game_with_po_points(149).is_role_t4 is False

    def test_t5_not_role_t4(self):
        assert _game_with_po_points(200).is_role_t4 is False


# ── is_t5plus ─────────────────────────────────────────────────────────────────


class TestIsT5Plus:
    def test_t5_is_t5plus(self):
        assert _game_with_po_points(200).is_t5plus is True

    def test_t7_is_t5plus(self):
        assert _game_with_po_points(800).is_t5plus is True

    def test_t4_not_t5plus(self):
        assert _game_with_po_points(80).is_t5plus is False


# ── has_uncleared ─────────────────────────────────────────────────────────────


class TestHasUncleared:
    def test_uncleared_objective_detected(self):
        game = make_game(objectives=[_po(10), _uncleared_po()])
        assert game.has_uncleared is True

    def test_no_uncleared_objectives(self):
        game = make_game(objectives=[_po(10), _po(20)])
        assert game.has_uncleared is False

    def test_empty_objectives_no_uncleared(self):
        assert make_game(objectives=[]).has_uncleared is False


# ── get_total_points ──────────────────────────────────────────────────────────


class TestGetTotalPoints:
    def test_sums_all_objective_types(self):
        game = make_game(objectives=[_po(10), _so(5)])
        assert game.get_total_points() == 15

    def test_includes_uncleared_objectives(self):
        # Uncleareds have 0 pts so total is unchanged, but this confirms no skip
        game = make_game(objectives=[_po(10), _uncleared_po()])
        assert game.get_total_points() == 10

    def test_empty_game_zero_points(self):
        assert make_game(objectives=[]).get_total_points() == 0


# ── get_po_points ─────────────────────────────────────────────────────────────


class TestGetPoPoints:
    def test_only_primary_counted(self):
        game = make_game(objectives=[_po(10), _so(99)])
        assert game.get_po_points() == 10

    def test_excludes_uncleareds_by_default(self):
        game = make_game(objectives=[_po(10), _uncleared_po()])
        assert game.get_po_points(include_uncleareds=False) == 10

    def test_includes_uncleareds_when_flagged(self):
        game = make_game(objectives=[_po(10), _uncleared_po()])
        # uncleared adds 0 pts, so total is still 10
        assert game.get_po_points(include_uncleareds=True) == 10


# ── get_so_points ─────────────────────────────────────────────────────────────


class TestGetSoPoints:
    def test_only_secondary_counted(self):
        game = make_game(objectives=[_po(99), _so(15)])
        assert game.get_so_points() == 15

    def test_uncleared_secondary_excluded(self):
        uncleared_so = make_objective(point_value=0, obj_type="Secondary", name="SO (UNCLEARED)")
        game = make_game(objectives=[_so(15), uncleared_so])
        assert game.get_so_points() == 15

    def test_no_secondaries_returns_zero(self):
        assert make_game(objectives=[_po(10)]).get_so_points() == 0


# ── get_primary_objectives ────────────────────────────────────────────────────


class TestGetPrimaryObjectives:
    def test_excludes_uncleareds_by_default(self):
        game = make_game(objectives=[_po(10), _uncleared_po()])
        assert len(game.get_primary_objectives()) == 1

    def test_includes_uncleareds_with_flag(self):
        game = make_game(objectives=[_po(10), _uncleared_po()])
        assert len(game.get_primary_objectives(include_uncleareds=True)) == 2

    def test_excludes_secondary_objectives(self):
        game = make_game(objectives=[_po(10), _so(5)])
        result = game.get_primary_objectives()
        assert all(o.type == "Primary" for o in result)


# ── get_objective ─────────────────────────────────────────────────────────────


class TestGetObjective:
    def test_returns_objective_by_id(self):
        obj = _po(10)
        game = make_game(objectives=[obj])
        assert game.get_objective(obj.ce_id) is obj

    def test_returns_none_for_missing_id(self):
        assert make_game(objectives=[]).get_objective("nonexistent") is None


# ── categories helpers ────────────────────────────────────────────────────────


class TestCategories:
    @pytest.mark.parametrize("cats, expected_nums", [
        (["Action"], [1]),
        (["Arcade"], [2]),
        (["Bullet Hell"], [3]),
        (["First-Person"], [4]),
        (["Platformer"], [5]),
        (["Strategy"], [6]),
        (["Action", "Strategy"], [1, 6]),
    ])
    def test_categories_num(self, cats, expected_nums):
        assert make_game(categories=cats).categories_num == expected_nums

    def test_categories_string_single(self):
        assert make_game(categories=["Action"]).categories_string == "Action"

    def test_categories_string_multiple(self):
        result = make_game(categories=["Arcade", "Strategy"]).categories_string
        assert result == "Arcade, Strategy"


# ── ce_link ───────────────────────────────────────────────────────────────────


class TestCELink:
    def test_ce_link_format(self):
        game = make_game(ce_id="abcd1234-0000-0000-0000-000000000000")
        assert game.ce_link == "https://cedb.me/game/abcd1234-0000-0000-0000-000000000000"


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEGameToDict:
    def test_returns_dict(self):
        assert isinstance(make_game().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_game().to_dict()
        for key in ("name", "ce_id", "platform", "categories", "objectives"):
            assert key in result
