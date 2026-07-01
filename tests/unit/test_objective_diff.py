import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

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
    request_obj = args[0]
    assert request_obj.full_url == "https://cedb.me/api/game/game-1"


def test_fetch_game_json_sends_correct_user_agent_header():
    body = json.dumps({"id": "game-1", "objectives": []}).encode()
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=None)

    with patch(
        "pi_screenshot_service.objective_diff.urllib.request.urlopen",
        return_value=response,
    ) as mock_urlopen:
        fetch_game_json("game-1")

    args, kwargs = mock_urlopen.call_args
    request_obj = args[0]
    assert request_obj.get_header("User-agent") == "CE-Assistant-pi-screenshot-service/1.0"


def test_fetch_game_json_raises_value_error_when_game_not_found():
    url = "https://cedb.me/api/game/does-not-exist"
    http_error = HTTPError(url, 404, "Not Found", {}, None)

    with patch(
        "pi_screenshot_service.objective_diff.urllib.request.urlopen",
        side_effect=http_error,
    ):
        with pytest.raises(ValueError, match="does-not-exist"):
            fetch_game_json("does-not-exist")


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
    assert result == "//tr[.//h3[text()[1] = 'Mountain Climber']]"


def test_build_diff_row_xpath_uses_exact_equality_not_substring_containment():
    # A short objective name (e.g. "Clear") must not ambiguously match a row
    # for a longer objective name that has it as a text-prefix (e.g. "Clear
    # the Level"). Exact equality against the h3's first text node avoids
    # the ambiguity that `contains()` would introduce.
    result = build_diff_row_xpath("Clear")
    assert " = " in result
    assert "contains(" not in result


def test_inject_diff_highlight_calls_execute_script_with_correct_arguments():
    from pi_screenshot_service.objective_diff import DIFF_HIGHLIGHT_JS, inject_diff_highlight

    driver = MagicMock()
    driver.execute_script.return_value = True
    row = MagicMock()

    result = inject_diff_highlight(driver, row, "Win the game", "Beat the game")

    assert result is True
    driver.execute_script.assert_called_once_with(
        DIFF_HIGHLIGHT_JS, row, "Win the game", "Beat the game"
    )


def test_inject_diff_highlight_returns_false_when_execute_script_returns_false():
    from pi_screenshot_service.objective_diff import inject_diff_highlight

    driver = MagicMock()
    driver.execute_script.return_value = False
    row = MagicMock()

    result = inject_diff_highlight(driver, row, "old", "new")

    assert result is False
