import json
from unittest.mock import MagicMock, patch

from pi_screenshot_service.objective_diff import (
    build_diff_row_xpath,
    fetch_game_json,
    find_objective_name,
    xpath_literal,
)


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


def test_xpath_literal_wraps_plain_text_in_single_quotes():
    assert xpath_literal("Mountain Climber") == "'Mountain Climber'"


def test_xpath_literal_uses_single_quotes_when_value_only_has_double_quotes():
    # Real objective title from the Alkali game's /api payload
    value = '"A" is for Alkali'
    assert xpath_literal(value) == "'" + value + "'"


def test_xpath_literal_uses_double_quotes_when_value_has_a_single_quote():
    value = "Player's Choice"
    assert xpath_literal(value) == '"' + value + '"'


def test_xpath_literal_uses_concat_when_value_has_both_quote_types():
    value = "Player's \"Choice\""
    result = xpath_literal(value)

    single_quote = "'"
    double_quote = '"'
    expected = (
        "concat("
        + single_quote + "Player" + single_quote
        + ", " + double_quote + single_quote + double_quote + ", "
        + single_quote + 's "Choice"' + single_quote
        + ")"
    )
    assert result == expected


def test_build_diff_row_xpath_embeds_the_literal():
    result = build_diff_row_xpath("Mountain Climber")
    assert result == "//tr[.//h3[contains(., 'Mountain Climber')]]"
