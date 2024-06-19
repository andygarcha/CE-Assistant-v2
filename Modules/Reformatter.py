"""
This module simply exists to move over the existing database_user 
to the new database_user. It will take in the old database,
make CEUser objects out of them, and then dump that into the new 
MongoDB databases.
"""
import bson.objectid
from Classes.CE_Game import CEGame
from Classes.CE_Objective import CEObjective
from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Cooldown import CECooldown
from Classes.CE_Roll import CERoll

def reformat_objective(dict, ce_id, is_community, game_ce_id) -> CEObjective :
    """Takes in a dict of an objective and returns a CEObjective object."""
    point_value, requirements, achievements, name = (None,)*4

    if 'Point Value' in dict : point_value = dict['Point Value']
    if 'Requirements' in dict : requirements = dict['Requirements']
    if 'Achievements' in dict :
        achievements = []
        for a in dict['Achievements'] :
            achievements.append(a)
    if 'Name' in dict : name = dict['Name']
    
    
    return CEObjective(
        ce_id=ce_id,
        objective_type="Community" if is_community else "Primary",
        description=dict['Description'],
        point_value=point_value,
        name=name,
        game_ce_id=game_ce_id,
        requirements=requirements,
        achievement_ce_ids=achievements
    )

def reformat_game(dict) -> CEGame :
    """Takes in a dict of a game and returns a CEGame object.

    Example
    --------
    ```
    "Name" : "Neon White",
    "CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
    "Platform" : "steam",
    "Platform ID" : "1533420",
    "Tier" : "Tier 3",
    "Genre" : "First-Person",
    "Primary Objectives" : {
        "2a7ad593-4afd-4470-b709-f5ac6b4487e5" : {
            "Name" : "Demon Exterminator",
            "Point Value" : 30,
            "Description" : "Clear White's Hell Rush.",
            "Achievements" : {
                "bdd7146d-1bb2-480d-90c1-7590c12bc096" : "White's Hell Rush Complete"
            }
        },
        "a351dce1-ee51-4b55-a05b-38a74854a8be" : {
            "Name" : "I just keep getting better and better.",
            "Point Value" : 20,
            "Description" : "Earn all Red Medals.",
            "Requirements" : "Screenshot/GIF of level select pages."
        }
    },
    "Community Objectives" : {
        "b03b690b-0933-49ce-8422-87cf3dfa0f4e" : {
            "Name" : "Not bad for a dead guy, huh?",
            "Description" : "Reach a total time of 50:00.00 or less on the global leaderboard.",
            "Requirements" : "Screenshot of total time leaderboard (Main Hub > Believer's Park > Leaderboard)"
        }
    },
    "Last Updated" : 1711088343,
    "Full Completions" : 58,
    "Total Owners" : 256
    """


    objectives : list[CEObjective] = []
    for p in dict['Primary Objectives'] :
        objectives.append(reformat_objective(dict['Primary Objectives'][p], p, False, dict['CE ID']))
    for c in dict['Community Objectives'] :
        objectives.append(reformat_objective(dict['Community Objectives'][c], c, True, dict['CE ID']))

    return CEGame(
        ce_id=dict['CE ID'],
        game_name=dict['Name'],
        platform=dict['Platform'],
        platform_id=dict['Platform ID'],
        category=dict['Genre'],
        objectives=objectives,
        last_updated=dict['Last Updated']
    )

async def reformat_database_name() :
    import pymongo
    import bson
    from motor.motor_asyncio import AsyncIOMotorClient
    import Modules.Mongo_Reader as Mongo_Reader

    client = AsyncIOMotorClient("mongodb+srv://andrewgarcha:KUTo7dCtGRy4Nrhd@ce-cluster.inrqkb3.mongodb.net/?retryWrites=true&w=majority")
    collection = client['database_name']['ce-collection']

    database_name = await collection.find_one({'_id' : bson.ObjectId('6500f7d3b3e4253bef9f51e6')})
    del database_name['_id']

    game_objects : list[CEGame] = []
    for game in database_name :
        game_objects.append(reformat_game(database_name[game]))

    return await Mongo_Reader.dump_games(game_objects)


async def reformat_database_user() :
    import Modules.Mongo_Reader as Mongo_Reader
    import bson
    client = Mongo_Reader._mongo_client
    collection = client['database_name']['ce-collection']

    database_user = await collection.find_one({'_id' : bson.ObjectId('64f8bd1b094bdbfc3f7d0051')})
    del database_user['_id']

    user_objects : list[CEUser] = []
    for user in database_user :
        user_objects.append(reformat_user(database_user[user]))
    
    return await Mongo_Reader.dump_users(user_objects)

def reformat_user(user : dict) -> CEUser :
    """Reformats the user that follows the old structure.\n
    Example: 
    ```
    {
        CE ID: "82117366-ed79-4c76-aa11-1c0cc0b03150",
        Discord ID: 948841388617912382,
        Rank: "A Rank", 
        Reroll Tickets: 0,
        Casino Score: 1, 
        Owned Games : {},
        Cooldowns : {},
        Current Rolls : [],
        Completed Rolls : [],
        Pending Rolls : {}
    }
    ```
    """
    print(user)

    games : list[CEUserGame] = []
    cooldowns : list[CECooldown] = []
    currentrolls : list[CERoll] = []
    completedrolls : list[CERoll] = []
    pendings : list[CECooldown] = []

    for id in user['Owned Games'] :
        games.append(reformat_user_game(user["Owned Games"][id], id))
    for roll in user["Current Rolls"] :
        currentrolls.append(reformat_roll(roll, user["CE ID"], True))
    for roll in user["Completed Rolls"] :
        completedrolls.append(reformat_roll(roll, user['CE ID'], False))
    for cooldown in user['Cooldowns'] :
        cooldowns.append(CECooldown(
            cooldown, user['Cooldowns'][cooldown]
        ))
    for pending in user['Pending Rolls'] :
        pendings.append(CECooldown(
            pending, user['Pending Rolls'][pending]
        ))


    return CEUser(
        discord_id=user['Discord ID'],
        ce_id = user['CE ID'],
        casino_score=user['Casino Score'],
        owned_games=games,
        current_rolls=currentrolls,
        completed_rolls=completedrolls,
        pending_rolls=pendings,
        cooldowns=cooldowns
    )


def reformat_user_game(game : dict, game_ce_id : str) -> CEUserGame :
    """Reformats the user game that follows the old structure.\n
    Example:
    ```
    {
        d28e20d0-b092-45c6-8c5b-25e448b09215 : {
            Primary Objectives : {
                38613933-5280-4e52-b742-36f3608aa345 : 475,
                0a1f2de6-8a66-4ecb-8266-4796e057ee9e : 75,
                672d79a5-8cda-4aa9-8a74-fcfcb7422fdd : 60,
                03482217-5ccf-4580-b798-959f3aa135ac : 25,
                067b678c-cf9e-4ce0-9e61-f15757b2eec0 : 15
            },
            Community Objectives {
                5da196f8-f65f-4028-8ff1-0194167df5c2 : True
            }
        }
    }
    """
    all_objectives : list[CEUserObjective] = []
    if 'Primary Objectives' in game :
        for id in game['Primary Objectives'] :
            all_objectives.append(
                CEUserObjective(
                    ce_id=id,
                    game_ce_id = game_ce_id,
                    type="Primary",
                    user_points=game['Primary Objectives'][id],
                    name="N/A"
                )
            )
    if 'Community Objectives' in game :
        for id in game['Community Objectives'] :
            all_objectives.append(
                CEUserObjective(
                    ce_id=id,
                    game_ce_id=game_ce_id,
                    type="Community",
                    user_points=game['Community Objectives'][id],
                    name="N/A"
                )
            )

    return CEUserGame(
        ce_id=game_ce_id,
        user_objectives=all_objectives,
        name="N/A"
    )

def reformat_roll(roll : dict, user_ce_id : str, current : bool) -> CERoll :
    """Reformats the old version of a roll to the current method. 
    
    Example:
    ```
    {
        "Event Name" : "One Hell of a Day",
        "Games" : [],
        "End Time" : 499163793,
        "Partner" : "eebbf608-18b4-4f40-9bbb-1c49b9c64fe0",
        "Rerolls" : 2
    }
    ```
    
    """
    return CERoll(
        roll_name=roll["Event Name"],
        user_ce_id=user_ce_id,
        games=roll["Games"] if "Games" in roll else None,
        partner_ce_id=roll["Partner"] if "Partner" in roll else None,
        init_time=0,
        due_time=roll["End Time"] if ("End Time" in roll and current) else None,
        completed_time=roll["End Time"] if ("End TIme" in roll and not current) else None,
        rerolls=roll["Rerolls"] if "Rerolls" in roll else None,
        is_current=False
    )