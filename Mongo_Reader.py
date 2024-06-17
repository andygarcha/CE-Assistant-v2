"""
Handles all MongoDB-related interactions for CE Assistant v2.
"""


# imports
import json
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

# open secret_info.json
with open('secret_info.json') as f :
    """The :class:`ObjectID` values stored under the `_id` value in each document."""
    local_json_data = json.load(f)
    _uri = local_json_data['mongo_uri']
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
        objective_type=objective['Type'],
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
    completed_time, rerolls, user_id = (None,)*3
    if 'Event Name' in roll : event_name = roll['Event Name']
    if 'User ID' in roll : user_id = roll['User ID']
    if 'Partner ID' in roll : partner = roll['Partner']
    if 'Games' in roll : games = roll['Games']
    if 'Init Time' in roll : init_time = roll['Init Time']
    if 'Due Time' in roll : due_time = roll['Due Time']
    if 'Completed Time' in roll : completed_time = roll['Completed Time']
    if 'Rerolls' in roll : rerolls = roll['Rerolls']

    return CERoll(
        roll_name=event_name,
        user_ce_id=user_id,
        games=games,
        partner_ce_id=partner,
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
        type=objective['Type'],
        user_points=objective['User Points'],
        name=objective['Name']
    )


def _mongo_to_user_game(game : dict) -> CEUserGame :
    """Turns a user game (stored in user --> Owned Games) 
    into a :class:`CEUserGame` object.
    Game is sent over as such:
    ```
    {
        "Name" : "Neon White",
        "CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
        "Objectives" : [
            {
                "Name" : "I just keep getting better and better.",
                "CE ID" : "a351dce1-ee51-4b55-a05b-38a74854a8be",
                "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                "Type" : 'Primary',
                "User Points" : 20
            },
            {
                "Name" : "Demon Exterminator",
                "CE ID" : "2a7ad593-4afd-4470-b709-f5ac6b4487e5",
                "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                "Type" : "Badge",
                "User Points" : 35
            }
        ]
    }
    ```
    """
    objectives : list[CEUserObjective] = []

    for objective in game['Objectives'] :
        objectives.append(_mongo_to_user_objective(objective))

    return CEUserGame(
        ce_id=game['CE ID'],
        name=game['Name'],
        user_objectives=objectives
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
        "Objectives" : [
            {
                "bla" : "blah",
                "fhjdsalk" : "fhjkdslahfjkdl"
            },
            {
                "hfjkdls", "p9owqs",
                "plpfsdq", "ol,cvx"
            }
        ]
        "Last Updated" : 1689078932
    }
    ```
    """

    # go through objectives first!
    game_objectives : list[CEObjective] = []
    if 'Objectives' in game :
        for objective in game['Objectives'] :
            game_objective = _mongo_to_game_objective(
                objective=objective
            )
            game_objective.game_ce_id = game['CE ID']
            game_objectives.append(game_objective)

    return CEGame(
        ce_id=game['CE ID'],
        game_name=game['Name'],
        platform=game['Platform'],
        platform_id=game['Platform ID'],
        category=game['Category'],
        objectives=game_objectives,
        last_updated=game['Last Updated']
    )




async def get_mongo_users() -> list[CEUser] :
    """Returns a list of :class:`CEUser`'s pulled directly from the MongoDB database."""
    users : list[CEUser] = []
    database_user = await get_mongo("user")
    for user in database_user['data'] :
        users.append(_mongo_to_user(user))
    return users



async def get_mongo_games() -> list[CEGame] :
    """Returns a list of :class:`CEGame`'s pulled directly from the MongoDB database."""
    games : list[CEGame] = []
    database_name = await get_mongo('name')
    for game in database_name['data'] :
        games.append(_mongo_to_game(game))
    return games



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

async def dump_user(user : CEUser | list[CEUser]) -> None :
    """Takes in one (or more) `CEUser`'s and dumps them."""
    if type(user) == CEUser : 
        user : list[CEUser] = [user]
    else :
        user : list[CEUser] = user

    database_user = await get_mongo_users()

    for i, u in enumerate(database_user) :
        for b in user :
            if u.get_ce_id() == b.get_ce_id() :
                database_user[i] = b

    await dump_users(database_user)
