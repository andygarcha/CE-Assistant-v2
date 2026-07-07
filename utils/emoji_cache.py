"""Resolves custom Discord emoji markup (e.g. <:tier1:123>) to a locally
cached PNG file, downloading from Discord's CDN on first use."""

import logging
import re
from pathlib import Path

from Modules import http_session

logger = logging.getLogger(__name__)

CACHE_DIR = Path("Assets/emoji_cache")

_EMOJI_PATTERN = re.compile(r"^<a?:\w+:(\d+)>$")


def parse_emoji_id(emoji_markup: str) -> str | None:
    """Extracts the numeric ID out of a `<:name:id>` or `<a:name:id>` emoji string."""
    match = _EMOJI_PATTERN.match(emoji_markup)
    if match is None:
        return None
    return match.group(1)


async def get_cached_emoji_path(
    emoji_markup: str, cache_dir: Path = CACHE_DIR
) -> Path | None:
    """Returns the local path to `emoji_markup`'s PNG, downloading and
    caching it first if this is the first time it's been requested.
    Returns None if the markup can't be parsed or the download fails."""
    emoji_id = parse_emoji_id(emoji_markup)
    if emoji_id is None:
        logger.error("Could not parse emoji ID out of %r", emoji_markup)
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / f"{emoji_id}.png"
    if cached_path.exists():
        return cached_path

    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
    try:
        session = await http_session.get_session()
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(
                    "Failed to download emoji %s: HTTP %s", emoji_id, response.status
                )
                return None
            data = await response.read()
    except Exception:
        logger.exception("Failed to download emoji %s", emoji_id)
        return None

    cached_path.write_bytes(data)
    return cached_path
