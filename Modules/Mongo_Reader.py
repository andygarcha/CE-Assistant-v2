"""
Handles all MongoDB-related interactions for CE Assistant v2.
Version 3 : Object-Oriented, and each item has its own document.
"""

# imports
import logging
import os
import uuid
from typing import Literal

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# -- local --
from Classes.CE_Game import CEAPIGame, CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_Roll import CERoll
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.OtherClasses import (
    CECurateInput,
    CEIndividualValueInput,
    CEInput,
    CETagInput,
    CEValueInput,
)

logger = logging.getLogger(__name__)

# open .env
load_dotenv()
_uri = os.getenv("MONGODB_URI")

_mongo_client = AsyncIOMotorClient(_uri)
V3NAMETITLE = "database-name-v3"
V3USERTITLE = "database-user-v3"
V3INPUTTITLE = "database-input-v3"
V3MISCTITLE = "database-misc-v3"

"""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """
""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """"""


"""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """

---- Everything from this line down is using database v3. ----

""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """"""


"""""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """
""" """""" """""" """""" """""" """""" """""" """""" """""" """""" """"""


# VERSION 3
async def get_list(database: Literal["name", "user", "input"]) -> list[str]:
    "Returns a list of CE IDs in the specified database."
    if database == "name":
        collection = _mongo_client["database_name"][V3NAMETITLE]
    elif database == "user":
        collection = _mongo_client["database_name"][V3USERTITLE]
    elif database == "input":
        collection = _mongo_client["database_name"][V3INPUTTITLE]

    cursor = collection.find({}, {"ce_id": 1, "_id": 0})
    ce_ids = await cursor.to_list(length=None)

    ce_id_values = [doc["ce_id"] for doc in ce_ids if "ce_id" in doc]
    return ce_id_values


# -- games -- #
async def get_game(ce_id: str) -> CEGame | None:
    "Gets a game associated with `ce_id`."
    collection = _mongo_client["database_name"][V3NAMETITLE]

    db = await collection.find_one({"ce_id": ce_id})
    if db is None:
        return None
        # raise ValueError(f"No game with id {ce_id} found in mongo.")

    return __mongo_to_game(db)


async def get_database_name() -> list[CEGame]:
    collection = _mongo_client["database_name"][V3NAMETITLE]

    documents = []

    async for document in collection.find({}, {"_id": 0}):
        documents.append(__mongo_to_game(document))

    return documents

    cursor = collection.find({}, {"_id": 0})
    objects = await cursor.to_list(length=None)

    database_name: list[CEGame] = []
    for o in objects:
        database_name.append(__mongo_to_game(o))

    return database_name


async def dump_game(game: CEGame | CEAPIGame):
    "Dumps a game."
    if type(game) is not CEGame and type(game) is not CEAPIGame:
        raise TypeError(f"Argument 'game' is of type {type(game)}, not CEGame.")

    collection = _mongo_client["database_name"][V3NAMETITLE]

    if (await collection.find_one({"ce_id": game.ce_id})) is None:
        await collection.insert_one(game.to_dict())
    else:
        await collection.replace_one({"ce_id": game.ce_id}, game.to_dict())
    pass


async def delete_game(ce_id: str):
    "Deletes a game."
    collection = _mongo_client["database_name"][V3NAMETITLE]

    result = await collection.delete_one({"ce_id": ce_id})
    if result.deleted_count == 0:
        raise Exception("Game not deleted properly.")


def __mongo_to_game(game: dict) -> CEGame:
    return CEGame(
        ce_id=game["ce_id"],
        game_name=game["name"],
        platform=game["platform"],
        platform_id=game["platform_id"],
        categories=[game["category"]],
        objectives=[__mongo_to_objective(obj) for obj in game["objectives"]],
        last_updated=game["last_updated"],
        banner=game["banner"],
    )


def __mongo_to_objective(obj: dict) -> CEObjective:
    return CEObjective(
        ce_id=obj["ce_id"],
        objective_type=obj["type"],
        description=obj["description"],
        point_value=obj["value"],
        name=obj["name"],
        game_ce_id=obj["game_ce_id"],
        requirements=obj["requirements"],
        achievement_ce_ids=obj["achievements"],
        point_value_partial=obj["partial_value"],
    )


# -- users -- #


async def get_user(ce_id: str, use_discord_id: bool = False) -> CEUser:
    "Gets a user associated with `ce_id`."
    collection = _mongo_client["database_name"][V3USERTITLE]
    if not use_discord_id:
        db = await collection.find_one({"ce_id": ce_id})
    else:
        db = await collection.find_one({"discord_id": ce_id})

    if db is None:
        if use_discord_id:
            raise ValueError(f"No user found with discord id {ce_id} in mongo.")
        else:
            raise ValueError(f"No user found with ce id {ce_id} in mongo.")

    return __mongo_to_user(db)


async def dump_user(user: CEUser):
    "Dumps a user back to the backend."

    if not isinstance(user, CEUser):
        raise TypeError(f"Argument 'user' is of type {type(user)}, not CEUser.")

    collection = _mongo_client["database_name"][V3USERTITLE]

    if (await collection.find_one({"ce_id": user.ce_id})) is None:
        await collection.insert_one(user.to_dict())
    else:
        await collection.replace_one({"ce_id": user.ce_id}, user.to_dict())
    return


async def get_database_user() -> list[CEUser]:
    collection = _mongo_client["database_name"][V3USERTITLE]

    cursor = collection.find({}, {"_id": 0})
    objects = await cursor.to_list(length=None)

    database_user: list[CEUser] = []
    for o in objects:
        try:
            database_user.append(__mongo_to_user(o))
        except Exception as e:
            logger.exception(e)
            continue

    return database_user


def __mongo_to_user(user: dict) -> CEUser:
    if user["discord_id"] is None:
        raise ValueError(
            f"You either called 'get_user(None)' or this user {user['ce_id']} was removed."
        )
    display_name: str = ""
    if "display-name" in user:
        display_name = user["display-name"]
    elif "display_name" in user:
        display_name = user["display_name"]
    return CEUser(
        discord_id=user["discord_id"],
        ce_id=user["ce_id"],
        display_name=display_name,
        avatar=user["avatar"],
        rolls=[__mongo_to_roll(roll) for roll in user["rolls"]],
        owned_games=[__mongo_to_user_game(game) for game in user["owned_games"]],
        last_updated=user["last_updated"],
        steam_id=user["steam_id"],
    )


def __mongo_to_roll(roll: dict) -> CERoll:
    return CERoll(
        roll_name=roll["name"],
        init_time=roll["init_time"],
        due_time=roll["due_time"],
        completed_time=roll["completed_time"],
        games=roll["games"],
        user_ce_id=roll["user_ce_id"],
        partner_ce_id=roll["partner_ce_id"],
        rerolls=roll["rerolls"],
        status=roll["status"],
        _id=str(uuid.uuid4()),
    )


def __mongo_to_user_game(game: dict) -> CEUserGame:
    return CEUserGame(
        name=game["name"],
        ce_id=game["ce_id"],
        user_objectives=[__mongo_to_user_objective(obj) for obj in game["objectives"]],
    )


def __mongo_to_user_objective(obj: dict) -> CEUserObjective:
    return CEUserObjective(
        ce_id=obj["ce_id"],
        game_ce_id=obj["game_ce_id"],
        name=obj["name"],
        type=obj["type"],
        user_points=obj["user_points"],
    )


# -- inputs -- #
async def get_input(ce_id: str) -> CEInput | None:
    "Gets an input associated with `ce_id`."
    collection = _mongo_client["database_name"][V3INPUTTITLE]
    db = await collection.find_one({"ce_id": ce_id})
    if db is None:
        return None
        raise ValueError(f"Input with ID {ce_id} not found.")

    return __mongo_to_input(db)


async def dump_input(input: CEInput):
    "Dumps an input."
    collection = _mongo_client["database_name"][V3INPUTTITLE]
    if (await collection.find_one({"ce_id": input.ce_id})) is None:
        await collection.insert_one(input.to_dict())
    else:
        await collection.replace_one({"ce_id": input.ce_id}, input.to_dict())
    pass


async def get_database_input() -> list[CEInput]:
    collection = _mongo_client["database_name"][V3INPUTTITLE]

    cursor = collection.find({}, {"_id": 0})
    objects = await cursor.to_list(length=None)

    database_input: list[CEInput] = []
    for o in objects:
        try:
            database_input.append(__mongo_to_input(o))
        except Exception as e:
            logger.exception(e)
            continue

    return database_input


def __mongo_to_input(i: dict) -> CEInput:
    return CEInput(
        game_ce_id=i["ce_id"],
        value_inputs=[__mongo_to_value_input(j) for j in i["value"]],
        curate_inputs=[__mongo_to_curate_input(k) for k in i["curate"]],
        tag_inputs=[__mongo_to_tag_input(m) for m in i["tags"]],
    )


def __mongo_to_tag_input(i: dict) -> CETagInput:
    return CETagInput(user_ce_id=i["user_ce_id"], tags=i["tags"])


def __mongo_to_curate_input(i: dict) -> CECurateInput:
    return CECurateInput(user_ce_id=i["user_ce_id"], curate=i["curate"])


def __mongo_to_value_input(i: dict) -> CEValueInput:
    return CEValueInput(
        objective_ce_id=i["objective_ce_id"],
        individual_value_inputs=[
            __mongo_to_individual_value_input(j) for j in i["evaluations"]
        ],
    )


def __mongo_to_individual_value_input(i: dict) -> CEIndividualValueInput:
    return CEIndividualValueInput(i["user_ce_id"], i["recommendation"])


# -- curator count -- #
async def get_curator_count() -> int:
    "Gets the current curator count."
    collection = _mongo_client["database_name"][V3MISCTITLE]

    db = await collection.find_one({"curator_count": {"$exists": True}})
    if db is None:
        raise Exception("No curator count found.")
    return db["curator_count"]


async def dump_curator_count(cc: int):
    "Dumps the curator count."
    collection = _mongo_client["database_name"][V3MISCTITLE]

    result = await collection.update_one(
        {
            "curator_count": {"$exists": True}
        },  # Filter to find a document with "curator_count"
        {"$set": {"curator_count": cc}},  # Update to set "curator_count" to new_value
    )

    # Check if the document was found and updated
    if result.matched_count > 0:
        logger.info("Document updated successfully.")
    else:
        logger.warning("No document with 'curator_count' found.")


async def dump_curator_ids(ids: list[str]):
    collection = _mongo_client["database_name"][V3MISCTITLE]

    result = await collection.find_one({"curated": {"$exists": True}})
    if result is None:
        raise Exception("Could not find curated list in MongoDB.")

    mongoids: list[str] = result["curated"]
    for idnum in ids:
        if idnum not in mongoids:
            mongoids.append(idnum)

    logger.debug("Updated curator ids: %s", mongoids)

    await collection.replace_one({"curated": {"$exists": True}}, {"curated": mongoids})


async def get_curator_ids():
    collection = _mongo_client["database_name"][V3MISCTITLE]

    db = await collection.find_one({"curated": {"$exists": True}})
    if db is None:
        raise Exception("Could not find curator ids in get_curator_ids.")
    return db["curated"]


async def get_database_tier():
    collection = _mongo_client["database_name"][V3MISCTITLE]

    db = await collection.find_one({"database_tier": {"$exists": True}})
    if db is None:
        raise Exception("Could not find db tier in get_database_tier")
    return db["database_tier"]


async def dump_database_tier(database_tier: dict):
    "Dumps the curator count."
    collection = _mongo_client["database_name"][V3MISCTITLE]

    result = await collection.update_one(
        {"database_tier": {"$exists": True}}, {"$set": {"database_tier": database_tier}}
    )

    # Check if the document was found and updated
    if result.matched_count > 0:
        logger.info("Database Tier document updated successfully.")
    else:
        logger.warning("No document with 'database_tier' found.")
