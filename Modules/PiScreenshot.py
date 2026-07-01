import json

import aiohttp

with open("secret_info.json") as f:
    _secret_info = json.load(f)

SCREENSHOT_SERVICE_URL: str = _secret_info.get("pi_screenshot_url", "")


class ScreenshotError(Exception):
    "Raised when the pi screenshot service fails to produce an image."


async def fetch_screenshot(
    session: aiohttp.ClientSession,
    game_id: str,
    base_url: str = SCREENSHOT_SERVICE_URL,
) -> tuple[bytes, dict[str, str]]:
    "Fetches a game's screenshot PNG bytes and its X-Timing-* headers from the pi screenshot service."
    url = f"{base_url}/screenshot/{game_id}"
    async with session.get(url) as response:
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
