import io
from unittest.mock import MagicMock, patch

from PIL import Image
from selenium.webdriver.common.by import By

from pi_screenshot_service import objective_diff
from pi_screenshot_service.capture import capture_objective_diff


def _make_row_element():
    row = MagicMock()
    row.location = {"x": 10, "y": 20}
    row.size = {"width": 300, "height": 80}
    return row


def _make_diff_driver(row, highlight_succeeds=True):
    driver = MagicMock()

    page_scripts = {
        "return document.body.offsetWidth": 500,
        "return document.body.parentNode.scrollHeight": 500,
        "return document.body.clientWidth": 500,
        "return window.innerHeight": 500,
    }

    def execute_script(script, *args):
        if script == objective_diff.DIFF_HIGHLIGHT_JS:
            return highlight_succeeds
        return page_scripts.get(script)

    driver.execute_script.side_effect = execute_script
    driver.get_window_size.return_value = {"width": 500, "height": 500}

    objective_row_marker = MagicMock()
    objective_row_marker.is_displayed.return_value = True
    driver.find_elements.return_value = [objective_row_marker]

    def find_element(by, value):
        if by == By.XPATH:
            return row
        raise AssertionError(f"unexpected find_element call: {by}, {value}")

    driver.find_element.side_effect = find_element

    tile = Image.new("RGB", (500, 500), (10, 20, 30))
    buf = io.BytesIO()
    tile.save(buf, format="PNG")
    driver.get_screenshot_as_png.return_value = buf.getvalue()

    return driver


def _run_capture_diff(driver, game_id="game-1", objective_id="obj-1", old_text="old value", new_text="new value", game_json=None):
    if game_json is None:
        game_json = {"objectives": [{"id": "obj-1", "name": "Some Objective"}]}

    with (
        patch("pi_screenshot_service.capture.time.sleep"),
        patch("Modules.Screenshot.time.sleep"),
        patch(
            "pi_screenshot_service.capture.objective_diff.fetch_game_json",
            return_value=game_json,
        ),
    ):
        return capture_objective_diff(driver, game_id, objective_id, old_text, new_text)


def test_capture_objective_diff_returns_png_bytes():
    row = _make_row_element()
    driver = _make_diff_driver(row)

    image_bytes, _timings = _run_capture_diff(driver)

    image = Image.open(io.BytesIO(image_bytes))
    assert image.format == "PNG"


def test_capture_objective_diff_injects_highlight_with_correct_texts():
    row = _make_row_element()
    driver = _make_diff_driver(row)

    _run_capture_diff(driver, old_text="Win the game", new_text="Beat the game")

    diff_calls = [
        call
        for call in driver.execute_script.call_args_list
        if call.args[0] == objective_diff.DIFF_HIGHLIGHT_JS
    ]
    assert len(diff_calls) == 1
    _script, root_arg, old_arg, new_arg, _field_arg = diff_calls[0].args
    assert root_arg is row
    assert old_arg == "Win the game"
    assert new_arg == "Beat the game"


def test_capture_objective_diff_returns_timing_breakdown():
    row = _make_row_element()
    driver = _make_diff_driver(row)

    _image_bytes, timings = _run_capture_diff(driver)

    assert set(timings) == {"warmup", "api_lookup", "page_load", "highlight", "screenshot"}
    for phase, seconds in timings.items():
        assert isinstance(seconds, float), phase
        assert seconds >= 0, phase


def test_capture_objective_diff_raises_when_objective_not_found():
    row = _make_row_element()
    driver = _make_diff_driver(row)

    try:
        _run_capture_diff(driver, objective_id="missing-obj", game_json={"objectives": []})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "missing-obj" in str(e)


def test_capture_objective_diff_raises_when_highlight_text_not_found():
    row = _make_row_element()
    driver = _make_diff_driver(row, highlight_succeeds=False)

    try:
        _run_capture_diff(driver, new_text="text that is not on the page")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "text that is not on the page" in str(e)
