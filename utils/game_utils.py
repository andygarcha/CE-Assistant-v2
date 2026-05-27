import random
from typing import Literal, get_args, TYPE_CHECKING
from utils.general_utils import get_item_from_list
from Modules import http_session
import logging

if TYPE_CHECKING:
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser


def get_banned_games() -> list[str] | None:
    "Returns the list of CE IDs of banned rollable games."
    import Modules.SpreadsheetHandler as SpreadsheetHandler

    BANNED_GAMES = SpreadsheetHandler.get_sheet_data(
        SpreadsheetHandler.CE_SHEET_BANNED_GAMES_RANGE, SpreadsheetHandler.CE_SHEET_ID
    )
    if BANNED_GAMES is None:
        return None
    # Returns as [CE ID, Game Name, Reason]

    banned_games_ids = []

    for item in BANNED_GAMES:
        banned_games_ids.append(item[0])
    return banned_games_ids


async def get_rollable_game(
    database_name: list[CEGame],
    database_tier: dict,
    completion_limit: int | None,
    price_limit: int | None,
    tier_number: int,
    user: list[CEUser] | CEUser,
    category: str | list[str] | None = None,
    already_rolled_games: list = [],
    has_points_restriction: bool = False,
    price_restriction: bool = True,
    hours_restriction: bool = True,
) -> str | None:
    """Takes in a slew of parameters and returns a `str` of
    Challenge Enthusiast ID that match the criteria.
    """
    # fix the problem with multiple categories (this is super gross)
    if isinstance(category, str):
        category = [category]
    if isinstance(user, CEUser):
        user = [user]

    # NOTE: if tier_number == 6, then we need to be able to roll any t5, t6, or t7.

    database_tier_games: list[dict] = []
    # YES category and YES tier (tier != 6)
    if category is not None and tier_number is not None and tier_number != 6:
        for _cat in category:
            database_tier_games = database_tier[str(tier_number)][_cat]
    # YES category and YES tier (tier == 6)
    elif category is not None and tier_number == 6:
        for c in category:
            for t in range(5, 8):
                database_tier_games = database_tier[str(t)][c]
    # YES category but NO tier
    elif category is not None and tier_number is None:
        for c in category:
            for tn in range(1, 8):
                database_tier_games.extend(database_tier[str(tn)][c])
    # NO category and YES tier (tier != 6)
    elif category is None and tier_number is not None and tier_number != 6:
        for c in get_args(CATEGORIES):
            database_tier_games.extend(database_tier[str(tier_number)][c])
    # NO category and YES tier (tier == 6)
    elif category is None and tier_number == 6:
        for c in get_args(CATEGORIES):
            for t in range(5, 8):
                database_tier_games = database_tier[str(t)][c]
    # NO category and NO tier
    else:
        for tn in range(1, 8):
            for c in get_args(CATEGORIES):
                database_tier_games.extend(database_tier[str(tn)][c])

    random.shuffle(database_tier_games)

    # get banned games
    try:
        banned_games = get_banned_games()
    except Exception as e:
        logging.exception(e)
        return None

    """
    Requirements to check:
    - is on steam # done already
    - correct category # done already
    - correct tier # done already
    - game not banned # accounted for
    - if points_restriction, player doesn't have points in game # accounted for
    - if multiple users, no one has completed the game # accounted for
    - if one user, user has not completed game # accounted for
    - game hasn't already been rolled # accounted for
    - game doesn't have an uncleared # accounted for
    - if price_restriction... # accounted for
        - price is less than price_limit
        - OR 
        - user owns game
    - if hours_restriction, sh median completion time is less than hour_limit # accounted for
    """

    for game in database_tier_games:
        # banned
        if game["ce_id"] in banned_games:
            continue

        # already rolled
        if game["ce_id"] in already_rolled_games:
            continue

        # has uncleared
        __game_object = get_item_from_list(game["ce_id"], database_name)
        if __game_object is None or __game_object.has_uncleared:
            continue

        # has points
        if has_points_restriction:
            fails = False
            for _user in user:
                if _user.has_points(game["ce_id"]):
                    fails = True
                    break
            if fails:
                continue

        # too pricey
        if price_restriction and price_limit is not None:
            if not game["price"] <= (price_limit * 100):
                fails = False
                for _user in user:
                    if not _user.owns_game(game["ce_id"]):
                        fails = True
                        break
                if fails:
                    continue

        # too many hours
        if hours_restriction and completion_limit is not None:
            if game["sh_hours"] > (completion_limit * 60):
                continue

        # already completed
        fails = False
        for _user in user:
            if _user.has_completed_game(game["ce_id"], database_name):
                fails = True
                break
        if fails:
            continue

        return game["ce_id"]

    return None


async def name_to_steamid(name: str) -> str:
    "Takes in the name of a game and returns the Steam App ID associated with it."

    # -- check CE first --
    import Modules.SupabaseReader as SupabaseReader

    database_name = SupabaseReader.get_database_name()
    for game in database_name:
        if game.game_name.lower() == name.lower() and game.platform == "steam":
            return game.platform_id

    # -- now check steam instead --
    payload = {"term": name, "cc": "US"}
    session = await http_session.get_session()
    async with session.get(
        "https://store.steampowered.com/api/storesearch/?", params=payload
    ) as response:
        json_response = await response.json()

        # look through all the games
        for item in json_response["items"]:
            if item["name"].lower() == name.lower():
                return item["id"]

        # if no exact match is found, return the first one
        return json_response["items"][0]["id"]


CATEGORY_NAMES = {
    "3c3fd562-525c-4e24-a1fa-5b5eda85ebbd": "Platformer",
    "4d43349a-43a8-4755-9d52-41ece63ec5b1": "Action",
    "7f8676fe-4900-400b-9284-c073388d88f7": "Bullet Hell",
    "a6d00cc0-9481-47cb-bb52-a7011041915a": "First-Person",
    "ec499226-0913-4db1-890e-093b366bcb3c": "Arcade",
    "ffb558c1-5a45-4b8c-856c-e9622ce54f00": "Strategy",
    "00000000-0000-0000-0000-000000000000": "Total",
}


def genre_id_to_name(genre_id: str) -> str | None:
    return CATEGORY_NAMES.get(genre_id)


ALL_ROLL_EVENT_NAMES = Literal[
    "One Hell of a Day",
    "One Hell of a Week",
    "One Hell of a Month",
    "Two Week T2 Streak",
    'Two "Two Week T2 Streak" Streak',
    "Never Lucky",
    "Triple Threat",
    "Let Fate Decide",
    "Fourward Thinking",
    "Russian Roulette",
    "Destiny Alignment",
    "Soul Mates",
    "Teamwork Makes the Dream Work",
    "Winner Takes All",
    "Game Theory",
]
ALL_ROLL_EVENT_NAMES_TUPLE = get_args(ALL_ROLL_EVENT_NAMES)
SOLO_ROLL_EVENT_NAMES = Literal[
    "One Hell of a Day",
    "One Hell of a Week",
    "One Hell of a Month",
    "Two Week T2 Streak",
    'Two "Two Week T2 Streak" Streak',
    "Never Lucky",
    "Triple Threat",
    "Let Fate Decide",
    "Fourward Thinking",
]
SOLO_ROLL_EVENT_NAMES_TUPLE = get_args(SOLO_ROLL_EVENT_NAMES)
COOP_ROLL_EVENT_NAMES = Literal[
    "Destiny Alignment",
    "Soul Mates",
    "Teamwork Makes the Dream Work",
    "Winner Takes All",
    "Game Theory",
]
COOP_ROLL_EVENT_NAMES_TUPLE = get_args(COOP_ROLL_EVENT_NAMES)
MULTI_STAGE_ROLLS = Literal[
    "Two Week T2 Streak", 'Two "Two Week T2 Streak" Streak', "Fourward Thinking"
]
MULTI_STAGE_ROLLS_TUPLE = get_args(MULTI_STAGE_ROLLS)
PVP_ROLL_EVENT_NAMES = Literal["Winner Takes All", "Game Theory"]
PVP_ROLL_EVENT_NAMES_TUPLE = get_args(PVP_ROLL_EVENT_NAMES)


OBJECTIVE_TYPES = Literal["Primary", "Secondary", "Badge", "Community"]
PLATFORM_NAMES = Literal["steam", "retroachievements"]

CATEGORIES = Literal[
    "Action", "Arcade", "Bullet Hell", "First-Person", "Platformer", "Strategy"
]


def achievements_are_equal(
    old_achievements: list[str] | None, new_achievements: list[str] | None
) -> bool:
    "Returns true if the achievements are equal, false if they're not."
    if old_achievements is None or new_achievements is None:
        return old_achievements is new_achievements is None

    return set(old_achievements) == set(new_achievements)
