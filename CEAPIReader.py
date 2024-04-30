"""
This module is dedicated to interactions with the Challenge Enthusiasts API.

To pull data from individual game or user pages, use `get_api_page_data()`.

To pull data from all games on the site, use `get_api_games_full()`.

To pull data from all users on the site, use `get_api_users_all()`.
"""

import datetime
import time
from typing import Literal
from CE_Game import CEGame
from CE_Objective import CEObjective
from CE_User_Objective import CEUserObjective
from CE_User import CEUser
from CE_User_Game import CEUserGame
from CE_Cooldown import CECooldown
from FailedScrapeException import FailedScrapeException
import requests
import json


# ---------------------- module for ce-api maintenance -----------------------

def _timestamp_to_unix(input : str) :
    """Takes in the Challenge Enthusiasts timestamp (`"2024-02-25T07:04:38.000Z"`) 
    and converts it to unix timestamp (`1708862678`)"""
    return int(time.mktime(datetime.datetime.strptime(str(input[:-5:]), "%Y-%m-%dT%H:%M:%S").timetuple()))



def _ce_to_game(json_response : dict) -> CEGame :
    """Takes in a :class:`dict` pulled from the Challenge Enthusiasts API
    and returns a :class:`CEGame` object from it."""

    # Step 1: iterate through all of the objectives and make two separate arrays.
    all_primary_objectives : list[CEObjective] = []
    all_community_objectives : list[CEObjective] = []
    for objective in json_response['objectives'] :

        # Step 2: iterate through all the objective requirements and sort those as well.
        requirements : str | None = None
        achievement_ids : list[str] | None = []
        for requirement in objective['objectiveRequirements'] :
            if requirement['type'] == "achievement" : 
                achievement_ids.append(requirement['id'])
            elif requirement['type'] == "custom" : 
                requirements : str | None = requirement['data']
        
        # if no achievement ids were found, send it as None in the constructor.
        if achievement_ids == [] : achievement_ids = None

        # make the actual objective object...
        ce_objective = CEObjective(
            ce_id=objective['id'],
            is_community=objective['community'],
            description=objective['description'],
            point_value=objective['points'],
            name=objective['name'],
            game_ce_id=json_response['id'],
            requirements=requirements,
            achievement_ce_ids=achievement_ids,
            point_value_partial=objective['pointsPartial']
        )
        
        # ...and assign it to the correct array.
        if ce_objective.is_community() : all_community_objectives.append(ce_objective)
        else : all_primary_objectives.append(ce_objective)

    last_updated = _timestamp_to_unix(json_response['updatedAt'])
    for objective in json_response['objectives'] :
        if _timestamp_to_unix(objective['updatedAt']) > last_updated:
            last_updated = _timestamp_to_unix(objective['updatedAt'])
        for objreq in objective['objectiveRequirements'] :
            if _timestamp_to_unix(objreq['updatedAt']) > last_updated :
                last_updated = _timestamp_to_unix(objreq['updatedAt'])

    # now that we have all objectives, we can make the object...
    ce_game = CEGame(
        ce_id=json_response['id'],
        game_name=json_response['name'],
        platform=json_response['platform'],
        platform_id=json_response['platformId'],
        category=json_response['genre']['name'],
        primary_objectives=all_primary_objectives,
        community_objectives=all_community_objectives,
        last_updated=last_updated
    )
    
    # ... and return it.
    return ce_game




def get_api_games_full() -> list[CEGame] | None :
    """Returns an array of :class:`CEGame`'s grabbed from https://cedb.me/api/games/full"""
    # Step 1: get the big json intact.
    json_response = []
    done_fetching : bool = False
    i = 1
    try:
        while (not done_fetching) :
            api_response = requests.get("https://cedb.me/api/games/full?limit=100&" 
                                        + f"offset={(i-1)*100}")
            j = json.loads(api_response.text)
            json_response += j
            done_fetching = len(j) == 0
            i += 1
    except : 
        raise FailedScrapeException(f"Scraping failed from api/games/full " 
                                    + f"on games {(i-1)*100} through {i*100-1}.")

    # Step 2: iterate through the new json and construct an array of CEGame's.
    all_games : list[CEGame] = []
    for game in json_response :

        # if the game is unfinished, come back.
        if not game['isFinished'] : continue

        # grab the object
        ce_game = _ce_to_game(game)

        # ... and append it to the list.
        all_games.append(ce_game)
    return all_games




def get_api_users_all() -> list[CEUser] | None :
    """Returns an array of :class:`CEUser`'s grabbed from https://cedb.me/api/users/all"""

    # Step 1: get the big json intact.
    json_response = []
    done_fetching : bool = False
    i = 1
    try :
        while (not done_fetching) :
            api_response = requests.get(f"https://cedb.me/api/users/all?limit=100" 
                                        + f"&offset={(i-1)*100}")
            j = json.loads(api_response.text)
            json_response += j
            done_fetching = len(j) == 0
            i += 1
    except : 
        raise FailedScrapeException("Failed scraping from api/users/all/ for users "
                                    + f"on users {(i-1)*100} through {i*100-1}")




def get_api_page_data(type : Literal["user", "game"], ce_id : str) -> CEUser | CEGame | None :
    """Returns either a :class:`CEUser` or a :class:`CEGame` 
    from `ce_id` depending on `type`."""
    # if type is user
    if type == "user" :
        json_response = json.loads((requests.get(f"https://cedb.me/api/user/{ce_id}")).text)
        if len(json_response) == 0 : return None

        # Go through all of their games and make CEUserGame's out of them.
        user_games : list[CEUserGame] = []
        for game in json_response['userGames'] :
            user_games.append(
                CEUserGame(
                    ce_id=game['game']['id'],
                    user_primary_objectives=[],
                    user_community_objectives=[],
                    name=game['game']['name']
                )
            )
            
        # Now go through all their objectives and make CEUserObjective's out of them.
        for objective in json_response['userObjectives'] :
            if not objective['partial'] :
                user_points = objective['objective']['points']
            else :
                user_points = objective['objective']['pointsPartial']
            
            new_objective = CEUserObjective(
                ce_id = objective['objective']['id'],
                game_ce_id=objective['objective']['gameId'],
                is_community=objective['objective']['community'],
                user_points=user_points,
                name=objective['objective']['name']
            )
            new_objective = CEUserObjective(objective['objective']['id'], 
                                              objective['objective']['gameId'], 
                                              objective['objective']['community'], 
                                              user_points,
                                              name=objective['objective']['name'])

            # now that we have the objective
            # we need to assign it to the correct games
            for ce_game in user_games :
                if ce_game.get_ce_id() == new_objective.get_game_ce_id() : 
                    ce_game.add_user_objective(new_objective)
                    break

        return CEUser(0, json_response['id'], 0, user_games, [], [], [], [])

    elif type == "game" :
        json_response = json.loads((requests.get(f"https://cedb.me/api/game/{ce_id}")).text)
        return _ce_to_game(json_response)