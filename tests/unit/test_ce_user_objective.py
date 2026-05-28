import pytest

from Classes.CE_User_Objective import CEUserObjective
from tests.conftest import make_user_objective

GAME_ID = "game-001-0000-0000-000000000000"
OBJ_ID = "obj-0001-0000-0000-000000000000"


# ── properties ────────────────────────────────────────────────────────────────


class TestCEUserObjectiveProperties:
    def test_ce_id(self):
        assert make_user_objective(ce_id=OBJ_ID).ce_id == OBJ_ID

    def test_game_ce_id(self):
        assert make_user_objective(game_ce_id=GAME_ID).game_ce_id == GAME_ID

    def test_type(self):
        assert make_user_objective(obj_type="Primary").type == "Primary"

    def test_user_points(self):
        assert make_user_objective(user_points=42).user_points == 42

    def test_name(self):
        assert make_user_objective(name="Complete it").name == "Complete it"

    def test_name_defaults_to_empty_string(self):
        obj = CEUserObjective(
            ce_id=OBJ_ID, game_ce_id=GAME_ID, type="Primary", user_points=10
        )
        assert obj.name == ""

    @pytest.mark.parametrize("obj_type", ["Primary", "Secondary", "Badge", "Community"])
    def test_all_objective_types(self, obj_type):
        assert make_user_objective(obj_type=obj_type).type == obj_type


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestCEUserObjectiveToDict:
    def test_returns_dict(self):
        assert isinstance(make_user_objective().to_dict(), dict)

    def test_expected_keys_present(self):
        result = make_user_objective().to_dict()
        for key in ("name", "ce_id", "game_ce_id", "type", "user_points"):
            assert key in result

    def test_values_match(self):
        obj = make_user_objective(
            ce_id=OBJ_ID, game_ce_id=GAME_ID, obj_type="Badge", user_points=25
        )
        d = obj.to_dict()
        assert d["ce_id"] == OBJ_ID
        assert d["game_ce_id"] == GAME_ID
        assert d["type"] == "Badge"
        assert d["user_points"] == 25
