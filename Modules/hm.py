"""
This module, named after my legendary friend ApolloTheOne (aka apollohm),
will house a bunch of random pieces of data that need to be accessed 
across multiple files.
"""

import calendar
import datetime
import time
from typing import Literal
import random
import requests
import json


__icons = {
    # tiers
    "Tier 0" : '<:tier0:1126268390605070426>',
    "Tier 1" : '<:tier1:1126268393725644810>',
    "Tier 2" : '<:tier2:1126268395483037776>',
    "Tier 3" : '<:tier3:1126268398561677364>',
    "Tier 4" : '<:tier4:1126268402596585524>',
    "Tier 5" : '<:tier5:1126268404781809756>',
    "Tier 6" : '<:tier6:1126268408116285541>',
    "Tier 7" : '<:tier7:1126268411220074547>',

    # categories
    "Action" : '<:CE_action:1126326215356198942>',
    "Arcade" : '<:CE_arcade:1126326209983291473>',
    "Bullet Hell" : '<:CE_bullethell:1126326205642190848>',
    "First-Person" : '<:CE_firstperson:1126326202102186034>',
    "Platformer" : '<:CE_platformer:1126326197983383604>',
    "Strategy" : '<:CE_strategy:1126326195915591690>',

    # others
    "Points" : '<:CE_points:1128420207329816597>',
    'Arrow' : '<:CE_arrow:1126293045315375257>',

    # ranks
    "A Rank" : '<:rank_a:1126268299504795658>',
    "B Rank" : '<:rank_b:1126268303480979517>',
    "C Rank" : '<:rank_c:1126268305083215913>',
    "D Rank" : '<:rank_d:1126268307813715999>',
    "E Rank" : '<:rank_e:1126268309730512947>',
    "S Rank" : '<:rank_s:1126268319855562853>',
    "SS Rank" : '<:rank_ss:1126268323089367200>',
    "SSS Rank" : '<:rank_sss:1126268324804833280>',
    "EX Rank" : '<:rank_ex:1126268312842666075>',
    "P Rank" : '<:rank_p:1126268315279564800>',
    "Q Rank" : '<:rank_q:1126268318081364128>',

    # miscellaneous
    "Casino" : '<:CE_casino:1128844342732263464>',
    "Diamond" : '<:CE_diamond:1126286987524051064>',
    "All" : '<:CE_all:1126326219332399134>',
    "Rank Omega" : '<:rank_omega:1126293063455756318>',
    "Hexagon" : '<:CE_hexagon:1126289532497694730>',
    "Site Dev" : '<:SiteDev:963835646538027018>',

    # reactions
    "Shake" : '<:shake:894912425869074462>',
    "Safety" : '<:safety:802615322858487838>',
    "Crown" : "<:crown:1289287905331777596>",

    # logos
    "steam" : '<:steam:1282856420827463730>',
    "retroachievements": "<:retroachievementslogo:1282856386228916285>"
}

__test_icons = {
    "Action" : "<:CE_action:1133558549990088734>",
    "Arcade" : "<:CE_arcade:1133558574287683635>",
    "Bullet Hell" : "<:CE_bullethell:1133558610530676757>",
    "First-Person" : "<:CE_firstperson:1133558611898015855>",
    "Platformer" : "<:CE_platformer:1133558613705769020>",
    "Points" : "<:CE_points:1133558614867587162>",
    "Strategy" : "<:CE_strategy:1133558616536915988>",

    "Tier 0" : "<:tier0:1133560874464985139>",
    "Tier 1" : "<:tier1:1133560876381773846>",
    "Tier 2" : "<:tier2:1133560878294372432>",
    "Tier 3" : "<:tier3:1133560879544291469>",
    "Tier 4" : "<:tier4:1133560881356226650>",
    "Tier 5" : "<:tier5:1133560882291548323>",
    "Tier 6" : "<:tier6:1133540654983688324>",
    "Tier 7" : "<:tier7:1133540655981920347>",
    
    "Crown" : "<:crown:1289290399025860691>",
}

__ICON_KEYS = Literal['Tier 0', 'Tier 1', 'Tier 2', 'Tier 3', 
             'Tier 4', 'Tier 5', 'Tier 6', 'Tier 7', 
             'Action', 'Arcade', 'Bullet Hell', 'First-Person', 
             'Platformer', 'Strategy', 'Points', 'Arrow', 
             'A Rank', 'B Rank', 'C Rank', 'D Rank', 'E Rank', 
             'S Rank', 'SS Rank', 'SSS Rank', 'EX Rank', 'P Rank', 
             'Q Rank', 'Casino', 'Diamond', 'All', 'Rank Omega', 
             'Hexagon', 'Site Dev', 'Shake', 'Safety', 'steam',
             'retroachievements', 'Crown']


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



# ------------- image icons -------------
CE_MOUNTAIN_ICON = "https://i.imgur.com/4PPsX4o.jpg"
"""The mountain icon used most commonly by CE."""
CE_HEX_ICON = "https://i.imgur.com/FLq0rFQ.png"
"""The hex icon used by CE's banner."""
CE_JAMES_ICON = "https://i.imgur.com/fcdHTvx.png"
"""The icon made by James that was previously used."""
FINAL_CE_ICON = "https://i.imgur.com/O9J7fg2.png"
"""The icon made by @crappy for CE Assistant."""

OBJECTIVE_TYPES = Literal["Primary", "Secondary", "Badge", "Community"]
PLATFORM_NAMES = Literal['steam', 'retroachievements']

# ------------- discord channel numbers -------------
IN_CE = False
# ce ids
__CE_OLD_LOG_ID = 1208259110638985246          # old log
__CE_CASINO_TEST_ID = 1208259878381031485      # fake casino (old)
__CE_GAME_ADDITIONS_ID = 949482536726298666    # game additions
__CE_CASINO_ID = 1080137628604694629           # real casino
__CE_CASINO_LOG_ID = 1218980203209035938       # casino log
__CE_PRIVATE_LOG_ID = 1208259110638985246      # private log
__CE_USER_LOG_ID = 1256832310523859025         # user log
__CE_PROOF_SUBMISSIONS_ID = 747384873320448082 # proof submissions
__CE_INPUT_LOG_ID = __CE_PRIVATE_LOG_ID        # input
# bot test ids
__TEST_GAME_ADDITIONS_ID = 1128742486416834570
__TEST_CASINO_ID = 811286469251039333
__TEST_CASINO_LOG_ID = 1257381604452466737
__TEST_PRIVATE_LOG_ID = 1141886539157221457
__TEST_USER_LOG_ID = 1257381593136365679
__TEST_PROOF_SUBMISSIONS_ID = 1263199416462868522
__TEST_INPUT_LOG_ID = 1294335132236251157
# go-to channels 
# NOTE: replace these with the ids as needed
if IN_CE:
    GAME_ADDITIONS_ID = __CE_GAME_ADDITIONS_ID
    CASINO_ID = __CE_CASINO_ID
    CASINO_LOG_ID = __CE_CASINO_LOG_ID
    PRIVATE_LOG_ID = __CE_PRIVATE_LOG_ID
    USER_LOG_ID = __CE_USER_LOG_ID
    PROOF_SUBMISSIONS_ID = __CE_PROOF_SUBMISSIONS_ID
    INPUT_LOG_ID = __CE_INPUT_LOG_ID
else :
    GAME_ADDITIONS_ID = __TEST_GAME_ADDITIONS_ID
    CASINO_ID = __TEST_CASINO_ID
    CASINO_LOG_ID = __TEST_CASINO_LOG_ID
    PRIVATE_LOG_ID = __TEST_PRIVATE_LOG_ID
    USER_LOG_ID = __TEST_USER_LOG_ID
    PROOF_SUBMISSIONS_ID = __TEST_PROOF_SUBMISSIONS_ID
    INPUT_LOG_ID = __TEST_INPUT_LOG_ID


"""
def get_current_unix() -> int :
    "Gets the current time in unix timestamp."
    dt = datetime.datetime.now(datetime.timezone.utc)

    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()
"""

def get_emoji(input : __ICON_KEYS) -> str :
    """Returns the emoji related to `input`."""
    if not IN_CE and input in list(__test_icons.keys()) :
        return __test_icons[input]
    return __icons[input]

#"""
#"3c3fd562-525c-4e24-a1fa-5b5eda85ebbd" : "Platformer",
#        "4d43349a-43a8-4755-9d52-41ece63ec5b1" : "Action",
##        "7f8676fe-4900-400b-9284-c073388d88f7" : "Bullet Hell",
#        "a6d00cc0-9481-47cb-bb52-a7011041915a" : "First-Person",
#        "ec499226-0913-4db1-890e-093b366bcb3c" : "Arcade",
##        "ffb558c1-5a45-4b8c-856c-e9622ce54f00" : "Strategy",
#        "00000000-0000-0000-0000-000000000000" : None
#3        """
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

def get_grammar_str(input : list) -> str :
    """Takes in the list `input` and returns a string of their
    contents grammatically correct.\n
    Example: [a, b, c] --> 'a, b, and c'\n
    Example: [a] --> 'a'"""
    #TODO: finish this function

CATEGORIES = Literal['Action', 'Arcade', 'Bullet Hell', 'First-Person',
            'Platformer', 'Strategy']

def get_item_from_list(ce_id, list) :
    """Return the object who's Challenge Enthusiast
    ID is provided by `ce_id`."""
    for item in list :
        if item.ce_id == ce_id : return item
    return None

def get_index_from_list(ce_id, list) :
    """Returns the index of the object provided by `ce_id`."""
    for i in range(len(list)) :
        if list[i].ce_id == ce_id : return i
    return -1

def replace_item_in_list(ce_id, item, list) -> list :
    """Replaces the object who's Challenge Enthusiast
    ID is provided by `ce_id`."""
    for i in range(len(list)) :
        if list[i].ce_id == ce_id :
            list[i] = item
    return list

def months_to_days(num_months : int) -> int:
    """Takes in a number of months `num_months` and returns 
    the number of days between today and `num_months` months away.
    \nWritten by Schmole (thank you schmole!!)"""
    # purpose -- determine number of days to 'x' months away. 
    #Required as duration will be different depending on 
    #point in the year, and get_rollable_game requires day inputs
    # function input = number of months
    # function output = number of days between now and input months away
    if num_months == 0 : return 0 
    now = datetime.datetime.now()
    end_year = now.year + (now.month + num_months - 1) // 12
    end_month = (now.month + num_months - 1) % 12 + 1
    end_date = datetime.date(end_year, end_month, min(calendar.monthrange(end_year, end_month)[1], now.day))
    date_delta = end_date - datetime.date(now.year, now.month, now.day)

    return date_delta.days

def get_unix(days = 0, minutes = None, months = None, old_unix = None) -> int:
    """Returns a unix timestamp for `days` days (or `minutes` minutes, or `months` months) from the current time.
    \nAdditionally, `old_unix` can be passed as a parameter to get `days` days (or `minutes` minutes, or `months` months) from that unix."""
    # -- old unix passed --
    if(old_unix != None) :
        if (minutes != None) : return int(minutes * 60) + old_unix
        elif (months != None) : return (months_to_days(months))*(86400) + old_unix
        else : return days * 86400 + old_unix

    # -- old unix NOT passed --
    # return right now
    if(days == "now") : return int(time.mktime((datetime.datetime.now()).timetuple()))
    # return the minutes
    elif (minutes != None) : return int(time.mktime((datetime.datetime.now()+datetime.timedelta(minutes=minutes)).timetuple()))
    # return the months
    elif (months != None) : return get_unix(days=months_to_days(months))
    # return the days
    elif (days == None) : return None

    else: return int(time.mktime((datetime.datetime.now()+datetime.timedelta(days=days)).timetuple()))


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

def get_rollable_game(
        database_name : list,
        completion_limit : int,
        price_limit : int,
        tier_number : int,
        user,
        category : str | list[str] = None,
        already_rolled_games : list = [],
        has_points_restriction : bool = False,
        price_restriction : bool = True
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
        print(f"get_rollable_game() called with the following parameters: ")
        print(f"database_name: {'passed correctly' if (database_name is not None or len(database_name) == 0) else 'passed incorrectly'}")
        print(f"completion limit: {completion_limit}")
        print(f"price_limit: {price_limit}")
        print(f"tier_number: {tier_number}")
        if (type(user) != list) :
            print(f"user: {user.ce_id}")
        else :
            print(f"user: {[u.ce_id for u in user]}")
        print(f"category: {category}")
        print(f"already_rolled_games: {already_rolled_games}")
        print(f"has_points_restriction: {has_points_restriction}")
        print(f"price_restriction: {price_restriction}")



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

        price = game.get_price()
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

        sh_data = game.get_steamhunters_data()
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
    response = requests.get("https://store.steampowered.com/api/storesearch/?", params=payload)
    json_response = json.loads(response)

    # look through all the games
    for item in json_response['items'] :
        if item['name'].lower() == name.lower() : return item['id']
    
    # if no exact match is found, return the first one
    return json_response['items'][0]['id']

def achievements_are_equal(old_achievements : list[str] | None, new_achievements : list[str] | None) -> bool :
    "Returns true if the achievements are equal, false if they're not."
    if old_achievements is None and new_achievements is not None : return False
    if old_achievements is not None and new_achievements is None : return False
    if old_achievements is None and new_achievements is None : return True
    return set(old_achievements) == set(new_achievements)

def current_month_str() -> str :
    "Returns the name of the current month."
    return datetime.datetime.now().strftime('%B')

def current_month_num() -> int :
    "The number of the current month."
    return datetime.datetime.now().month

def previous_month_str() -> str :
    "Returns the name of the previous month."
    current_month_num = datetime.datetime.now().month
    previous_month_num = (current_month_num - 1) if current_month_num != 1 else 12
    return datetime.datetime(year=2024, month=previous_month_num, day = 1).strftime('%B')

def cetimestamp_to_datetime(timestamp : str) -> datetime.datetime :
    "Takes in a CE timestamp and returns a datetime."
    return datetime.datetime.strptime(str(timestamp[:-5:]), "%Y-%m-%dT%H:%M:%S")

def format_ce_link(ce_link : str) -> str | None :
    "Takes in a full link and returns the CE ID."

    # replace all the other stuff
    ce_id = ce_link.replace("https://","").replace("www.","").replace("cedb.me", "").replace("/","").replace("games","").replace("user","")

    # if it's not valid, return None
    if not (ce_id[8:9] == ce_id[13:14] == ce_id[18:19] == ce_id[23:24] == "-") :
        return None
    
    # else, return the id.
    return ce_id

def is_within_percentage(input : int | float, percentage : int, value : int) -> bool :
    """Checks if `input` is within `percent`% of `value`.
    Example: `is_within_percentage(10, 50, 15)` will check if 10 is within 50% of 15."""
    threshold = percentage / 100 * value
    lower_bound = value - threshold
    upper_bound = value + threshold
    return lower_bound <= input <= upper_bound