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
    "Safety" : '<:safety:802615322858487838>'
}

__ICON_KEYS = Literal['Tier 0', 'Tier 1', 'Tier 2', 'Tier 3', 
             'Tier 4', 'Tier 5', 'Tier 6', 'Tier 7', 
             'Action', 'Arcade', 'Bullet Hell', 'First-Person', 
             'Platformer', 'Strategy', 'Points', 'Arrow', 
             'A Rank', 'B Rank', 'C Rank', 'D Rank', 'E Rank', 
             'S Rank', 'SS Rank', 'SSS Rank', 'EX Rank', 'P Rank', 
             'Q Rank', 'Casino', 'Diamond', 'All', 'Rank Omega', 
             'Hexagon', 'Site Dev', 'Shake', 'Safety']


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


banned_games = [
    "Serious Sam HD: The Second Encounter", 
    "Infinite Air with Mark McMorris", 
    "A Bastard's Tale",
    "A Most Extraordinary Gnome",
    "Bot Vice",
    "Curvatron",
    "Dark Souls III",
    "Destructivator 2",
    "DSY",
    "Geballer",
    "Gravity Den",
    "Gridform",
    "Heck Deck",
    "ITTA",
    "Just Arms",
    "LaserBoy",
    "Little Nightmares",
    "MO:Astray",
    "MOONPONG",
    "Mortal Shell",
    "Overture",
    "Project Rhombus",
    "Satryn Deluxe",
    "SEUM",
    "Squidlit",
    "Super Cable Boy",
    "The King's Bird",
    "you have to win the game",
    "Heavy Bullets",
    "Barrier X",
    "Elasto Mania Remastered"
]

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
__CE_OLD_LOG_ID = 1208259110638985246         # old log
__CE_LOG_ID = 1218980203209035938             # current log
__CE_CASINO_TEST_ID = 1208259878381031485     # fake casino
__CE_CASINO_ID = 1080137628604694629          # real casino
__CE_GAME_ADDITIONS_ID = 949482536726298666   # game additions
__CE_PRIVATE_LOG_ID = 1208259110638985246     # private log
# bot test ids
__TEST_LOG_ID = 1141886539157221457
__TEST_CASINO_ID = 811286469251039333
__TEST_GAME_ADDITIONS_ID = 1128742486416834570
# go-to channels 
# NOTE: replace these with the ids as needed
if IN_CE:
    GAME_ADDITIONS_ID = __CE_GAME_ADDITIONS_ID
    CASINO_ID = __CE_CASINO_ID
    LOG_ID = __CE_LOG_ID
    PRIVATE_LOG_ID = __CE_PRIVATE_LOG_ID
else :
    GAME_ADDITIONS_ID = __TEST_GAME_ADDITIONS_ID
    CASINO_ID = __TEST_CASINO_ID
    LOG_ID = __TEST_LOG_ID
    PRIVATE_LOG_ID = __TEST_LOG_ID


"""
def get_current_unix() -> int :
    "Gets the current time in unix timestamp."
    dt = datetime.datetime.now(datetime.timezone.utc)

    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()
"""

def get_emoji(input : __ICON_KEYS) -> str :
    """Returns the emoji related to `input`."""
    return __icons[input]

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
    now = datetime.datetime.now()
    end_year = now.year + (now.month + num_months - 1) // 12
    end_month = (now.month + num_months - 1) % 12 + 1
    end_date = datetime.date(end_year, end_month, min(calendar.monthrange(end_year, end_month)[1], now.day))
    date_delta = end_date - datetime.date(now.year, now.month, now.day)

    return date_delta.days

def get_unix(days = 0, minutes = -1, months = -1, old_unix = -1) -> int:
    """Returns a unix timestamp for `days` days (or `minutes` minutes, or `months` months) from the current time.
    \nAdditionally, `old_unix` can be passed as a parameter to get `days` days (or `minutes` minutes, or `months` months) from that unix."""
    # -- old unix passed --
    if(old_unix != -1) :
        if (minutes != -1) : return int(minutes * 60) + old_unix
        elif (months != -1) : return (months_to_days(months))*(86400) + old_unix
        else : return days * 86400 + old_unix

    # -- old unix NOT passed --
    # return right now
    if(days == "now") : return int(time.mktime((datetime.datetime.now()).timetuple()))
    # return the minutes
    elif (minutes != -1) : return int(time.mktime((datetime.datetime.now()+datetime.timedelta(minutes=minutes)).timetuple()))
    # return the months
    elif (months != -1) : return get_unix(months_to_days(months))
    # return the days
    else: return int(time.mktime((datetime.datetime.now()+datetime.timedelta(days)).timetuple()))



def get_rollable_game(
        database_name : list,
        completion_limit : int,
        price_limit : int,
        tier_number : int,
        user,
        category : str | list[str] = None,
        already_rolled_games : list = [],
):
    """Takes in a slew of parameters and returns a `str` of 
    Challenge Enthusiast ID that match the criteria.
    """
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser

    # avoid circular imports
    database_name : list[CEGame] = database_name
    user : CEUser = user

    # randomize database_name :
    random.shuffle(database_name)

    # if only one category was sent, put it in an array so we can use `in`.
    if type(category) == str :
        category = [category]

    # ---- iterate through all the games ----
    for game in database_name :
        if category != None and game.category not in category :
            "Incorrect category."
            continue

        if game.platform != "steam" :
            "Non-steam game."
            continue

        if game.is_unfinished() :
            "Game is currently under construction."
            continue

        if game.get_tier() != f"Tier {tier_number}" :
            "Incorrect tier."
            continue

        if (user.owns_game(game.ce_id) 
            and user.get_owned_game(game.ce_id).is_completed()) :
            "User has completed game already."
            continue

        if game.ce_id in already_rolled_games :
            "This game has already been rolled."
            continue

        if game.has_an_uncleared() :
            "This game has an uncleared objective."
            continue

        if game.get_price() > price_limit :
            "The price is too high."
            continue

        sh_data = game.get_steamhunters_data()
        if sh_data == None or sh_data > completion_limit :
            "The SteamHunters median-completion-time is too high."
            continue

        if game.game_name in banned_games :
            "This game is in the Banned Games section."
            continue

        return game.ce_id
    
    return None


async def name_to_steamid(name : str) -> str :
    "Takes in the name of a game and returns the Steam App ID associated with it."

    # -- check CE first --
    import Modules.Mongo_Reader as Mongo_Reader
    database_name = await Mongo_Reader.get_mongo_games()
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