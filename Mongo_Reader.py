"""
Handles all MongoDB-related interactions for CE Assistant v2.
"""


# imports
from typing import Literal
from bson import ObjectId
from CE_Cooldown import CE_Cooldown
from CE_Game import CE_Game
from CE_Objective import CE_Objective
from CE_Roll import CE_Roll
from CE_User import CE_User
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient

from CE_User_Game import CE_User_Game
from CE_User_Objective import CE_User_Objective


# ----------------------------- mongo helpers --------------------------------
_mongo_ids = {
    "name_old" : ObjectId('64f8d47f827cce7b4ac9d35b'),
    "tier" : ObjectId('64f8bc4d094bdbfc3f7d0050'),
    "curator" : ObjectId('64f8d63592d3fe5849c1ba35'),
    "tasks" : ObjectId('64f8d6b292d3fe5849c1ba37'),
    "user" : ObjectId('64f8bd1b094bdbfc3f7d0051'),
    "unfinished" : ObjectId('650076a9e35bbc49b06c9881'),
    "name" : ObjectId('6500f7d3b3e4253bef9f51e6'),
    "steamhunters" : ObjectId('65f64af8ba6efd911038594c')
}
"""The :class:`ObjectID` values stored under the `_id` value in each document."""
_uri = "mongodb+srv://andrewgarcha:KUTo7dCtGRy4Nrhd@ce-cluster.inrqkb3.mongodb.net/" 
+ "?retryWrites=true&w=majority"
_mongo_client = AsyncIOMotorClient(_uri)
_mongo_database = _mongo_client['database_name']
collection = _mongo_client['database_name']['ce-collection']
"""The MongoDB collection used to pull and push all the databases."""
# get and set mongo databases
_mongo_names = Literal["name_old", "tier", "curator", "user", "tasks", "unfinished", 
                       "name", "steamhunters"]
async def get_mongo(title : _mongo_names):
    """Returns the MongoDB associated with `title`."""
    _db = await collection.find_one({'_id' : _mongo_ids[title]})
    del _db['_id']
    return _db
async def dump_mongo(title : _mongo_names, data) :
    """Dumps the MongoDB given by `title` and passed by `data`."""
    if "_id" not in data : data["_id"] = _mongo_ids[title]
    return await collection.replace_one({'_id' : _mongo_ids[title]}, data)



# ---------------------------------- end mongo helpers -----------------------------------



def _mongo_to_game_objective(objective : dict) -> CE_Objective :
    """Turns the MongoDB dictionary for an objective into a :class:`CE_Objective` object."""
    achievements = None
    requirements = None
    if "Achievements" in objective : achievements = objective['Achievements']
    if "Requirements" in objective : requirements = objective['Requirements']
    return CE_Objective(objective['CE ID'], False, objective['Description'],
                                objective['Point Value'], objective['Name'], None,
                                requirements, achievements)



def _mongo_to_user_roll(roll : dict) -> CE_Roll :
    """Turns the MongoDB dictionary for a roll event into a :class:`CE_Roll` object."""
    event_name, partner, games, init_time, due_time, completed_time, cooldown_days, rerolls
    if 'Event Name' in roll : event_name = roll['Event Name']
    if 'Partner' in roll : partner = roll['Partner']
    if 'Games' in roll : games = roll['Games']
    if 'Init Time' in roll : init_time = roll['Init Time']
    if 'Due Time' in roll : due_time = roll['Due Time']
    if 'Completed Time' in roll : completed_time = roll['Completed Time']
    if 'Cooldown Days' in roll : cooldown_days = roll['Cooldown Days']
    if 'Rerolls' in roll : rerolls = roll['Rerolls']

    return CE_Roll(event_name, init_time, due_time, completed_time, games,
                   partner, cooldown_days, rerolls)


def _mongo_to_user_game(game : dict) -> CE_User_Game :
    """Turns a user game (stored in user --> Owned Games) 
    into a :class:`CE_User_Game` object.
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
    game_id = game.keys()[0]
    primary_objectives : list[CE_User_Objective] = []
    community_objectives : list[CE_User_Objective] = []

    if 'Primary Objectives' in game :
        for obj in game['Primary Objectives'] :
            primary_objectives.append(CE_User_Objective(obj, game_id, False, 
                                                        game['Primary Objectives'][obj]))
    if 'Community Objectives' in game :
        for obj in game['Community Objectives'] :
            community_objectives.append(CE_User_Objective(obj, game_id, True,
                                                          game['Community Objectives'][obj]))
    
    return CE_User_Game(game_id, primary_objectives, community_objectives)





def _mongo_to_user(user : dict) -> CE_User :
    """Turns the MongoDB dictionary into a :class:`CE_User` object."""
    current_rolls : list[CE_Roll] = []
    for roll in user['Current Rolls'] :
        current_rolls.append(_mongo_to_user_roll(roll))
    completed_rolls : list[CE_Roll] = []
    for roll in user['Completed Rolls'] :
        completed_rolls.append(_mongo_to_user_roll(roll))
    cooldowns : list[CE_Cooldown] = []
    for roll in user['Cooldowns'] :
        cooldowns.append(CE_Cooldown(roll, user['Cooldowns'][roll]))
    pending_rolls : list[CE_Cooldown] = []
    for pending in user['Pending Rolls'] :
        pending_rolls.append(CE_Cooldown(pending, user['Pending Rolls'][pending]))
    user_games : list[CE_User_Game] = []
    for game in user['Owned Games'] :
        user_games.append(_mongo_to_user_game({game : user['Owned Games'][game]}))

    return CE_User(user['Discord ID'], user['CE ID'], user['Casino Score'], user_games,
                   current_rolls, completed_rolls, pending_rolls, cooldowns)



def _mongo_to_game(game : dict) -> CE_Game :
    """Turns the MongoDB dictionary into a :class:`CE_Game` object.
    Example input:
    ```
    { 
        "Name" : name,
        "CE ID" : ce_id,
        "Platform" : platform,
        "Platform ID" : platform_id,
        "Category" : category,
        "Primary Objectives" : {
            "hfjksdlafhjkldas" : 20,
            "j;ofjdaioslfal;o" : 10
        },
        "Community Objectives" : {},
        "Last Updated" : 1689078932
    }
    ```
    
    """

    # go through objectives first!
    game_primary_objectives : list[CE_Objective] = []
    game_community_objectives : list[CE_Objective] = []
    if 'Primary Objectives' in game :
        for objective in game :
            game_objective = _mongo_to_game_objective(objective)
            game_objective.set_community(False)
            game_objective.set_game_id(game['CE ID'])
            game_primary_objectives.append(game_objective)
    if 'Community Objectives' in game :
        for objective in game :
            game_objective = _mongo_to_game_objective(objective)
            game_objective.set_community(True)
            game_objective.set_game_id(game['CE ID'])
            game_community_objectives.append(game_objective)
    
    return CE_Game(game['CE ID'], game['Name'], game['Platform'], game['Platform ID'], 
                   game['Category'], game_primary_objectives, game_community_objectives, 
                   game['Last Updated'])
            



async def get_mongo_users() -> list[CE_User] :
    """Returns a list of :class:`CE_User`'s pulled directly from the MongoDB database."""
    users = list[CE_User] = []
    database_user = await get_mongo("user")
    for user in database_user :
        users.append(_mongo_to_user(database_user[user]))
    return users



async def get_mongo_games() -> list[CE_Game] :
    """Returns a list of :class:`CE_Game`'s pulled directly from the MongoDB database."""
    games = list[CE_Game] = []
    database_name = await get_mongo('name')
    for game in database_name :
        games.append(_mongo_to_game(database_name[game]))
    return games



async def get_user_from_id(ce_id : str) -> CE_User | None :
    """Takes in a String `ce_id` and grabs its :class:`CE_User` 
    object from the MongoDB database."""
    for user in await get_mongo_users() :
        if user.get_ce_id() == ce_id : return user
    return None



async def get_game_from_id(ce_id : str) -> CE_Game :
    """Takes in a String `ce_id` and grabs its :class:`CE_Game` 
    object from the MongoDB database."""



async def dump_users(users : list[CE_User]) -> None :
    """Takes in a list of :class:`CE_User`'s and dumps it back to the MongoDB database."""



async def dump_games(games : list[CE_Game]) -> None :
    """Takes in a list of :class:`CE_Game`'s and dumps it back to the MongoDB database."""