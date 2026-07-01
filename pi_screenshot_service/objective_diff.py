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


DIFF_HIGHLIGHT_JS = """
function findTextNode(node, needle) {
    if (node.nodeType === 3 && node.textContent.includes(needle)) {
        return node;
    }
    for (const child of node.childNodes) {
        const found = findTextNode(child, needle);
        if (found) return found;
    }
    return null;
}

const root = arguments[0];
const oldText = arguments[1];
const newText = arguments[2];

const textNode = findTextNode(root, newText);
if (!textNode) {
    return false;
}

const idx = textNode.textContent.indexOf(newText);
const before = textNode.textContent.slice(0, idx);
const after = textNode.textContent.slice(idx + newText.length);

const oldSpan = document.createElement('span');
oldSpan.textContent = oldText;
oldSpan.style.textDecoration = 'line-through';
oldSpan.style.color = 'red';

const arrowSpan = document.createElement('span');
arrowSpan.textContent = ' \\u2192 ';
arrowSpan.style.color = 'white';
arrowSpan.style.fontWeight = 'bold';

const newSpan = document.createElement('span');
newSpan.textContent = newText;

const parent = textNode.parentNode;
parent.insertBefore(document.createTextNode(before), textNode);
parent.insertBefore(oldSpan, textNode);
parent.insertBefore(arrowSpan, textNode);
parent.insertBefore(newSpan, textNode);
parent.insertBefore(document.createTextNode(after), textNode);
parent.removeChild(textNode);

return true;
"""


def inject_diff_highlight(driver, root_element, old_text: str, new_text: str) -> bool:
    "Injects a strikethrough-red old value + arrow + new value in place of `new_text` inside `root_element`. Returns whether `new_text` was found."
    return driver.execute_script(DIFF_HIGHLIGHT_JS, root_element, old_text, new_text)
