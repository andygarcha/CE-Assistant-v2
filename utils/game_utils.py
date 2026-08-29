from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Literal, NamedTuple, get_args

from Modules import http_session
from utils.general_utils import get_item_from_list

if TYPE_CHECKING:
    from collections.abc import Sequence

    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser
    from Classes.CE_User_Game import CEUserGame


def get_rollable_game(
    database_name: list[CEGame],
    database_tier: dict,
    completion_limit: int | None,
    price_limit: int | None,
    tier_number: int | None,
    user: list[CEUser] | CEUser,
    category: str | list[str] | None = None,
    already_rolled_games: list | None = None,
    has_points_restriction: bool = False,
    price_restriction: bool = True,
    hours_restriction: bool = True,
    allow_multi_category: bool = True,
) -> str | None:
    """
    Takes in a slew of parameters and returns a `str` of
    Challenge Enthusiast ID that match the criteria.

    Returns
    ---
    - If a game is chosen, this will return that game's CE ID.
    - If a game is unable to be chosen, this will return None.

    Disallowed Games
    ---
    - games that are not on Steam
    - games that are in the BANNED_GAMES array
    - games that any of the passed-in users have completed
    - games that have an uncleared primary objective

    Parameters
    ---
    database_name : `list[CEGame]`
        A list of all games in the site.
        This is *NOT* the list of games this function will loop through...
        ... that is database_tier. However, if you would like
        to limit the amount of rollable games, you can only send in
        games you'd like to be rolled.
    database_tier: `list[dict]`
        A mapping of game_ids, price, and average completion time.
        This is the list of games that this function will loop through.
        Example: database_tier[category][tier] = list[dict]
        Keys: 'ce_id', 'price', 'sh_hours'.
    completion_limit: `int | None`
        The (exclusive) upper limit of a game's allowed average completion time.
        If this is None, there is no upper limit.
    price_limit: `int | None`
        The (exclusive) upper limit of a game's allowed price.
        If this is None, there is no upper limit.
    tier_number: `int | None`
        The tier a chosen game must be.
        If this is None, there is no required tier.
        If this is 6, any game T5-T7 may be chosen.
    user: `CEUser | list[CEUser]`
        The user(s) who are requesting this roll.
        This is to filter out games that have already been completed.
    category: `str | list[str] | None`
        The category (or categories) a chosen game must be.
        If this is None, there is no required category.
    already_rolled_games: `list[str]`
        A list of games that are to be excluded from the search.
    has_points_restriction: `bool`
        A boolean flag that, if set to True,
        disallows any game that rolling users currently have points in.
    price_restriction: `bool`
        A boolean flag that, if set to True,
        requires the search to adhere to the chosen price limit.
    hours_restriction: `bool`
        A boolean flag that, if set to True,
        requires the search to adhere to the chosen completion time limit.
    allow_multi_category: `bool`
        A boolean flag that, if set to True,
        allows a multi-category game to be chosen.
        This would be turned off for events like 'One Hell of a Week',
        which requires all five games to be different categories.
    """

    from Classes.CE_User import CEUser

    # fix the problem with multiple categories (this is super gross)
    if isinstance(category, str):
        category = [category]
    if isinstance(user, CEUser):
        user = [user]

    if already_rolled_games is None:
        already_rolled_games = []

    # NOTE: if tier_number == 6, then we need to be able to roll any t5, t6, or t7.

    database_tier_games: list[dict] = []
    # YES category and YES tier (tier != 6)
    if category is not None and tier_number is not None and tier_number != 6:
        for _cat in category:
            database_tier_games.extend(database_tier[str(tier_number)][_cat])
    # YES category and YES tier (tier == 6)
    elif category is not None and tier_number == 6:
        for c in category:
            for t in range(5, 8):
                database_tier_games.extend(database_tier[str(t)][c])
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
                database_tier_games.extend(database_tier[str(t)][c])
    # NO category and NO tier
    else:
        for tn in range(1, 8):
            for c in get_args(CATEGORIES):
                database_tier_games.extend(database_tier[str(tn)][c])

    secrets.SystemRandom().shuffle(database_tier_games)

    # get banned games
    try:
        from Modules import SupabaseReader

        banned_games = [g["game_id"] for g in SupabaseReader.get_banned_games()]
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

        # allows_multi_category
        if not allow_multi_category and len(__game_object.categories) != 1:
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
        if (
            price_restriction
            and price_limit is not None
            and game["price"] > (price_limit * 100)
        ):
            fails = False
            for _user in user:
                if not _user.owns_game(game["ce_id"]):
                    fails = True
                    break
            if fails:
                continue

        # too many hours
        if (
            hours_restriction
            and completion_limit is not None
            and game["sh_hours"] > (completion_limit * 60)
        ):
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
]
COOP_ROLL_EVENT_NAMES_TUPLE = get_args(COOP_ROLL_EVENT_NAMES)
MULTI_STAGE_ROLLS = Literal[
    "Two Week T2 Streak", 'Two "Two Week T2 Streak" Streak', "Fourward Thinking"
]
MULTI_STAGE_ROLLS_TUPLE = get_args(MULTI_STAGE_ROLLS)


OBJECTIVE_TYPES = Literal["Primary", "Secondary", "Badge", "Community"]
PLATFORM_NAMES = Literal["steam", "retroachievements"]

CATEGORIES = Literal[
    "Action", "Arcade", "Bullet Hell", "First-Person", "Platformer", "Strategy"
]

GAME_ID_CHALLENGE_ENTHUSIASTS = "76574ec1-42df-4488-a511-b9f2d9290e5d"
GAME_ID_CLOWN_TOWN = "09f100aa-caa7-4154-a224-1c3e9277eea4"


def achievements_are_equal(
    old_achievements: list[str] | None, new_achievements: list[str] | None
) -> bool:
    "Returns true if the achievements are equal, false if they're not."
    if old_achievements is None or new_achievements is None:
        return old_achievements is None and new_achievements is None

    return set(old_achievements) == set(new_achievements)


# ==== role point thresholds ====

TIER_COUNT = 7
CATEGORY_COUNT = 6

ENTHUSIAST_POINTS_PER_TIER = 500
"Tier N Enthusiast requires N * 500 points, for tiers 1 through 4."

ENTHUSIAST_T5_PLUS_THRESHOLD = 2500
"Tier 5 Enthusiast requires 2500 points across Tier 5, 6 and 7 games combined."


class RolePoints(NamedTuple):
    """
    The points a user has accrued toward tier- and category-based Discord roles.

    tiers: 7 entries, where index 0 is Tier 1 and index 6 is Tier 7.
    categories: 6 entries, ordered Action, Arcade, Bullet Hell, First-Person,
    Platformer, Strategy (matching `CEGame.categories_num`).
    """

    tiers: list[int]
    categories: list[int]


def compute_role_points(
    games: Sequence[CEUserGame], database_name: Sequence[CEGame]
) -> RolePoints:
    """
    Totals up the points a user has earned toward their tier and category roles.

    Tier points only count games where the user has finished every Primary
    Objective. Which tier bucket such a game lands in is decided by what the
    user actually *earned* in it -- their POs plus any Secondary Objectives
    they also finished -- so completing an SO can lift a game into a higher
    tier than its POs alone would reach. A game worth 75 PO points is a Tier 3
    on its own, but a user who also clears a 10 point SO has earned 85, which
    counts for them as a Tier 4.

    A game the user hasn't finished the POs of contributes no tier points at
    all. Category points, by contrast, don't care about completion.

    Parameters
    ---
    games: `Sequence[CEUserGame]`
        The games this user owns.
    database_name: `Sequence[CEGame]`
        The game database to look each owned game up in. Games that aren't
        present are skipped.
    """
    from Classes.CE_Game import tier_for_points

    tiers = [0] * TIER_COUNT
    categories = [0] * CATEGORY_COUNT

    games_by_ce_id: dict[str, CEGame] = {game.ce_id: game for game in database_name}

    for game in games:
        game_database = games_by_ce_id.get(game.ce_id)

        if game_database is None:
            continue

        # is_completed covers "every PO done"; is_overcompleted additionally
        # covers games that have no POs at all, where clearing every SO is
        # what counts as finishing them.
        if game.is_completed(game_database) or game.is_overcompleted(game_database):
            earned = game.user_points

            # Points below the Tier 1 threshold belong to no tier, and
            # tier_for_points returns 0 for them. Indexing tiers[0 - 1] would
            # wrap around to the Tier 7 slot, so they're skipped instead.
            tier_num = tier_for_points(earned)
            if tier_num > 0:
                tiers[tier_num - 1] += earned

        # category roles don't care about completion
        # PO points only?
        for c_num in game_database.categories_num:
            categories[c_num - 1] += game.user_points

    return RolePoints(tiers=tiers, categories=categories)


def t5_plus_points(tiers: Sequence[int]) -> int:
    """
    Returns the points earned in completed Tier 5 and above games, which is
    what Tier 5 Enthusiast is measured against. Tiers 5, 6 and 7 live at
    indices 4, 5 and 6 of a `RolePoints.tiers` list.
    """
    return sum(tiers[4:])
