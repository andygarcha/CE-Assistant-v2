from typing import Callable

_PREFIX = "/screenshot/"


def parse_game_id(path: str) -> str | None:
    "Extracts the game id from a `/screenshot/<id>` path, or None if the path doesn't match."
    if not path.startswith(_PREFIX):
        return None

    game_id = path[len(_PREFIX) :]
    return game_id or None


def build_response(
    game_id: str | None, capture: Callable[[str], bytes]
) -> tuple[int, str, bytes]:
    "Maps a parsed game id + the capture call's outcome to an HTTP status/content-type/body."
    if game_id is None:
        return 400, "text/plain", b"missing game id"

    try:
        image_bytes = capture(game_id)
        return 200, "image/png", image_bytes
    except TimeoutError as e:
        return 504, "text/plain", str(e).encode()
    except Exception as e:
        return 500, "text/plain", str(e).encode()
