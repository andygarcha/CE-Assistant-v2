"""
Tests for `CEAPIReader._ce_to_user`'s objective parsing, specifically that it
passes the API's `partial` flag straight through to `CEUserObjective` instead
of pre-computing a `user_points` snapshot (Modules/CEAPIReader.py:474-489).
"""

from Modules.CEAPIReader import _ce_to_user


def _api_user_response(**overrides) -> dict:
    response = {
        "id": "user-001-0000-0000-000000000000",
        "displayName": "TestUser",
        "avatar": "https://example.com/avatar.png",
        "userConnections": [],
        "userGames": [
            {"game": {"id": "game-001-0000-0000-000000000000", "name": "Test Game"}}
        ],
        "userObjectives": [
            {
                "partial": False,
                "objective": {
                    "id": "obj-001-0000-0000-000000000000",
                    "gameId": "game-001-0000-0000-000000000000",
                    "name": "Test Objective",
                    "type": "primary",
                    "points": 25,
                    "pointsPartial": 5,
                },
            }
        ],
    }
    response.update(overrides)
    return response


def _find_objective(user, ce_id: str):
    for game in user.owned_games:
        for obj in game.user_objectives:
            if obj.ce_id == ce_id:
                return obj
    return None


def test_full_completion_gets_full_points():
    user = _ce_to_user(_api_user_response())
    assert user is not None
    obj = _find_objective(user, "obj-001-0000-0000-000000000000")
    assert obj is not None
    assert obj.user_points == 25


def test_partial_completion_gets_partial_points():
    response = _api_user_response()
    response["userObjectives"][0]["partial"] = True
    user = _ce_to_user(response)
    assert user is not None
    obj = _find_objective(user, "obj-001-0000-0000-000000000000")
    assert obj is not None
    assert obj.user_points == 5


def test_partial_flag_is_preserved_on_the_object():
    response = _api_user_response()
    response["userObjectives"][0]["partial"] = True
    user = _ce_to_user(response)
    assert user is not None
    obj = _find_objective(user, "obj-001-0000-0000-000000000000")
    assert obj is not None
    assert obj.partial is True
