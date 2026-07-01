import json
import urllib.request

API_TIMEOUT_SECONDS = 10


def fetch_game_json(game_id: str) -> dict:
    "Fetches a game's full JSON payload (including objectives) from cedb.me's API."
    url = f"https://cedb.me/api/game/{game_id}"
    with urllib.request.urlopen(url, timeout=API_TIMEOUT_SECONDS) as response:
        return json.loads(response.read())


def find_objective_name(game_json: dict, objective_id: str) -> str | None:
    "Returns the current display name of an objective by id, or None if not found."
    for objective in game_json.get("objectives", []):
        if objective.get("id") == objective_id:
            return objective.get("name")
    return None


def xpath_literal(value: str) -> str:
    "Builds a safe XPath string literal for `value`, even if it contains both quote types."
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


def build_diff_row_xpath(objective_name: str) -> str:
    "Builds an XPath expression matching the `<tr>` containing an objective's title."
    return f"//tr[.//h3[contains(., {xpath_literal(objective_name)})]]"
