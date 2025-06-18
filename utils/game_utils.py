import random
from typing import Literal

import aiohttp


def get_banned_games() -> list[str] :
    "Returns the list of CE IDs of banned rollable games."
    import Modules.SpreadsheetHandler as SpreadsheetHandler

    BANNED_GAMES = SpreadsheetHandler.get_sheet_data(SpreadsheetHandler.CE_SHEET_BANNED_GAMES_RANGE, 
                                                     SpreadsheetHandler.CE_SHEET_ID)
    "Returns as [CE ID, Game Name, Reason]"

    banned_games_ids = []

    for item in BANNED_GAMES :
        banned_games_ids.append(item[0])
    return banned_games_ids





async def get_rollable_game(
        database_name : list,
        completion_limit : int,
        price_limit : int,
        tier_number : int,
        user,
        category : str | list[str] = None,
        already_rolled_games : list = [],
        has_points_restriction : bool = False,
        price_restriction : bool = True,
        hours_restriction : bool = True
):
    """Takes in a slew of parameters and returns a `str` of 
    Challenge Enthusiast ID that match the criteria.
    """
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser

    # avoid circular imports
    database_name : list[CEGame] = database_name
    user : CEUser | list[CEUser] = user

    # turn this on to see what's happening
    VIEW_CONSOLE_MESSAGES = True

    if VIEW_CONSOLE_MESSAGES :
        print("get_rollable_game() called with the following parameters: ")
        print(f"database_name: {'passed correctly' if (database_name is not None or len(database_name) == 0) else '!!! passed incorrectly !!!'}")
        print(f"completion limit: {completion_limit}")
        print(f"price_limit: {price_limit}")
        print(f"tier_number: {tier_number}")
        if (type(user) != list) :
            print(f"user: {user.ce_id}")
        else :
            print(f"users: {[u.ce_id for u in user]}")
        print(f"category: {category}")
        print(f"already_rolled_games: {already_rolled_games}")
        print(f"has_points_restriction: {has_points_restriction}")
        print(f"price_restriction: {price_restriction}")
        print(f"hours_restriction: {hours_restriction}")

    # randomize database_name :
    random.shuffle(database_name)

    # get banned games
    try :
        banned_games = get_banned_games()
    except :
        return None

    # if only one category was sent, put it in an array so we can use `in`.
    if type(category) == str :
        category = [category]

    # if the hours restriction was turned off, we can just set completion_limit to None so that everything gets rolled!
    if not hours_restriction :
        completion_limit = None

    # ---- iterate through all the games ----
    for game in database_name :
        if VIEW_CONSOLE_MESSAGES: print(f"evaluating {game.name_with_link()}... ", end="")
        if category != None and game.category not in category :
            "Incorrect category."
            if VIEW_CONSOLE_MESSAGES: print("Incorrect category.")
            continue

        if game.platform != "steam" :
            "Non-steam game."
            if VIEW_CONSOLE_MESSAGES: print("Non-steam game.")
            continue

        """
        if game.is_unfinished() :
            "Game is currently under construction."
            continue
        """

        if tier_number == 6 and not game.is_t5plus() :
            "Incorrect tier."
            if VIEW_CONSOLE_MESSAGES: print("Requested a T6 and did not get one.")
            continue
        
        if tier_number != None and game.get_tier() != f"Tier {tier_number}" :
            "Incorrect tier."
            if VIEW_CONSOLE_MESSAGES: print("Incorrect tier.")
            continue
        
        if (type(user) is list) :
            "If there's more than one user..."
            must_continue = False
            for u in user :
                "...one of them has completed the game."
                if u.has_completed_game(game.ce_id, database_name) : 
                    if VIEW_CONSOLE_MESSAGES : print("Multiple users passed, and one of them has completed this game.")
                    must_continue = True
            if must_continue : continue

        else :
            "User has completed the game already."
            if user.has_completed_game(game.ce_id, database_name) : 
                if VIEW_CONSOLE_MESSAGES : print("One user passed, and they have already completed this game.")
                continue


        if game.ce_id in already_rolled_games :
            "This game has already been rolled."
            if VIEW_CONSOLE_MESSAGES : print("Game has already been rolled.")
            continue

        if game.has_an_uncleared() :
            "This game has an uncleared objective."
            if VIEW_CONSOLE_MESSAGES : print("Has an uncleared.")
            continue

        price = await game.get_price_async()
        if price_restriction and price is not None and price > price_limit :
            if type(user) is list :
                "If there's more than one user..."
                must_continue = False
                for u in user :
                    "One of the users doesn't own the game."
                    if not u.owns_game(game.ce_id) : 
                        if VIEW_CONSOLE_MESSAGES : print("The price is too high and one of the user's doesn't own the game.")
                        must_continue = True
                if must_continue : continue
            else :
                if not user.owns_game(game.ce_id) : 
                    if VIEW_CONSOLE_MESSAGES : print("The price is too high, and the user doesn't own the game.")
                    continue
            "The price is too high (and the price is restricted) and the user doesn't own the game."

        sh_data = await game.get_steamhunters_data_async()
        if completion_limit is not None and (sh_data == None or sh_data > completion_limit) :
            "The SteamHunters median-completion-time is too high."
            if VIEW_CONSOLE_MESSAGES: print(f"The steamhunters median completion time was {sh_data}")
            continue

        if game.ce_id in banned_games :
            "This game is in the Banned Games section."
            if VIEW_CONSOLE_MESSAGES: print("Game is banned.")
            continue
        
        if has_points_restriction :
            "If the user isn't allowed to have points in the game..."
            if type(user) is list :
                "One of the users passed has points in the game."
                must_continue = False
                for u in user :
                    if u.has_points(game.ce_id) : 
                        if VIEW_CONSOLE_MESSAGES: print("One of the passed users has points in the game.")
                        must_continue = True
                if must_continue : continue
            else :
                "The user passed has points in the game."
                if user.has_points(game.ce_id) : 
                    if VIEW_CONSOLE_MESSAGES : print("The user has points in this game.")
                    continue

        if VIEW_CONSOLE_MESSAGES : print("Passed!!!")
        return game.ce_id
    
    return None




async def name_to_steamid(name : str) -> str :
    "Takes in the name of a game and returns the Steam App ID associated with it."

    # -- check CE first --
    import Modules.Mongo_Reader as Mongo_Reader
    database_name = await Mongo_Reader.get_database_name()
    for game in database_name :
        if game.game_name.lower() == name.lower() and game.platform == "steam" : return game.platform_id
    
    # -- now check steam instead --
    payload = {"term" : name, "cc" : "US"}
    async with aiohttp.ClientSession() as session :
        async with session.get("https://store.steampowered.com/api/storesearch/?", params=payload) as response :
            json_response = await response.json()

            # look through all the games
            for item in json_response['items'] :
                if item['name'].lower() == name.lower() : return item['id']
            
            # if no exact match is found, return the first one
            return json_response['items'][0]['id']



def genre_id_to_name(genre_id : str) -> str :
    match(genre_id) :
        case "3c3fd562-525c-4e24-a1fa-5b5eda85ebbd" : return "Platformer"
        case "4d43349a-43a8-4755-9d52-41ece63ec5b1" : return "Action"
        case "7f8676fe-4900-400b-9284-c073388d88f7" : return "Bullet Hell"
        case "a6d00cc0-9481-47cb-bb52-a7011041915a" : return "First-Person"
        case "ec499226-0913-4db1-890e-093b366bcb3c" : return "Arcade"
        case "ffb558c1-5a45-4b8c-856c-e9622ce54f00" : return "Strategy"
        case "00000000-0000-0000-0000-000000000000" : return "Total"
        case _ : return None



ALL_ROLL_EVENT_NAMES = Literal["One Hell of a Day", "One Hell of a Week", "One Hell of a Month",
                        "Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak", "Never Lucky",
                        "Triple Threat", "Let Fate Decide", "Fourward Thinking", "Russian Roulette",
                        "Destiny Alignment", "Soul Mates", "Teamwork Makes the Dream Work", "Winner Takes All",
                        "Game Theory"]
SOLO_ROLL_EVENT_NAMES = Literal["One Hell of a Day", "One Hell of a Week", "One Hell of a Month",
                        "Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak", "Never Lucky",
                        "Triple Threat", "Let Fate Decide", "Fourward Thinking"]
COOP_ROLL_EVENT_NAMES = Literal["Destiny Alignment", "Soul Mates", "Teamwork Makes the Dream Work", "Winner Takes All",
                        "Game Theory"]
MULTI_STAGE_ROLLS = Literal["Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak", "Fourward Thinking"]
PVP_ROLL_EVENT_NAMES = Literal["Winner Takes All", "Game Theory"]



OBJECTIVE_TYPES = Literal["Primary", "Secondary", "Badge", "Community"]
PLATFORM_NAMES = Literal['steam', 'retroachievements']

CATEGORIES = Literal['Action', 'Arcade', 'Bullet Hell', 'First-Person',
            'Platformer', 'Strategy']


def achievements_are_equal(old_achievements : list[str] | None, new_achievements : list[str] | None) -> bool :
    "Returns true if the achievements are equal, false if they're not."
    if old_achievements is None and new_achievements is not None : return False
    if old_achievements is not None and new_achievements is None : return False
    if old_achievements is None and new_achievements is None : return True
    return set(old_achievements) == set(new_achievements)