"""
This module simply exists to move over the existing database_user 
to the new database_user. It will take in the old database,
"""
from CE_Game import CEGame
from CE_Objective import CEObjective
from CE_User import CEUser
from CE_User_Game import CEUserGame
from CE_User_Objective import CEUserObjective

def reformat_objective(dict, ce_id, is_community) -> CEObjective :
    """Takes in a dict of an objective and returns a CEObjective object."""
    point_value, requirements, achievements = (None,)*3
    
    return CEObjective(
        ce_id=ce_id,
        objective_type="Community" if is_community else "Primary",
        description=dict['Description'],

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
        objectives.append(reformat_objective(dict['Primary Objectives'][p], p, False))
    for c in dict['Community Objectives'] :
        objectives.append(reformat_objective(dict['Community Objectives'][c], c, True))

