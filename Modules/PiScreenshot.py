import json

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


async def fetch_screenshot(
    session: aiohttp.ClientSession,
    game_id: str,
    base_url: str = SCREENSHOT_SERVICE_URL,
) -> tuple[bytes, dict[str, str]]:
    "Fetches a game's screenshot PNG bytes and its X-Timing-* headers from the pi screenshot service."
    url = f"{base_url}/screenshot/{game_id}"
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
