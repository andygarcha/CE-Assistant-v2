"""
Handles all MongoDB-related interactions for CE Assistant v2.
Version 3 : Object-Oriented, and each item has its own document.
"""


# imports
import json
from typing import Literal
from bson import ObjectId

# -- local --
from Classes.CE_Cooldown import CECooldown
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.OtherClasses import *

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient




# open secret_info.json
with open('secret_info.json') as f :
    """The :class:`ObjectID` values stored under the `_id` value in each document."""
    local_json_data = json.load(f)
    _uri = local_json_data['mongo_uri']
_mongo_client = AsyncIOMotorClient(_uri)
V3NAMETITLE = "database-name-v3"
V3USERTITLE = "database-user-v3"
V3INPUTTITLE = "database-input-v3"
V3MISCTITLE = "database-misc-v3"


# VERSION 3
async def get_list(database : Literal["name", "user", "input"]) -> list[str] :
    if database == "name" :
        collection = _mongo_client['database_name'][V3NAMETITLE]
    elif database == "user" :
        collection = _mongo_client['database_name'][V3USERTITLE]
    elif database == "input" :
        collection = _mongo_client['database_name'][V3INPUTTITLE]

    cursor = collection.find({}, {"ce_id" : 1, "_id" : 0})
    ce_ids = await cursor.to_list(length=None)

    ce_id_values = [doc["ce_id"] for doc in ce_ids if "ce_id" in doc]
    return ce_id_values



# -- games -- #
async def get_game(ce_id : str) -> CEGame | None :
    "Gets a game associated with `ce_id`."
    collection = _mongo_client['database_name'][V3NAMETITLE]
    
    db = await collection.find_one({"ce_id" : ce_id})
    if db is None : return None

    return __mongo_to_game(db)

async def get_database_name() -> list[CEGame] :
    collection = _mongo_client['database_name'][V3NAMETITLE]

    cursor = collection.find({}, {"_id" : 0})
    objects = await cursor.to_list(length=None)

    database_user : list[CEUser] = []
    for o in objects :
        try : database_user.append(__mongo_to_game(o))
        except : continue
    
    return database_user

async def dump_game(game : CEGame) :
    "Dumps a game."
    collection = _mongo_client['database_name'][V3NAMETITLE]

    if (await collection.find_one({"ce_id" : game.ce_id})) == None :
        await collection.insert_one(game.to_dict())
    else :
        await collection.replace_one({"ce_id" : game.ce_id}, game.to_dict())
    pass

async def delete_game(ce_id : str) :
    "Deletes a game."
    collection = _mongo_client['database_name'][V3NAMETITLE]

    result = await collection.delete_one({"ce_id" : ce_id})
    if result.deleted_count == 0 :
        raise Exception("Game not deleted properly.")


def __mongo_to_game(game : dict) -> CEGame :
    return CEGame(
        ce_id=game['ce_id'],
        game_name=game['name'],
        platform=game['platform'],
        platform_id=game['platform_id'],
        category=game['category'],
        objectives=[__mongo_to_objective(obj) for obj in game['objectives']]
    )

def __mongo_to_objective(obj : dict) -> CEObjective :
    return CEObjective(
        ce_id=obj['ce_id'],
        objective_type=obj['type'],
        description=obj['description'],
        point_value=obj['value'],
        name=obj['name'],
        game_ce_id=obj['game_ce_id'],
        requirements=obj['requirements'],
        achievement_ce_ids=obj['achievements'],
        point_value_partial=obj['partial_value']
    )

# -- users -- #

async def get_user(ce_id : str) -> CEUser :
    "Gets a user associated with `ce_id`."
    collection = _mongo_client['database_name'][V3USERTITLE]

    db = await collection.find_one({"ce_id" : ce_id})
    if db is None : return None

    return __mongo_to_user(db)

async def dump_user(user : CEUser) :
    "Dumps a user back to the backend."
    collection = _mongo_client['database_name'][V3USERTITLE]

    if (await collection.find_one({"ce_id" : user.ce_id})) == None :
        await collection.insert_one(user.to_dict())
    else :
        await collection.replace_one({"ce_id" : user.ce_id}, user.to_dict())
    pass

async def get_database_user() -> list[CEUser] :
    collection = _mongo_client['database_name'][V3USERTITLE]

    cursor = collection.find({}, {"_id" : 0})
    objects = await cursor.to_list(length=None)

    database_user : list[CEUser] = []
    for o in objects :
        try : database_user.append(__mongo_to_user(o))
        except : continue
    
    return database_user

def __mongo_to_user(user : dict) -> CEUser :
    return CEUser(
        discord_id=user['discord_id'],
        ce_id=user['ce_id'],
        display_name=user['display_name'],
        avatar=user['avatar'],
        rolls=[__mongo_to_roll(roll) for roll in user['rolls']],
        owned_games=[__mongo_to_user_game(game) for game in user['owned_games']]
    )

def __mongo_to_roll(roll : dict) -> CERoll :
    return CERoll(
        roll_name=roll['name'],
        init_time=roll['init_time'],
        due_time=roll['due_time'],
        completed_time=roll['completed_time'],
        games=roll['games'],
        user_ce_id=roll['user_ce_id'],
        partner_ce_id=roll['partner_ce_id'],
        rerolls=roll['rerolls'],
        status=roll['status']
    )

def __mongo_to_user_game(game : dict) -> CEUserGame :
    return CEUserGame(
        name=game['name'],
        ce_id=game['ce_id'],
        user_objectives=[__mongo_to_user_objective(obj) for obj in game['objectives']]
    )

def __mongo_to_user_objective(obj : dict) -> CEUserObjective :
    return CEUserObjective(
        ce_id=obj['ce_id'],
        game_ce_id=obj['game_ce_id'],
        name=obj['name'],
        type=obj['type'],
        user_points=obj['user_points']
    )


# -- inputs -- #
async def get_input(ce_id : str) -> CEInput :
    "Gets an input associated with `ce_id`."
    pass


# -- curator count -- #
async def get_curator_count() -> int :
    "Gets the current curator count."
    collection = _mongo_client['database_name'][V3MISCTITLE]

    db = await collection.find_one({"curator_count" : {"$exists": True}})
    return db['curator_count']

async def dump_curator_count(cc : int) :
    "Dumps the curator count."
    collection = _mongo_client['database_name'][V3MISCTITLE]

    result = await collection.update_one(
        {"curator_count": {"$exists": True}},  # Filter to find a document with "curator_count"
        {"$set": {"curator_count": cc}}  # Update to set "curator_count" to new_value
    )

    # Check if the document was found and updated
    if result.matched_count > 0:
        print("Document updated successfully.")
    else:
        print("No document with 'curator_count' found.")
    pass