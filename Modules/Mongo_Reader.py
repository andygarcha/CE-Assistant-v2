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
from Classes.CE_Game import CEAPIGame, CEGame
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

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

---- Everything from this line down is using database v3. ----

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

# VERSION 3
async def get_list(database : Literal["name", "user", "input"]) -> list[str] :
    "Returns a list of CE IDs in the specified database."
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
        #raise ValueError(f"No game with id {ce_id} found in mongo.")

    return __mongo_to_game(db)

async def get_database_name() -> list[CEGame] :
    collection = _mongo_client['database_name'][V3NAMETITLE]

    documents = []

    async for document in collection.find() :
        documents.append(__mongo_to_game(document))

    cursor = collection.find({}, {"_id" : 0})
    objects = await cursor.to_list(length=None)

    database_name : list[CEGame] = []
    for o in objects :
        database_name.append(__mongo_to_game(o))
    
    return database_name

async def dump_game(game : CEGame | CEAPIGame) :
    "Dumps a game."
    if type(game) is not CEGame and type(game) is not CEAPIGame :
        raise TypeError(f"Argument 'game' is of type {type(game)}, not CEGame.")
    
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
        objectives=[__mongo_to_objective(obj) for obj in game['objectives']],
        last_updated=game['last_updated']
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

async def get_user(ce_id : str, use_discord_id : bool = False) -> CEUser :
    "Gets a user associated with `ce_id`."
    collection = _mongo_client['database_name'][V3USERTITLE]
    if not use_discord_id :
        db = await collection.find_one({"ce_id" : ce_id})
    else :
        db = await collection.find_one({"discord_id" : ce_id})
    
    if db is None and use_discord_id : 
        raise ValueError(f"No user found with discord id {ce_id} in mongo.")
    elif db is None and not use_discord_id :
        raise ValueError(f"No user found with ce id {ce_id} in mongo.")

    return __mongo_to_user(db)

async def dump_user(user : CEUser) :
    "Dumps a user back to the backend."

    if type(user) is not CEUser :
        raise TypeError(f"Argument 'user' is of type {type(user)}, not CEUser.")

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
        except Exception as e : 
            print(e)
            continue
    
    return database_user

def __mongo_to_user(user : dict) -> CEUser :
    display_name : str = None
    if 'display-name' in user : display_name = user['display-name']
    elif 'display_name' in user : display_name = user['display_name']
    return CEUser(
        discord_id=user['discord_id'],
        ce_id=user['ce_id'],
        display_name=display_name,
        avatar=user['avatar'],
        rolls=[__mongo_to_roll(roll) for roll in user['rolls']],
        owned_games=[__mongo_to_user_game(game) for game in user['owned_games']],
        last_updated=user['last_updated']
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
    collection = _mongo_client['database_name'][V3INPUTTITLE]
    db = await collection.find_one({"ce_id" : ce_id})
    if db is None : 
        return None
        raise ValueError(f"Input with ID {ce_id} not found.")

    return __mongo_to_input(db)

async def dump_input(input : CEInput) :
    "Dumps an input."
    collection = _mongo_client['database_name'][V3INPUTTITLE]
    if (await collection.find_one({"ce_id" : input.ce_id})) == None :
        await collection.insert_one(input.to_dict())
    else :
        await collection.replace_one({"ce_id" : input.ce_id}, input.to_dict())
    pass

async def get_database_input() -> list[CEInput] :
    collection = _mongo_client['database_name'][V3INPUTTITLE]

    cursor = collection.find({}, {"_id" : 0})
    objects = await cursor.to_list(length=None)

    database_input : list[CEInput] = []
    for o in objects :
        try : database_input.append(__mongo_to_input(o))
        except Exception as e : 
            print(e.with_traceback())
            continue
    
    return database_input

def __mongo_to_input(i : dict) -> CEInput :
    return CEInput(
        game_ce_id=i['ce_id'],
        value_inputs=[__mongo_to_value_input(j) for j in i['value']],
        curate_inputs=[__mongo_to_curate_input(k) for k in i['curate']],
        tag_inputs=[__mongo_to_tag_input(l) for l in i['tags']]
    )

def __mongo_to_tag_input(i : dict) -> CETagInput :
    return CETagInput(
        user_ce_id=i['user_ce_id'],
        tags=i['tags']
    )

def __mongo_to_curate_input(i : dict) -> CECurateInput :
    return CECurateInput(
        user_ce_id=i['user_ce_id'],
        curate=i['curate']
    )

def __mongo_to_value_input(i : dict) -> CEValueInput :
    return CEValueInput(
        objective_ce_id=i['objective_ce_id'],
        individual_value_inputs=[__mongo_to_individual_value_input(j) for j in i['evaluations']]
    )

def __mongo_to_individual_value_input(i : dict) -> CEIndividualValueInput :
    return CEIndividualValueInput(
        i['user_ce_id'],
        i['recommendation']
    )


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




"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

---- Everything from this line down is using database v2. ----

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

_collection_v2 = _mongo_client['database_name']['ce-assistant-v2']
_mongo_names_v2 = Literal['name', 'user', 'curator', 'input']
mongo_ids_v2 = {
    'name' : ObjectId('66303f21918c91e3b67b33df'),
    'user' : ObjectId('66303f66918c91e3b67b33e0'),
    'curator' : ObjectId('66c7ef38a1c0c555afe139ec'),
    'input' : ObjectId('66f64983e65f770f71d4ac2e')
}

async def get_mongo_v2(title :_mongo_names_v2) :
    """Returns the MongoDB associated with `title`
    (without the `id` marker!)"""
    db = await _collection_v2.find_one({'_id' : mongo_ids_v2[title]})
    del db['_id']
    return db

async def dump_mongo_v2(title : _mongo_names_v2, data) :
    """Dumps the MongoDB given by `title` and passed by `data`."""
    if '_id' not in data : data['_id'] = mongo_ids_v2[title]
    return await _collection_v2.replace_one({'_id' : mongo_ids_v2[title]}, data)


def _mongo_to_game_objective_v2(objective : dict) -> CEObjective :
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





def _mongo_to_user_roll_v2(roll : dict, is_current : bool) -> CERoll :
    """Turns the MongoDB dictionary for a roll event 
    into a :class:`CERoll` object."""
    event_name, partner, games, init_time, due_time = (None,)*5
    completed_time, rerolls, user_id, winner = (None,)*4
    if 'Event Name' in roll : event_name = roll['Event Name']
    if 'User ID' in roll : user_id = roll['User ID']
    if 'Partner ID' in roll : partner = roll['Partner ID']
    if 'Games' in roll : games = roll['Games']
    if 'Init Time' in roll : init_time = roll['Init Time']
    if 'Due Time' in roll : due_time = roll['Due Time']
    if 'Completed Time' in roll : completed_time = roll['Completed Time']
    if 'Rerolls' in roll : rerolls = roll['Rerolls']
    if 'Winner' in roll : winner = roll["Winner"]

    if winner is None and is_current : status = "current"
    elif winner is None and not is_current : status = "won"
    elif winner is True : status = "won"
    elif winner is False : status = "failed"

    return CERoll(
        roll_name=event_name,
        user_ce_id=user_id,
        games=games,
        partner_ce_id=partner,
        init_time=init_time,
        due_time=due_time,
        completed_time=completed_time,
        rerolls=rerolls,
        status=status,
        is_current=False
    )


def _mongo_to_user_objective_v2(objective : dict) -> CEUserObjective :
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


def _mongo_to_user_game_v2(game : dict) -> CEUserGame :
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
        objectives.append(_mongo_to_user_objective_v2(objective))

    return CEUserGame(
        ce_id=game['CE ID'],
        name=game['Name'],
        user_objectives=objectives
    )


def _mongo_to_user_cooldown_v2(cooldown : dict) -> CECooldown :
    """Returns a CECooldown object."""
    return CECooldown(
        roll_name=cooldown['Event Name'],
        end_time=cooldown['End Time']
    )



def _mongo_to_user_v2(user : dict) -> CEUser :
    """Turns the MongoDB dictionary into a :class:`CEUser` object."""
    current_rolls : list[CERoll] = []
    for roll in user['Current Rolls'] :
        current_rolls.append(_mongo_to_user_roll_v2(roll, True))

    completed_rolls : list[CERoll] = []
    for roll in user['Completed Rolls'] :
        completed_rolls.append(_mongo_to_user_roll_v2(roll, False))

    cooldowns : list[CECooldown] = []
    for cooldown in user['Cooldowns'] :
        cooldowns.append(_mongo_to_user_cooldown_v2(cooldown))

    pending_rolls : list[CECooldown] = []
    for pending in user['Pending Rolls'] :
        pending_rolls.append(_mongo_to_user_cooldown_v2(pending))

    user_games : list[CEUserGame] = []
    for game in user['Owned Games'] :
        user_games.append(_mongo_to_user_game_v2(game))

    return CEUser(
        discord_id=user['Discord ID'],
        ce_id=user['CE ID'],
        owned_games=user_games,
        rolls=current_rolls + completed_rolls,
        display_name=(user['display-name'] if 'display-name' in user else ''),
        avatar=(user['avatar'] if 'avatar' in user else '')
    )



def _mongo_to_game_v2(game : dict) -> CEGame :
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
            game_objective = _mongo_to_game_objective_v2(
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




async def get_mongo_users_v2() -> list[CEUser] :
    """Returns a list of :class:`CEUser`'s pulled directly from the MongoDB database."""
    users : list[CEUser] = []
    database_user = await get_mongo_v2("user")
    for user in database_user['data'] :
        users.append(_mongo_to_user_v2(user))
    return users



async def get_mongo_games_v2() -> list[CEGame] :
    """Returns a list of :class:`CEGame`'s pulled directly from the MongoDB database."""
    games : list[CEGame] = []
    database_name = await get_mongo_v2('name')
    for game in database_name['data'] :
        games.append(_mongo_to_game_v2(game))
    return games

async def get_mongo_curator_count_v2() -> int :
    "Returns the Mongo curator count."
    data = await get_mongo_v2("curator")
    return data['curator_count']


async def dump_users_v2(users : list[CEUser]) -> None :
    """Takes in a list of :class:`CEUser`'s and dumps it back to the MongoDB database."""
    dictionary = []
    for user in users :
        dictionary.append(user.to_dict())
    await dump_mongo_v2('user', {'data' : dictionary})


async def dump_games_v2(games : list[CEGame]) -> None :
    """Takes in a list of :class:`CEGame`'s and dumps it back to the MongoDB database."""
    dictionary = []
    for game in games :
        dictionary.append(game.to_dict())
    await dump_mongo_v2('name', {'data' : dictionary})

async def dump_user_v2(user : CEUser | list[CEUser]) -> None :
    """Takes in one (or more) `CEUser`'s and dumps them."""
    if type(user) == CEUser : 
        user : list[CEUser] = [user]
    else :
        user : list[CEUser] = user

    database_user = await get_mongo_users_v2()

    for i, u in enumerate(database_user) :
        for b in user :
            if u.ce_id == b.ce_id :
                database_user[i] = b

    await dump_users_v2(database_user)


def __mongo_to_ceindividualvalueinput_v2(input : dict) -> CEIndividualValueInput :
    "Takes in a `dict` and returns a `CEIndividualValueInput`."
    return CEIndividualValueInput(
        user_ce_id=input['user-ce-id'], 
        value=input['recommendation']
    )

def __mongo_to_cevalueinput_v2(input : dict) -> CEValueInput :
    "Takes in a `dict` and returns a `CEValueInput`."
    objective_ce_id = input['objective-ce-id']
    individual_value_inputs : list[CEIndividualValueInput] = []
    for individual_value_input in input['evaluations'] :
        individual_value_inputs.append(__mongo_to_ceindividualvalueinput_v2(individual_value_input))

    return CEValueInput(
        objective_ce_id=objective_ce_id, 
        individual_value_inputs=individual_value_inputs
    )

def __mongo_to_cecurateinput_v2(input : dict) -> CECurateInput :
    "Takes in a `dict` and returns a `CECurateInput`."
    return CECurateInput(
        user_ce_id=input['user-ce-id'],
        curate=input['curate']
    )

def __mongo_to_cetaginput_v2(input : dict) -> CETagInput :
    "Takes in a `dict` and returns a `CETagInput`."
    return CETagInput(
        user_ce_id=input['user-ce-id'],
        tags=input['tags']
    )

def __mongo_to_ceinput_v2(input : dict) -> CEInput :
    "Takes in a dict and returns a `CEInput`."
    # get game id 
    ce_id = input['ce-id']

    # get all evaluations
    values : list[CEValueInput] = []
    for value in input['value'] :
        values.append(__mongo_to_cevalueinput_v2(value))
    
    # get all curates
    curates : list[CECurateInput] = []
    for curate in input['curate'] :
        curates.append(__mongo_to_cecurateinput_v2(curate))

    # get all tags
    tags : list[CETagInput] = []
    for tag in input['tags'] :
        tags.append(__mongo_to_cetaginput_v2(tag))

    return CEInput(
        game_ce_id=ce_id,
        value_inputs=values,
        curate_inputs=curates,
        tag_inputs=tags
)
    



async def get_inputs_v2() -> list[CEInput] :
    mongo_inputs = await get_mongo_v2("input")
    inputs : list[CEInput] = []
    for input in mongo_inputs['inputs'] :
        inputs.append(__mongo_to_ceinput_v2(input))

    return inputs

async def dump_inputs_v2(inputs : list[CEInput]) :
    input_dict_array = [] #[input.to_dict() for input in inputs]
    for input in inputs :
        input_dict_array.append(input.to_dict())
    await dump_mongo_v2('input', {'inputs' : input_dict_array})
    return

"""
async def dump_input(input : CEInput) :
    inputs = await get_inputs_v2()
    for i, input_object in enumerate(inputs) :
        if input_object.ce_id == input.ce_id :
            inputs[i] = input

    await dump_inputs_v2(inputs)
    return
"""