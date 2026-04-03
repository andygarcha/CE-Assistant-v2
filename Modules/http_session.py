import asyncio

import aiohttp

_DEFAULT_HEADERS = {"User-Agent": "andy's-super-duper-bot/0.1"}
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)

_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:
    """Returns a shared aiohttp session for the whole process."""
    global _session

    if _session is not None and not _session.closed:
        return _session

    async with _session_lock:
        if _session is None or _session.closed:
            _session = aiohttp.ClientSession(
                headers=_DEFAULT_HEADERS,
                timeout=_DEFAULT_TIMEOUT,
            )
    return _session


async def close_session() -> None:
    """Closes the shared session if it exists."""
    global _session

    if _session is not None and not _session.closed:
        await _session.close()
    _session = None
