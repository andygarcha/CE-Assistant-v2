import json
from unittest.mock import MagicMock, patch

from pi_screenshot_service.objective_diff import fetch_game_json, find_objective_name


def test_fetch_game_json_parses_response_body():
    body = json.dumps({"id": "game-1", "objectives": []}).encode()
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=None)

    with patch(
        "pi_screenshot_service.objective_diff.urllib.request.urlopen",
        return_value=response,
    ) as mock_urlopen:
        result = fetch_game_json("game-1")

    assert result == {"id": "game-1", "objectives": []}
    args, kwargs = mock_urlopen.call_args
    assert args[0] == "https://cedb.me/api/game/game-1"


def test_find_objective_name_returns_matching_name():
    game_json = {
        "objectives": [
            {"id": "obj-1", "name": "First"},
            {"id": "obj-2", "name": "Second"},
        ]
    }

    assert find_objective_name(game_json, "obj-2") == "Second"


def test_find_objective_name_returns_none_when_missing():
    game_json = {"objectives": [{"id": "obj-1", "name": "First"}]}

    assert find_objective_name(game_json, "does-not-exist") is None
