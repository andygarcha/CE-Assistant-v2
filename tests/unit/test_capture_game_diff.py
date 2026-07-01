import io
from unittest.mock import MagicMock, patch

from PIL import Image
from selenium.webdriver.common.by import By

from pi_screenshot_service import objective_diff
from pi_screenshot_service.capture import capture_game_diff


def _make_row(x, y, width, height):
    row = MagicMock()
    row.location = {"x": x, "y": y}
    row.size = {"width": width, "height": height}
    return row


def _make_game_diff_driver(row_a, row_b):
    driver = MagicMock()

    page_scripts = {
        "return document.body.offsetWidth": 900,
        "return document.body.parentNode.scrollHeight": 900,
        "return document.body.clientWidth": 900,
        "return window.innerHeight": 900,
    }

    def execute_script(script, *args):
        if script == objective_diff.DIFF_HIGHLIGHT_JS:
            return True
        if script == objective_diff.HIGHLIGHT_NEW_ROW_JS:
            return None
        return page_scripts.get(script)

    driver.execute_script.side_effect = execute_script
    driver.get_window_size.return_value = {"width": 900, "height": 900}

    objective_marker = MagicMock()
    objective_marker.is_displayed.return_value = True
    objective_marker.location = {"x": 0, "y": 400}
    objective_marker.size = {"width": 800, "height": 50}
    driver.find_elements.return_value = [objective_marker]

    primary_table = MagicMock()
    primary_table.find_elements.return_value = [objective_marker, objective_marker]

    title = MagicMock()
    title.size = {"width": 100}
    title.location = {"x": 0}

    header_image = MagicMock()
    header_image.location = {"x": 0, "y": 0}

    xpath_a = objective_diff.build_diff_row_xpath("Old Objective")
    xpath_b = objective_diff.build_diff_row_xpath("New Objective")

    def find_element(by, value):
        if by == By.CLASS_NAME and value == "css-c4zdq5":
            return primary_table
        if by == By.TAG_NAME and value == "h1":
            return title
        if by == By.CLASS_NAME and value == "GamePage-Header-Image":
            return header_image
        if by == By.XPATH and value == xpath_a:
            return row_a
        if by == By.XPATH and value == xpath_b:
            return row_b
        raise AssertionError(f"unexpected find_element call: {by}, {value}")

    driver.find_element.side_effect = find_element

    tile = Image.new("RGB", (900, 900), (5, 5, 5))
    buf = io.BytesIO()
    tile.save(buf, format="PNG")
    driver.get_screenshot_as_png.return_value = buf.getvalue()

    return driver


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


def _run_capture_game_diff(driver, game_id, old_objectives, game_json):
    with (
        patch("pi_screenshot_service.capture.time.sleep"),
        patch("Modules.Screenshot.time.sleep"),
        patch(
            "pi_screenshot_service.capture.objective_diff.fetch_game_json",
            return_value=game_json,
        ),
    ):
        return capture_game_diff(driver, game_id, old_objectives)


def test_capture_game_diff_highlights_changed_and_new_objectives():
    row_a = _make_row(0, 100, 800, 60)
    row_b = _make_row(0, 200, 800, 60)
    driver = _make_game_diff_driver(row_a, row_b)

    old_objectives = [
        _old_objective("obj-1", "Old Objective", "Old desc", 10, "Old req", "primary"),
    ]
    game_json = {
        "objectives": [
            _live_objective("obj-1", "Old Objective", "New desc", 10, "primary", "Old req"),
            _live_objective("obj-2", "New Objective", "Brand new", 5, "primary"),
        ]
    }

    image_bytes, _timings = _run_capture_game_diff(
        driver, "game-1", old_objectives, game_json
    )

    image = Image.open(io.BytesIO(image_bytes))
    assert image.format == "PNG"

    diff_calls = [
        c
        for c in driver.execute_script.call_args_list
        if c.args[0] == objective_diff.DIFF_HIGHLIGHT_JS
    ]
    assert len(diff_calls) == 1
    assert diff_calls[0].args[1] is row_a
    assert diff_calls[0].args[2] == "Old desc"
    assert diff_calls[0].args[3] == "New desc"

    new_row_calls = [
        c
        for c in driver.execute_script.call_args_list
        if c.args[0] == objective_diff.HIGHLIGHT_NEW_ROW_JS
    ]
    assert len(new_row_calls) == 1
    assert new_row_calls[0].args[1] is row_b


def test_capture_game_diff_returns_timing_breakdown():
    row_a = _make_row(0, 100, 800, 60)
    driver = _make_game_diff_driver(row_a, row_a)

    old_objectives = [
        _old_objective("obj-1", "Old Objective", "Old desc", 10, "Old req", "primary"),
    ]
    game_json = {
        "objectives": [
            _live_objective("obj-1", "Old Objective", "New desc", 10, "primary"),
        ]
    }

    _image_bytes, timings = _run_capture_game_diff(driver, "game-1", old_objectives, game_json)

    assert set(timings) == {"warmup", "diff", "page_load", "highlight", "screenshot"}
    for phase, seconds in timings.items():
        assert isinstance(seconds, float), phase
        assert seconds >= 0, phase


def test_capture_game_diff_skips_unchanged_objectives():
    row_a = _make_row(0, 100, 800, 60)
    driver = _make_game_diff_driver(row_a, row_a)

    old_objectives = [
        _old_objective("obj-1", "Old Objective", "Same desc", 10, "Same req", "primary"),
    ]
    game_json = {
        "objectives": [
            _live_objective(
                "obj-1", "Old Objective", "Same desc", 10, "primary", "Same req"
            ),
        ]
    }

    _run_capture_game_diff(driver, "game-1", old_objectives, game_json)

    diff_calls = [
        c
        for c in driver.execute_script.call_args_list
        if c.args[0] == objective_diff.DIFF_HIGHLIGHT_JS
    ]
    new_row_calls = [
        c
        for c in driver.execute_script.call_args_list
        if c.args[0] == objective_diff.HIGHLIGHT_NEW_ROW_JS
    ]
    assert diff_calls == []
    assert new_row_calls == []
