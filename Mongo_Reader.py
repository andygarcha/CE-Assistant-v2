"""
Handles all MongoDB-related interactions for CE Assistant v2.
"""


# imports
from typing import Literal
from bson import ObjectId
from CE_Cooldown import CECooldown
from CE_Game import CEGame
from CE_Objective import CEObjective
from CE_Roll import CERoll
from CE_User import CEUser
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient

from CE_User_Game import CEUserGame
from CE_User_Objective import CEUserObjective


# ----------------------------- mongo helpers --------------------------------
mongo_ids = {
    'name' : ObjectId('66303f21918c91e3b67b33df'),
    'user' : ObjectId('66303f66918c91e3b67b33e0')
}
"""The :class:`ObjectID` values stored under the `_id` value in each document."""
_uri = ("mongodb+srv://andrewgarcha:KUTo7dCtGRy4Nrhd@ce-cluster.inrqkb3.mongodb.net/" 
    + "?retryWrites=true&w=majority")
_mongo_client = AsyncIOMotorClient(_uri)
_collection = _mongo_client['database_name']['ce-assistant-v2']
_mongo_names = Literal['name', 'user']

async def get_mongo(title :_mongo_names) :
    """Returns the MongoDB associated with `title`
    (without the `id` marker!)"""
    db = await _collection.find_one({'_id' : mongo_ids[title]})
    del db['_id']
    return db

async def dump_mongo(title : _mongo_names, data) :
    """Dumps the MongoDB given by `title` and passed by `data`."""
    if '_id' not in data : data['_id'] = mongo_ids[title]
    return await _collection.replace_one({'_id' : mongo_ids[title]}, data)



# ---------------------------------- end mongo helpers -----------------------------------



def _mongo_to_game_objective(objective : dict) -> CEObjective :
    """Turns the MongoDB dictionary for an objective 
    into a :class:`CEObjective` object."""
    achievements, requirements, partial_points = (None,)*3
    if "Achievements" in objective : achievements = objective['Achievements']
    if "Requirements" in objective : requirements = objective['Requirements']
    if 'Partial Points' in objective : partial_points = objective['Partial Points']
    
    return CEObjective(
        ce_id=objective['CE ID'],
        is_community=objective['Community'],
        description=objective['Description'],
        point_value=objective['Point Value'],
        name=objective['Name'],
        game_ce_id=None,
        requirements=requirements,
        achievement_ce_ids=achievements,
        point_value_partial=partial_points
    )





def _mongo_to_user_roll(roll : dict) -> CERoll :
    """Turns the MongoDB dictionary for a roll event 
    into a :class:`CERoll` object."""
    event_name, partner, games, init_time, due_time = (None,)*5
    completed_time, cooldown_days, rerolls, user_id = (None,)*4
    if 'Event Name' in roll : event_name = roll['Event Name']
    if 'User ID' in roll : user_id = roll['User ID']
    if 'Partner ID' in roll : partner = roll['Partner']
    if 'Games' in roll : games = roll['Games']
    if 'Init Time' in roll : init_time = roll['Init Time']
    if 'Due Time' in roll : due_time = roll['Due Time']
    if 'Completed Time' in roll : completed_time = roll['Completed Time']
    if 'Cooldown Days' in roll : cooldown_days = roll['Cooldown Days']
    if 'Rerolls' in roll : rerolls = roll['Rerolls']

    return CERoll(
        roll_name=event_name,
        user_ce_id=user_id,
        games=games,
        partner_ce_id=partner,
        cooldown_days=cooldown_days,
        init_time=init_time,
        due_time=due_time,
        completed_time=completed_time,
        rerolls=rerolls
    )


def _mongo_to_user_objective(objective : dict) -> CEUserObjective :
    """
    Takes in a dict and returns a CEUserObjective object.
    """
    return CEUserObjective(
        ce_id=objective['CE ID'],
        game_ce_id=objective['Game CE ID'],
        is_community=objective['Community'],
        user_points=objective['User Points'],
        name=objective['Name']
    )


def _mongo_to_user_game(game : dict) -> CEUserGame :
    """Turns a user game (stored in user --> Owned Games) 
    into a :class:`CEUserGame` object.
    Game is sent over as such:
    ```
    { 
        "1e866995-6fec-452e-81ba-1e8f8594f4ea" : {
            "Primary Objectives" : {
                "d1c48bd5-14cb-444e-9301-09574dfbe86a" : 20,      
                "eb1bf5f9-4c82-4758-b6bb-a822e8bd97cb" : 150
            },
            "Community Objectives" : {
                "138df16d-c56a-4df4-8055-5176bd172a6b" : true
            }
        }
    }
    ```
    """
    primary_objectives : list[CEUserObjective] = []
    community_objectives : list[CEUserObjective] = []

    for objective in game['Primary Objectives'] :
        primary_objectives.append(_mongo_to_user_objective(objective))
    for objective in game['Community Objectives'] :
        primary_objectives.append(_mongo_to_user_objective(objective))

    return CEUserGame(
        ce_id=game['CE ID'],
        user_primary_objectives=primary_objectives,
        user_community_objectives=community_objectives,
        name=game['Name']
    )


def _mongo_to_user_cooldown(cooldown : dict) -> CECooldown :
    """Returns a CECooldown object."""
    return CECooldown(
        roll_name=cooldown['Event Name'],
        end_time=cooldown['End Time']
    )



def _mongo_to_user(user : dict) -> CEUser :
    """Turns the MongoDB dictionary into a :class:`CEUser` object."""
    current_rolls : list[CERoll] = []
    for roll in user['Current Rolls'] :
        current_rolls.append(_mongo_to_user_roll(roll))
        
    completed_rolls : list[CERoll] = []
    for roll in user['Completed Rolls'] :
        completed_rolls.append(_mongo_to_user_roll(roll))

    cooldowns : list[CECooldown] = []
    for cooldown in user['Cooldowns'] :
        cooldowns.append(_mongo_to_user_cooldown(cooldown))

    pending_rolls : list[CECooldown] = []
    for pending in user['Pending Rolls'] :
        pending_rolls.append(_mongo_to_user_cooldown(pending))

    user_games : list[CEUserGame] = []
    for game in user['Owned Games'] :
        user_games.append(_mongo_to_user_game(game))

    return CEUser(
        discord_id=user['Discord ID'],
        ce_id=user['CE ID'],
        casino_score=user['Casino Score'],
        owned_games=user_games,
        current_rolls=current_rolls,
        completed_rolls=completed_rolls,
        cooldowns=cooldowns,
        pending_rolls=pending_rolls
    )



def _mongo_to_game(game : dict) -> CEGame :
    """Turns the MongoDB dictionary into a :class:`CEGame` object.
    Example input:
    ```
    { 
        "Name" : name,
        "CE ID" : ce_id,
        "Platform" : platform,
        "Platform ID" : platform_id,
        "Category" : category,
        "Primary Objectives" : {
            "hfjksdlafhjkldas" : datadatadata,
            "j;ofjdaioslfal;o" : datadatamoredata
        },
        "Community Objectives" : {},
        "Last Updated" : 1689078932
    }
    ```
    
    """

    # go through objectives first!
    game_primary_objectives : list[CEObjective] = []
    game_community_objectives : list[CEObjective] = []
    if 'Primary Objectives' in game :
        for objective in game :
            game_objective = _mongo_to_game_objective(
                game['Primary Objectives'][objective]
            )
            game_objective.set_community(False)
            game_objective.set_game_id(game['CE ID'])
            game_primary_objectives.append(game_objective)
    if 'Community Objectives' in game :
        for objective in game :
            game_objective = _mongo_to_game_objective(
                game['Community Objectives'][objective]
            )
            game_objective.set_community(True)
            game_objective.set_game_id(game['CE ID'])
            game_community_objectives.append(game_objective)

    return CEGame(
        ce_id=game['CE ID'],
        game_name=game['Name'],
        platform=game['Platform'],
        platform_id=game['Platform ID'],
        category=game['Category'],
        primary_objectives=game_primary_objectives,
        community_objectives=game_community_objectives,
        last_updated=game['Last Updated']
    )
            



async def get_mongo_users() -> list[CEUser] :
    """Returns a list of :class:`CEUser`'s pulled directly from the MongoDB database."""
    users = list[CEUser] = []
    database_user = await get_mongo("user")
    for user in database_user['data'] :
        users.append(_mongo_to_user(database_user[user]))
    return users



async def get_mongo_games() -> list[CEGame] :
    """Returns a list of :class:`CEGame`'s pulled directly from the MongoDB database."""
    games = list[CEGame] = []
    database_name = await get_mongo('name')
    for game in database_name['data'] :
        games.append(_mongo_to_game(database_name[game]))
    return games



#async def get_user_from_id(ce_id : str) -> CEUser | None :
#    """Takes in a String `ce_id` and grabs its :class:`CEUser` 
#    object from the MongoDB database."""
#    for user in await get_mongo_users() :
#        if user.get_ce_id() == ce_id : return user
#    return None



#async def get_game_from_id(ce_id : str) -> CEGame :
#    """Takes in a String `ce_id` and grabs its :class:`CEGame` 
#    object from the MongoDB database."""



async def dump_users(users : list[CEUser]) -> None :
    """Takes in a list of :class:`CEUser`'s and dumps it back to the MongoDB database."""
    dictionary = []
    for user in users :
        dictionary.append(user.to_dict())
    await dump_mongo('user', {'data' : dictionary})


async def dump_games(games : list[CEGame]) -> None :
    """Takes in a list of :class:`CEGame`'s and dumps it back to the MongoDB database."""
    dictionary = []
    for game in games :
        dictionary.append(game.to_dict())
    await dump_mongo('name', {'data' : dictionary})