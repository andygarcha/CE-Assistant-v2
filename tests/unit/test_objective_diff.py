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


from pi_screenshot_service.objective_diff import (
    _custom_requirement_text,
    compute_objective_diffs,
)


def _old_objective(id, name, description, points, requirements, type):
    return {
        "id": id,
        "name": name,
        "description": description,
        "points": points,
        "requirements": requirements,
        "type": type,
    }


def _live_objective(id, name, description, points, type, requirements_data=""):
    objective_requirements = (
        [{"type": "custom", "data": requirements_data}] if requirements_data else []
    )
    return {
        "id": id,
        "name": name,
        "description": description,
        "points": points,
        "type": type,
        "objectiveRequirements": objective_requirements,
    }


def test_custom_requirement_text_returns_data_for_custom_type():
    objective = {"objectiveRequirements": [{"type": "custom", "data": "Do the thing"}]}
    assert _custom_requirement_text(objective) == "Do the thing"


def test_custom_requirement_text_ignores_achievement_type():
    objective = {"objectiveRequirements": [{"type": "achievement", "data": "ach-id"}]}
    assert _custom_requirement_text(objective) == ""


def test_custom_requirement_text_returns_empty_when_no_requirements():
    objective = {"objectiveRequirements": []}
    assert _custom_requirement_text(objective) == ""


def test_custom_requirement_text_finds_custom_among_mixed_types():
    objective = {
        "objectiveRequirements": [
            {"type": "achievement", "data": "ach-1"},
            {"type": "custom", "data": "The real requirement"},
        ]
    }
    assert _custom_requirement_text(objective) == "The real requirement"


def test_compute_objective_diffs_detects_new_objective():
    game_json = {"objectives": [_live_objective("obj-1", "Name", "Desc", 10, "primary")]}

    diffs = compute_objective_diffs([], game_json)

    assert diffs == [{"objective_id": "obj-1", "is_new": True, "field_changes": []}]


def test_compute_objective_diffs_detects_type_change_as_new():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "", "secondary")]
    game_json = {"objectives": [_live_objective("obj-1", "Name", "Desc", 10, "primary")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [{"objective_id": "obj-1", "is_new": True, "field_changes": []}]


def test_compute_objective_diffs_type_comparison_is_case_insensitive():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "", "Primary")]
    game_json = {"objectives": [_live_objective("obj-1", "Name", "Desc", 10, "primary")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == []


def test_compute_objective_diffs_detects_name_change():
    old = [_old_objective("obj-1", "Old Name", "Desc", 10, "", "primary")]
    game_json = {"objectives": [_live_objective("obj-1", "New Name", "Desc", 10, "primary")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [
        {
            "objective_id": "obj-1",
            "is_new": False,
            "field_changes": [{"field": "name", "old": "Old Name", "new": "New Name"}],
        }
    ]


def test_compute_objective_diffs_detects_description_change():
    old = [_old_objective("obj-1", "Name", "Old desc", 10, "", "primary")]
    game_json = {"objectives": [_live_objective("obj-1", "Name", "New desc", 10, "primary")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [
        {
            "objective_id": "obj-1",
            "is_new": False,
            "field_changes": [
                {"field": "description", "old": "Old desc", "new": "New desc"}
            ],
        }
    ]


def test_compute_objective_diffs_detects_points_change():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "", "primary")]
    game_json = {"objectives": [_live_objective("obj-1", "Name", "Desc", 20, "primary")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [
        {
            "objective_id": "obj-1",
            "is_new": False,
            "field_changes": [{"field": "points", "old": "10", "new": "20"}],
        }
    ]


def test_compute_objective_diffs_zeroes_points_for_community_type():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "", "community")]
    game_json = {"objectives": [_live_objective("obj-1", "Name", "Desc", 0, "community")]}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == []


def test_compute_objective_diffs_detects_requirements_change():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "Old req", "primary")]
    game_json = {
        "objectives": [
            _live_objective("obj-1", "Name", "Desc", 10, "primary", "New req")
        ]
    }

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [
        {
            "objective_id": "obj-1",
            "is_new": False,
            "field_changes": [
                {"field": "requirements", "old": "Old req", "new": "New req"}
            ],
        }
    ]


def test_compute_objective_diffs_ignores_unchanged_objective():
    old = [_old_objective("obj-1", "Name", "Desc", 10, "Req", "primary")]
    game_json = {
        "objectives": [_live_objective("obj-1", "Name", "Desc", 10, "primary", "Req")]
    }

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == []


def test_compute_objective_diffs_ignores_removed_objective():
    old = [_old_objective("obj-removed", "Name", "Desc", 10, "", "primary")]
    game_json = {"objectives": []}

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == []


def test_compute_objective_diffs_detects_multiple_field_changes_at_once():
    old = [_old_objective("obj-1", "Old Name", "Desc", 10, "", "primary")]
    game_json = {
        "objectives": [_live_objective("obj-1", "New Name", "Desc", 20, "primary")]
    }

    diffs = compute_objective_diffs(old, game_json)

    assert diffs == [
        {
            "objective_id": "obj-1",
            "is_new": False,
            "field_changes": [
                {"field": "name", "old": "Old Name", "new": "New Name"},
                {"field": "points", "old": "10", "new": "20"},
            ],
        }
    ]
