import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp

from Modules.PiScreenshot import CONNECT_TIMEOUT_SECONDS, ScreenshotError, fetch_screenshot


def _make_session(status: int, body: bytes = b"", text: str = "", headers: dict | None = None):
    response = MagicMock()
    response.status = status
    response.read = AsyncMock(return_value=body)
    response.text = AsyncMock(return_value=text)
    response.headers = headers or {}

    get_cm = MagicMock()
    get_cm.__aenter__ = AsyncMock(return_value=response)
    get_cm.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.get = MagicMock(return_value=get_cm)
    return session


def test_fetch_screenshot_returns_image_bytes_on_success():
    session = _make_session(200, body=b"\x89PNG...")

    image_bytes, _timings = asyncio.run(
        fetch_screenshot(session, "abc-123", base_url="http://pi:8731")
    )

    assert image_bytes == b"\x89PNG..."


def test_fetch_screenshot_requests_expected_url():
    session = _make_session(200, body=b"\x89PNG...")

    asyncio.run(fetch_screenshot(session, "abc-123", base_url="http://pi:8731"))

    args, kwargs = session.get.call_args
    assert args == ("http://pi:8731/screenshot/abc-123",)


def test_fetch_screenshot_uses_a_short_connect_timeout():
    "A dead/unreachable Pi shouldn't make callers wait through the shared session's\
    default 30s connect timeout -- fail fast instead."
    session = _make_session(200, body=b"\x89PNG...")

    asyncio.run(fetch_screenshot(session, "abc-123", base_url="http://pi:8731"))

    _args, kwargs = session.get.call_args
    timeout = kwargs["timeout"]
    assert timeout.sock_connect == CONNECT_TIMEOUT_SECONDS


def test_fetch_screenshot_raises_screenshot_error_on_connection_failure():
    session = _make_session(200, body=b"\x89PNG...")
    session.get.return_value.__aenter__ = AsyncMock(
        side_effect=aiohttp.ClientConnectionError("Connection refused")
    )

    try:
        asyncio.run(fetch_screenshot(session, "abc-123", base_url="http://pi:8731"))
        assert False, "expected ScreenshotError"
    except ScreenshotError as e:
        assert "unreachable" in str(e).lower()


def test_fetch_screenshot_raises_screenshot_error_on_connect_timeout():
    session = _make_session(200, body=b"\x89PNG...")
    session.get.return_value.__aenter__ = AsyncMock(side_effect=TimeoutError())

    try:
        asyncio.run(fetch_screenshot(session, "abc-123", base_url="http://pi:8731"))
        assert False, "expected ScreenshotError"
    except ScreenshotError as e:
        assert "unreachable" in str(e).lower()


def test_fetch_screenshot_raises_on_non_200_status():
    session = _make_session(504, text="page did not render in time")

    try:
        asyncio.run(fetch_screenshot(session, "abc-123", base_url="http://pi:8731"))
        assert False, "expected ScreenshotError"
    except ScreenshotError as e:
        assert "504" in str(e)
        assert "page did not render in time" in str(e)


def test_fetch_screenshot_returns_timing_headers_on_success():
    session = _make_session(
        200,
        body=b"\x89PNG...",
        headers={
            "X-Timing-Warmup": "2.00",
            "X-Timing-Page-Load": "1.50",
            "Content-Type": "image/png",
        },
    )

    _image_bytes, timings = asyncio.run(
        fetch_screenshot(session, "abc-123", base_url="http://pi:8731")
    )

    assert timings == {"X-Timing-Warmup": "2.00", "X-Timing-Page-Load": "1.50"}
