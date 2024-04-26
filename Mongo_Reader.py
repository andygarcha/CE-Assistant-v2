# imports
from typing import Literal
from bson import ObjectId
from CE_Game import CE_Game
from CE_Objective import CE_Objective
from CE_User import CE_User
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient


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
_uri = "mongodb+srv://andrewgarcha:KUTo7dCtGRy4Nrhd@ce-cluster.inrqkb3.mongodb.net/?retryWrites=true&w=majority"
_mongo_client = AsyncIOMotorClient(_uri)
_mongo_database = _mongo_client['database_name']
collection = _mongo_client['database_name']['ce-collection']
"""The MongoDB collection used to pull and push all the databases."""
# get and set mongo databases
_mongo_names = Literal["name_old", "tier", "curator", "user", "tasks", "unfinished", "name", "steamhunters"]
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
    """Turns the MongoDB dictionary into a :class:`CE_Objective` object."""
    achievements = None
    requirements = None
    if "Achievements" in objective : achievements = objective['Achievements']
    if "Requirements" in objective : requirements = objective['Requirements']
    return CE_Objective(objective['CE ID'], False, objective['Description'],
                                objective['Point Value'], objective['Name'], None,
                                requirements, achievements)

def _mongo_to_user(user : dict) -> CE_User :
    """Turns the MongoDB dictionary into a :class:`CE_User` object."""

def _mongo_to_game(game : dict) -> CE_Game :
    """Turns the MongoDB dictionary into a :class:`CE_Game` object."""

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
    
    return CE_Game(game['CE ID'], game['Name'], game['Platform'], game['Platform ID'], game['Category'],
                   game_primary_objectives, game_community_objectives, game['Last Updated'])
            

def get_mongo_users() -> list[CE_User] :
    """Returns a list of :class:`CE_User`'s pulled directly from the MongoDB database."""

async def get_mongo_games() -> list[CE_Game] :
    """Returns a list of :class:`CE_Game`'s pulled directly from the MongoDB database."""
    games = list[CE_Game] = []
    database_name = await get_mongo('name')
    for game in database_name :
        games.append(_mongo_to_game(game))
    return games

def get_user_from_id(ce_id : str) -> CE_User :
    """Takes in a String `ce_id` and grabs its :class:`CE_User` object from the MongoDB database."""

def get_game_from_id(ce_id : str) -> CE_Game :
    """Takes in a String `ce_id` and grabs its :class:`CE_Game` object from the MongoDB database."""

def dump_users(users : list[CE_User]) -> None :
    """Takes in a list of :class:`CE_User`'s and dumps it back to the MongoDB database."""

def dump_games(games : list[CE_Game]) -> None :
    """Takes in a list of :class:`CE_Game`'s and dumps it back to the MongoDB database."""