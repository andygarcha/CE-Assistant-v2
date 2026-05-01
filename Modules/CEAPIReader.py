"""
This module is dedicated to interactions with the Challenge Enthusiasts API.

To pull data from individual game or user pages, use `get_api_page_data()`.

To pull data from all games on the site, use `get_api_games_full()`.

To pull data from all users on the site, use `get_api_users_all()`.
"""

import asyncio
import datetime
import functools
import time
from typing import Literal
import typing

import aiohttp
from Modules import http_session

# -- local --
from Classes.CE_Game import CEAPIGame
from Classes.CE_Objective import CEObjective
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_User import CEUser, CEAPIUser
from Classes.CE_User_Game import CEUserGame
from Exceptions.FailedScrapeException import FailedScrapeException

# -- other --
import requests
import json


# ---------------------- module for ce-api maintenance -----------------------

def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper

def _timestamp_to_datetime(input : str) -> datetime.datetime:
    """Takes in the Challenge Enthusiasts timestamp (`"2024-02-25T07:04:38.000Z"`) 
    and converts it to a datetime object."""
    return datetime.datetime.fromisoformat(str(input[:-5]) + "+00:00")





def _ce_to_game(json_response : dict) -> CEAPIGame :
    """Takes in a :class:`dict` pulled from the Challenge Enthusiasts API
    and returns a :class:`CEAPIGame` object from it."""

    # Step 1: iterate through all of the objectives and make two separate arrays.
    all_objectives : list[CEObjective] = []
    for objective in json_response['objectives'] :

        # Step 2: iterate through all the objective requirements and sort those as well.
        requirements : str | None = None
        achievement_ids : list[str] | None = []
        for requirement in objective['objectiveRequirements'] :
            if requirement['type'] == "achievement" : 
                achievement_ids.append(requirement['data'])
            elif requirement['type'] == "custom" : 
                requirements : str | None = requirement['data']
        
        # if no achievement ids were found, send it as None in the constructor.
        if achievement_ids == [] : achievement_ids = None

        # make the actual objective object...
        ce_objective = CEObjective(
            ce_id=objective['id'],
            objective_type=str(objective['type']).capitalize(), 
            description=objective['description'],
            point_value=objective['points'],
            name=objective['name'],
            game_ce_id=json_response['id'],
            requirements=requirements,
            achievement_ce_ids=achievement_ids,
            point_value_partial=objective['pointsPartial']
        )
        
        # ...and assign it to the array.
        all_objectives.append(ce_objective)

    last_updated = _timestamp_to_datetime(json_response['updatedAt'])
    for objective in json_response['objectives'] :
        if _timestamp_to_datetime(objective['updatedAt']) > last_updated:
            last_updated = _timestamp_to_datetime(objective['updatedAt'])
        for objreq in objective['objectiveRequirements'] :
            if _timestamp_to_datetime(objreq['updatedAt']) > last_updated :
                last_updated = _timestamp_to_datetime(objreq['updatedAt'])

    # now that we have all objectives, we can make the object...
    ce_game = CEAPIGame(
        ce_id=json_response['id'],
        game_name=json_response['name'],
        platform=json_response['platform'],
        platform_id=json_response['platformId'],
        category=json_response['genre']['name'],
        objectives=all_objectives,
        last_updated=last_updated,
        full_data=json_response,
        banner=json_response['header']
    )
    
    # ... and return it.
    return ce_game


async def get_game(ce_id: str) -> CEAPIGame:
    session = await http_session.get_session()

    async with session.get(f'https://cedb.me/api/game/{ce_id}') as response:
        game = await response.json()

        return _ce_to_game(game)
    
async def get_user(ce_id: str) -> CEUser:
    session = await http_session.get_session()

    async with session.get(f"https://cedb.me/api/user/{ce_id}") as response:
        user = await response.json()
        return _ce_to_user(user)

async def get_api_games() -> list[str]:
    session = await http_session.get_session()

    async with session.get(f'https://cedb.me/api/games') as response:
        games = await response.json()

        return [g['id'] for g in games]
    
async def get_objective_ids() -> list[str]:
    # DELETE THIS IF THE ENDPOINT EVER GETS MADE!
    raise NotImplementedError

    session = await http_session.get_session()

    async with session.get("WHATEVER THE ENDPOINT IS!") as response:
        objectives = await response.json()

        return [o['id'] for o in objectives]

async def get_api_games_full(return_json = False) -> list[CEAPIGame] :
    """Returns an array of :class:`CEAPIGame`'s grabbed from https://cedb.me/api/games/full"""
    # Step 1: get the big json intact.
    PULL_LIMIT = 50 #grab this many games per API call
    TRY_LIMIT = 3 # try each batch of 'PULL LIMIT' this many times
    json_response = []
    done_fetching : bool = False
    i = 1
    
    session = await http_session.get_session()

    #overarching while statement - if not done, keep going
    while (not done_fetching):
        
        print(f"fetching games {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1}...", end=" ")
        
        #for each iteration (PULL_LIMIT), allow the site to be queried a few times in case of failure
        for x in range(TRY_LIMIT):

            # set up a variable used to catch errors
            str_error = None
            outer_response = None

            # try to call the API
            try:
                async with session.get(f"https://cedb.me/api/games/full?limit={PULL_LIMIT}&offset={(i-1)*PULL_LIMIT}") as response :
                    outer_response = response
                    j = await response.json()
                    json_response += j
                    done_fetching = len(j) == 0
                    i += 1
            
            # if we got an error from the API call, set "str_error" to a value to enable the error catch/retry below
            except Exception as e:
                str_error = e
                pass
            
            
            # if an error, print a message and try again until TRY_LIMIT attempts completed for this batch of PULL_LIMIT games
            if str_error:
                print(str_error)
                try :
                    print(await outer_response.text())
                except : print('couldnt print response')
                print(f"Scraping failed from api/games/full on games {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1}." + " Attempt " + str(x+1) + " of " + str(TRY_LIMIT))
        
                # if this block of games have failed TRY_LIMIT times, throw an exception and go to sleep
                if x+1 == TRY_LIMIT:
                    raise FailedScrapeException("Scraping failed from api/games/full " 
                                        + f"on games {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1}.")

            # if no error - continue on to the next block of "PULL LIMIT" games
            else:
                break
            
    print(f"\ndone fetching games! total games: {len(json_response)}")

    """"
    BIG ASS FUCKING NOTE
    you are going to have to skip some of the games if they're not `isFinished`
    the bot should effectively freeze the game in place. just copy it over from when it existed last.
    """

    if return_json: return json_response

    # Step 2: iterate through the new json and construct an array of CEAPIGame's.
    all_games : list[CEAPIGame] = []
    for game in json_response :

        # grab the object
        ce_game = _ce_to_game(game)

        # ... and append it to the list.
        all_games.append(ce_game)
    
    # and return
    return all_games



async def get_api_users_all(database_user : list[CEUser] | list[str] = None) -> list[CEUser]:
    """Returns an array of :class:`CEUser`'s grabbed from https://cedb.me/api/users/all.
    NOTE: if `database_user` is passed, this will only return the users who are CEA Registered.
    You can pass in the entire database_user here, or just a list of registered ids. Either work."""

    # Step 0: check if database_user was passed
    if database_user is not None and len(database_user) > 0 :
        registered_ids : list[str] = []
        if type(database_user[0]) == CEUser :
            registered_ids = [user.ce_id for user in database_user]
        elif type(database_user[0]) == str :
            registered_ids = database_user
        else :
            database_user = None


    # Step 1: get the big json intact.
    PULL_LIMIT = 50
    total_response = []
    done_fetching : bool = False
    i = 1
    session = await http_session.get_session()
    try :

        # this will run if database user has been provided
        if database_user is not None and False :
            while (not done_fetching) :
                
                # print
                print(f"fetching users {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1} from database_user")

                # set up data
                data = {'id' : registered_ids[((i-1)*PULL_LIMIT), i*PULL_LIMIT-1]}

                # pull the data and json-ify it
                api_response = requests.post("https://cedb.me/api/users/query", data=data)
                current_response = json.loads(api_response.text)

                # check if you're done fetching
                done_fetching = len(current_response) == 0

                # add this to the total response and increment i
                total_response += current_response
                i += 1

        # this will run if database user wasn't provided
        while (not done_fetching) :

            # pull the data
            print(f"fetching users {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1}", end=" ")

            # set up params
            params = {"limit" : PULL_LIMIT, "offset" : (i-1)*PULL_LIMIT}
            """# if database_user has been provided, include the 'ids' in the payload.
            if database_user is not None : params['ids'] = registered_ids"""

            # pull the data and json-ify it
            async with session.get("https://cedb.me/api/users/all", params=params) as response :
                current_response = await response.json()

                # check to see if this is the last one
                done_fetching = len(current_response) == 0

                # go through and filter out users that aren't CEA registered if database_user is passed through
                if database_user is not None :
                    removed_indexes = []
                    # if the user isn't registered, add the index to remove indexes
                    for index, user in enumerate(current_response) :
                        if user['id'] not in registered_ids :
                            removed_indexes.append(index)
                    # remove all of the indexes in reverse order
                    for index in reversed(removed_indexes) :
                        del current_response[index]
                    print(f"({len(removed_indexes)} removed)", end=". ")

                # print this so that there will be a new line
                else :
                    print("")

                # add to the total response and increment i
                total_response += current_response
                i += 1
    except Exception as e : 
        print(f"original exception: {e}")
        raise FailedScrapeException("Failed scraping from api/users/all/ "
                                    + f"on users {(i-1)*PULL_LIMIT} through {i*PULL_LIMIT-1}")
    print(f"done fetching users! total users: {len(total_response)}")

    # convert to objects
    all_users : list[CEUser] = []
    for user in total_response :
        all_users.append(_ce_to_user(user))

    # free up space
    del total_response

    # and return
    return all_users



def _ce_to_user(json_response : dict) -> CEUser :
    # Go through all of their games and make CEUserGame's out of them.
    user_games : list[CEUserGame] = []
    for game in json_response['userGames'] :
        user_games.append(
            CEUserGame(
                ce_id=game['game']['id'],
                user_objectives=[],
                name=game['game']['name']
            )
        )


    """ok
    ok now yal
    if a game turns not `isFinished`
    then copy the game over from mongo if it's there
    same thing with the objectives
    that's just the way it is now
    if it doesn't exist there anywya then skip!
    """

    steam_id = "None"

    for item in json_response['userConnections'] :
        if item['platform'] != 'steam' : continue
        steam_id = item['platformId']
        
    # Now go through all their objectives and make CEUserObjective's out of them.
    for objective in json_response['userObjectives'] :
        if not objective['partial'] :
            user_points = objective['objective']['points']
        else :
            user_points = objective['objective']['pointsPartial']

        new_objective = CEUserObjective(
            ce_id = objective['objective']['id'],
            game_ce_id=objective['objective']['gameId'],
            # NOTE: OBJECTIVE TYPE FIX
            type='Community' if objective['objective']['community'] else 'Primary',
            user_points=user_points,
            name=objective['objective']['name']
        )

        # now that we have the objective
        # we need to assign it to the correct games
        for ce_game in user_games :
            if ce_game.ce_id == new_objective.game_ce_id : 
                ce_game.add_user_objective(new_objective)
                break

    return CEUser(
        discord_id=0,
        ce_id = json_response['id'],
        owned_games = user_games,
        rolls=[],
        display_name=json_response['displayName'],
        avatar=json_response['avatar'],
        last_updated=0,
        steam_id=steam_id
    )



async def get_api_page_data(type : Literal["user", "game"], ce_id : str) -> CEUser | CEAPIGame | None :
    """Returns either a :class:`CEUser` or a :class:`CEAPIGame` 
    from `ce_id` depending on `type`."""
    session = await http_session.get_session()
    # if type is user
    if type == "user" :
        async with session.get(f"https://cedb.me/api/user/{ce_id}") as response :
            json_response = await response.json()
            if len(json_response) == 0 : return None
            return _ce_to_user(json_response=json_response)

    elif type == "game" :
        async with session.get(f"https://cedb.me/api/game/{ce_id}") as response :
            json_response = await response.json()
            if len(json_response) == 0 : return None
            return _ce_to_game(json_response=json_response)
