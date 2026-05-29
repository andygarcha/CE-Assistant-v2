import pytest

from Classes.CE_Objective import CEObjective
from tests.conftest import make_objective


# ── constructor normalization ─────────────────────────────────────────────────


class TestCEObjectiveConstructor:
    def test_empty_requirements_normalized_to_none(self):
        obj = make_objective(requirements="")
        assert obj.requirements is None

    def test_none_requirements_stays_none(self):
        obj = make_objective(requirements=None)
        assert obj.requirements is None

    def test_populated_requirements_preserved(self):
        obj = make_objective(requirements="Do the thing.")
        assert obj.requirements == "Do the thing."

    def test_empty_achievement_ce_ids_normalized_to_none(self):
        obj = make_objective(achievement_ce_ids=[])
        assert obj.achievement_ce_ids is None

    def test_none_achievement_ce_ids_stays_none(self):
        assert make_objective(achievement_ce_ids=None).achievement_ce_ids is None

    def test_populated_achievement_ce_ids_preserved(self):
        ids = ["ach-001", "ach-002"]
        assert make_objective(achievement_ce_ids=ids).achievement_ce_ids == ids


# ── is_uncleared ──────────────────────────────────────────────────────────────


class TestIsUncleared:
    def test_zero_point_value_is_uncleared(self):
        assert make_objective(point_value=0).is_uncleared() is True

    def test_uncleared_in_name_is_uncleared(self):
        assert make_objective(name="Beat the game (UNCLEARED)").is_uncleared() is True

    def test_unvalued_in_name_is_uncleared(self):
        assert make_objective(name="Beat the game (UNVALUED)").is_uncleared() is True

    def test_normal_objective_is_not_uncleared(self):
        assert (
            make_objective(point_value=10, name="Beat the game").is_uncleared() is False
        )

    def test_nonzero_points_with_clean_name_not_uncleared(self):
        assert make_objective(point_value=50).is_uncleared() is False


# ── has_partial ───────────────────────────────────────────────────────────────


class TestHasPartial:
    def test_zero_partial_returns_false(self):
        assert make_objective(point_value_partial=0).has_partial() is False

    def test_nonzero_partial_returns_true(self):
        assert make_objective(point_value_partial=5).has_partial() is True

    def test_none_partial_returns_false(self):

        obj = make_objective()
        assert isinstance(obj, CEObjective)
        obj._point_value_partial = 0
        assert obj.has_partial() is False


# ── uncleared_name ────────────────────────────────────────────────────────────


class TestUnclearedName:
    def test_strips_uncleared_suffix(self):
        obj = make_objective(name="Beat the game (UNCLEARED)")
        assert obj.uncleared_name() == "Beat the game"

    def test_strips_unvalued_suffix(self):
        obj = make_objective(name="Beat the game (UNVALUED)")
        assert obj.uncleared_name() == "Beat the game"

    def test_normal_name_returned_unchanged(self):
        obj = make_objective(name="Beat the game", point_value=10)
        assert obj.uncleared_name() == "Beat the game"


# ── get_type_short ────────────────────────────────────────────────────────────


class TestGetTypeShort:
    @pytest.mark.parametrize(
        "obj_type, expected",
        [
            ("Primary", "PO"),
            ("Secondary", "SO"),
            ("Badge", "BO"),
            ("Community", "CO"),
        ],
    )
    def test_short_types(self, obj_type, expected):
        assert make_objective(obj_type=obj_type).get_type_short() == expected


# ── equals ────────────────────────────────────────────────────────────────────


class TestEquals:
    def test_identical_objectives_are_equal(self):
        a = make_objective()
        b = make_objective()
        assert a.equals(b) is True

    def test_different_point_value_not_equal(self):
        assert (
            make_objective(point_value=10).equals(make_objective(point_value=20))
            is False
        )

    def test_different_type_not_equal(self):
        assert (
            make_objective(obj_type="Primary").equals(make_objective(obj_type="Badge"))
            is False
        )

    def test_different_name_not_equal(self):
        assert make_objective(name="A").equals(make_objective(name="B")) is False

    def test_different_ce_id_not_equal(self):
        assert (
            make_objective(ce_id="id-a").equals(make_objective(ce_id="id-b")) is False
        )

    def test_non_objective_returns_false(self):
        assert make_objective().equals(make_objective(obj_type="Community")) is False

    def test_one_has_achievements_other_does_not(self):
        with_ach = make_objective(achievement_ce_ids=["ach-001"])
        without_ach = make_objective(achievement_ce_ids=None)
        assert with_ach.equals(without_ach) is False

    def test_same_achievements_equal(self):
        ids = ["ach-001", "ach-002"]
        a = make_objective(achievement_ce_ids=ids)
        b = make_objective(achievement_ce_ids=ids)
        assert a.equals(b) is True

    def test_different_partial_points_not_equal(self):
        assert (
            make_objective(point_value_partial=0).equals(
                make_objective(point_value_partial=5)
            )
            is False
        )


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEObjectiveToDict:
    def test_returns_dict(self):
        assert isinstance(make_objective().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_objective().to_dict()
        for key in ("name", "ce_id", "value", "description", "game_ce_id", "type"):
            assert key in result
