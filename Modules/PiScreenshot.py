import json
from urllib.parse import quote

import aiohttp

with open("secret_info.json") as f:
    _secret_info = json.load(f)

SCREENSHOT_SERVICE_URL: str = _secret_info.get("pi_screenshot_url", "")

# The shared aiohttp session (Modules/http_session.py) defaults to a 30s connect
# timeout, meant for third-party APIs. If the Pi itself is offline (not just its
# screenshot service), that leaves callers hanging for 30s before finding out.
# Fail fast here instead; a live tailnet peer connects in well under this.
CONNECT_TIMEOUT_SECONDS = 5
# Generous read/total timeout so a real, slow-but-alive capture isn't cut off.
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(sock_connect=CONNECT_TIMEOUT_SECONDS, total=40)


class ScreenshotError(Exception):
    "Raised when the pi screenshot service fails to produce an image."


async def _get_image_response(
    session: aiohttp.ClientSession, url: str
) -> tuple[bytes, dict[str, str]]:
    "Shared GET + error-translation + timing-header extraction for both screenshot endpoints."
    try:
        async with session.get(url, timeout=_REQUEST_TIMEOUT) as response:
            if response.status != 200:
                body = await response.text()
                raise ScreenshotError(
                    f"screenshot service returned {response.status}: {body}"
                )
            image_bytes = await response.read()
            timings = {
                key: value
                for key, value in response.headers.items()
                if key.startswith("X-Timing-")
            }
            return image_bytes, timings
    except (aiohttp.ClientError, TimeoutError) as e:
        raise ScreenshotError(f"screenshot service unreachable: {e}") from e


async def fetch_screenshot(
    session: aiohttp.ClientSession,
    game_id: str,
    base_url: str = SCREENSHOT_SERVICE_URL,
) -> tuple[bytes, dict[str, str]]:
    "Fetches a game's screenshot PNG bytes and its X-Timing-* headers from the pi screenshot service."
    return await _get_image_response(session, f"{base_url}/screenshot/{game_id}")


async def fetch_diff_screenshot(
    session: aiohttp.ClientSession,
    game_id: str,
    objective_id: str,
    old_text: str,
    new_text: str,
    base_url: str = SCREENSHOT_SERVICE_URL,
) -> tuple[bytes, dict[str, str]]:
    "Fetches a diff-highlighted screenshot of one changed objective from the pi screenshot service."
    url = (
        f"{base_url}/screenshot-diff/{game_id}/{objective_id}"
        f"?old={quote(old_text)}&new={quote(new_text)}"
    )
    return await _get_image_response(session, url)
