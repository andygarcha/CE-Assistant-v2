import io
from unittest.mock import MagicMock, patch

from PIL import Image

from Modules.Screenshot import Screenshot


def _tile_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_driver(total_width, total_height, viewport_width, viewport_height, tile_colors):
    "A fake single-viewport-tall or multi-viewport-tall page driver."
    scripts = {
        "return document.body.offsetWidth": total_width,
        "return document.body.parentNode.scrollHeight": total_height,
        "return document.body.clientWidth": viewport_width,
        "return window.innerHeight": viewport_height,
    }

    def execute_script(script, *args):
        return scripts.get(script)

    driver = MagicMock()
    driver.get_window_size.return_value = {
        "width": viewport_width,
        "height": viewport_height,
    }
    driver.execute_script.side_effect = execute_script

    calls = {"n": 0}

    def get_screenshot_as_png():
        color = tile_colors[calls["n"]]
        calls["n"] += 1
        return _tile_png(viewport_width, viewport_height, color)

    driver.get_screenshot_as_png.side_effect = get_screenshot_as_png
    return driver


def test_full_screenshot_stitches_a_page_taller_than_one_viewport():
    "A page twice the viewport height should produce one image covering the full height."
    driver = _make_driver(
        total_width=100,
        total_height=200,
        viewport_width=100,
        viewport_height=100,
        tile_colors=[(255, 0, 0), (0, 255, 0)],
    )
    screenshot = Screenshot(final_page_height=200)

    with patch("Modules.Screenshot.time.sleep"):
        result = screenshot.full_screenshot(driver)

    assert isinstance(result, bytes)
    image = Image.open(io.BytesIO(result))
    assert image.size == (100, 200)
    # top tile should be red, bottom tile should be green
    assert image.getpixel((50, 10)) == (255, 0, 0)
    assert image.getpixel((50, 150)) == (0, 255, 0)


def test_full_screenshot_settles_briefly_between_tile_scrolls():
    "Per-tile settle sleep must stay well under the pi service's capture timeout."
    driver = _make_driver(
        total_width=100,
        total_height=200,
        viewport_width=100,
        viewport_height=100,
        tile_colors=[(255, 0, 0), (0, 255, 0)],
    )
    screenshot = Screenshot(final_page_height=200)

    with patch("Modules.Screenshot.time.sleep") as mock_sleep:
        screenshot.full_screenshot(driver)

    # only tile-to-tile scrolls need a settle; there's one scroll for 2 tiles
    tile_sleeps = [call.args[0] for call in mock_sleep.call_args_list]
    assert tile_sleeps == [2]


def test_full_screenshot_does_not_sleep_when_page_fits_in_one_tile():
    "No scrolling happens for a single-tile page, so there's nothing to settle for."
    driver = _make_driver(
        total_width=100,
        total_height=100,
        viewport_width=100,
        viewport_height=100,
        tile_colors=[(255, 0, 0)],
    )
    screenshot = Screenshot(final_page_height=100)

    with patch("Modules.Screenshot.time.sleep") as mock_sleep:
        screenshot.full_screenshot(driver)

    mock_sleep.assert_not_called()
