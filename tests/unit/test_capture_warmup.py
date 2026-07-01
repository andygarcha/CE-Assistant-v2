import io
from unittest.mock import MagicMock, patch

from PIL import Image

from pi_screenshot_service.capture import (
    WARMUP_GAME_ID,
    _warm_up_browser,
    capture_game_screenshot,
)


def test_warm_up_browser_navigates_to_the_warmup_game_page():
    driver = MagicMock()

    with patch("pi_screenshot_service.capture.time.sleep"):
        _warm_up_browser(driver)

    driver.get.assert_called_once_with(f"https://cedb.me/game/{WARMUP_GAME_ID}/")


def _make_element(x, y, width, height, displayed=True):
    element = MagicMock()
    element.is_displayed.return_value = displayed
    element.location = {"x": x, "y": y}
    element.size = {"width": width, "height": height}
    return element


def _make_capture_driver():
    "A fake driver just capable enough to make capture_game_screenshot run end to end."
    driver = MagicMock()

    objective = _make_element(0, 400, 200, 50)
    primary_table = MagicMock()
    primary_table.find_elements.return_value = [objective, objective]
    title = _make_element(0, 0, 100, 30)
    header_image = _make_element(0, 0, 300, 200)

    def find_element(by, value):
        if value == "css-c4zdq5":
            return primary_table
        if value == "h1":
            return title
        if value == "GamePage-Header-Image":
            return header_image
        raise AssertionError(f"unexpected find_element call: {value}")

    driver.find_element.side_effect = find_element
    driver.find_elements.return_value = [objective]

    scripts = {
        "return document.body.offsetWidth": 500,
        "return document.body.parentNode.scrollHeight": 500,
        "return document.body.clientWidth": 500,
        "return window.innerHeight": 500,
    }
    driver.execute_script.side_effect = lambda script, *a: scripts.get(script)
    driver.get_window_size.return_value = {"width": 500, "height": 500}

    tile = Image.new("RGB", (500, 500), (10, 20, 30))
    buf = io.BytesIO()
    tile.save(buf, format="PNG")
    driver.get_screenshot_as_png.return_value = buf.getvalue()

    return driver


def _run_capture(driver, game_id="target-game-id"):
    with patch("pi_screenshot_service.capture.time.sleep"), patch(
        "Modules.Screenshot.time.sleep"
    ):
        return capture_game_screenshot(driver, game_id)


def test_capture_game_screenshot_warms_up_before_navigating_to_target_game():
    driver = _make_capture_driver()

    _run_capture(driver)

    urls = [call.args[0] for call in driver.get.call_args_list]
    assert urls == [
        f"https://cedb.me/game/{WARMUP_GAME_ID}/",
        "https://cedb.me/game/target-game-id/",
    ]


def test_capture_game_screenshot_does_not_pad_with_black_when_header_is_flush_left():
    "The header image sits at (0, 0); subtracting BORDER_WIDTH must not go negative."
    driver = _make_capture_driver()

    image_bytes, _timings = _run_capture(driver)

    image = Image.open(io.BytesIO(image_bytes))
    assert image.getpixel((0, 0)) == (10, 20, 30)


def test_capture_game_screenshot_returns_a_timing_breakdown():
    driver = _make_capture_driver()

    _image_bytes, timings = _run_capture(driver)

    assert set(timings) == {"warmup", "page_load", "render", "screenshot"}
    for phase, seconds in timings.items():
        assert isinstance(seconds, float), phase
        assert seconds >= 0, phase
