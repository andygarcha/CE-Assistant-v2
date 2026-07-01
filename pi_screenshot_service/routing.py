from typing import Callable

_PREFIX = "/screenshot/"

_TIMING_HEADER_NAMES = {
    "warmup": "X-Timing-Warmup",
    "page_load": "X-Timing-Page-Load",
    "render": "X-Timing-Render",
    "screenshot": "X-Timing-Screenshot",
}


def parse_game_id(path: str) -> str | None:
    "Extracts the game id from a `/screenshot/<id>` path, or None if the path doesn't match."
    if not path.startswith(_PREFIX):
        return None

    game_id = path[len(_PREFIX) :]
    return game_id or None


def build_response(
    game_id: str | None,
    capture: Callable[[str], tuple[bytes, dict[str, float]]],
) -> tuple[int, str, bytes, dict[str, str]]:
    "Maps a parsed game id + the capture call's outcome to an HTTP status/content-type/body/headers."
    if game_id is None:
        return 400, "text/plain", b"missing game id", {}

    try:
        image_bytes, timings = capture(game_id)
        headers = {
            _TIMING_HEADER_NAMES[phase]: f"{seconds:.2f}"
            for phase, seconds in timings.items()
            if phase in _TIMING_HEADER_NAMES
        }
        return 200, "image/png", image_bytes, headers
    except TimeoutError as e:
        return 504, "text/plain", str(e).encode(), {}
    except Exception as e:
        return 500, "text/plain", str(e).encode(), {}
