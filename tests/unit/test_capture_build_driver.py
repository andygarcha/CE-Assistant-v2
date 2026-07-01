from unittest.mock import patch

import selenium.webdriver as webdriver

from pi_screenshot_service.capture import build_driver


def test_build_driver_uses_a_viewport_wider_than_the_site_container():
    "The site's `.container` maxes out at 1280px with no side padding; a viewport at \
    exactly that width leaves the header flush against the edge (no margin)."
    captured_args = []
    with (
        patch.object(
            webdriver.ChromeOptions,
            "add_argument",
            lambda self, arg: captured_args.append(arg),
        ),
        patch.object(webdriver, "Chrome", return_value=None),
    ):
        build_driver()

    window_size_arg = next(a for a in captured_args if a.startswith("--window-size="))
    width = int(window_size_arg.split("=")[1].split(",")[0])
    assert width > 1280
