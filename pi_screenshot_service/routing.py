import json
from typing import Callable
from urllib.parse import parse_qs, urlsplit

_PREFIX = "/screenshot/"
_DIFF_PREFIX = "/screenshot-diff/"


def parse_game_id(path: str) -> str | None:
    "Extracts the game id from a `/screenshot/<id>` path, or None if the path doesn't match."
    if not path.startswith(_PREFIX):
        return None

    game_id = path[len(_PREFIX) :]
    return game_id or None


def parse_diff_request(path: str) -> tuple[str, str, str, str] | None:
    "Extracts (game_id, objective_id, old_text, new_text) from a diff-screenshot request path, or None if malformed."
    split = urlsplit(path)
    if not split.path.startswith(_DIFF_PREFIX):
        return None

    remainder = split.path[len(_DIFF_PREFIX) :]
    parts = remainder.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    game_id, objective_id = parts

    query = parse_qs(split.query)
    old_values = query.get("old")
    new_values = query.get("new")
    if not old_values or not new_values:
        return None

    return game_id, objective_id, old_values[0], new_values[0]


def _timing_headers(timings: dict[str, float]) -> dict[str, str]:
    "Turns a phase-name -> seconds dict into `X-Timing-<Phase-Name>` headers."
    headers = {}
    for phase, seconds in timings.items():
        header_name = "X-Timing-" + phase.replace("_", "-").title()
        headers[header_name] = f"{seconds:.2f}"
    return headers


def build_response(
    game_id: str | None,
    capture: Callable[[str], tuple[bytes, dict[str, float]]],
) -> tuple[int, str, bytes, dict[str, str]]:
    "Maps a parsed game id + the capture call's outcome to an HTTP status/content-type/body/headers."
    if game_id is None:
        return 400, "text/plain", b"missing game id", {}

    try:
        image_bytes, timings = capture(game_id)
        return 200, "image/png", image_bytes, _timing_headers(timings)
    except TimeoutError as e:
        return 504, "text/plain", str(e).encode(), {}
    except Exception as e:
        return 500, "text/plain", str(e).encode(), {}


def build_diff_response(
    parsed: tuple[str, str, str, str] | None,
    capture: Callable[[str, str, str, str], tuple[bytes, dict[str, float]]],
) -> tuple[int, str, bytes, dict[str, str]]:
    "Maps a parsed diff request + the capture call's outcome to an HTTP status/content-type/body/headers."
    if parsed is None:
        return 400, "text/plain", b"missing game id, objective id, old, or new", {}

    game_id, objective_id, old_text, new_text = parsed
    try:
        image_bytes, timings = capture(game_id, objective_id, old_text, new_text)
        return 200, "image/png", image_bytes, _timing_headers(timings)
    except TimeoutError as e:
        return 504, "text/plain", str(e).encode(), {}
    except ValueError as e:
        return 404, "text/plain", str(e).encode(), {}
    except Exception as e:
        return 500, "text/plain", str(e).encode(), {}


_REQUIRED_OBJECTIVE_KEYS = {"id", "name", "description", "points", "requirements", "type"}


def parse_game_diff_path(path: str) -> str | None:
    "Extracts the game id from a `/screenshot-diff/<game_id>` POST path, or None if malformed."
    if not path.startswith(_DIFF_PREFIX):
        return None
    game_id = path[len(_DIFF_PREFIX) :]
    if not game_id or "/" in game_id:
        return None
    return game_id


def parse_old_objectives_body(body: bytes) -> list[dict] | None:
    "Parses and validates the POST body as a list of old-objective snapshots, or None if malformed."
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    for entry in parsed:
        if not isinstance(entry, dict) or not _REQUIRED_OBJECTIVE_KEYS.issubset(entry.keys()):
            return None
    return parsed


def build_game_diff_response(
    game_id: str | None,
    old_objectives: list[dict] | None,
    capture: Callable[[str, list[dict]], tuple[bytes, dict[str, float]]],
) -> tuple[int, str, bytes, dict[str, str]]:
    "Maps a parsed game-diff POST request + the capture call's outcome to an HTTP status/content-type/body/headers."
    if game_id is None or old_objectives is None:
        return 400, "text/plain", b"missing game id or malformed old objectives body", {}

    try:
        image_bytes, timings = capture(game_id, old_objectives)
        return 200, "image/png", image_bytes, _timing_headers(timings)
    except TimeoutError as e:
        return 504, "text/plain", str(e).encode(), {}
    except ValueError as e:
        return 404, "text/plain", str(e).encode(), {}
    except Exception as e:
        return 500, "text/plain", str(e).encode(), {}
