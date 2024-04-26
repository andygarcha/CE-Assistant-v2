import datetime
import time
from typing import Literal
from CE_Game import CE_Game
from CE_Objective import CE_Objective
from CE_User_Objective import CE_User_Objective
from CE_User import CE_User
from CE_User_Game import CE_User_Game
import requests
import json

class CE_API_Reader:

    def _timestamp_to_unix(self, input : str) :
        """Takes in the Challenge Enthusiasts timestamp (`"2024-02-25T07:04:38.000Z"`) 
        and converts it to unix timestamp (`1708862678`)"""
        return int(time.mktime(datetime.datetime.strptime(str(input[:-5:]), "%Y-%m-%dT%H:%M:%S").timetuple()))


    def get_api_games_full(self) -> list[CE_Game] | None :
        """Returns an array of :class:`CE_Game`'s grabbed from https://cedb.me/api/games/full"""

        # Step 1: get the big json intact.
        json_response = []
        done_fetching : bool = False
        i = 1
        try:
            while (not done_fetching) :
                api_response = requests.get(f"https://cedb.me/api/games/full?limit=100&offset={(i-1)*100}")
                j = json.loads(api_response.text)
                json_response += j
                done_fetching = len(j) == 0
                i += 1
        except : return None

        # Step 2: iterate through the new json and construct an array of CE_Game's.
        all_games : list[CE_Game] = []
        for game in json_response :

            # if the game is unfinished, come back.
            if not game['isFinished'] : continue

            # Step 2.5: iterate through all of the objectives and make two separate arrays.
            all_primary_objectives : list[CE_Objective] = []
            all_community_objectives : list[CE_Objective] = []
            for objective in game :

                # Step 2.75: iterate through all the objective requirements and sort those as well.
                requirements : str = None
                achievement_ids : list[str] = []
                for requirement in objective :
                    if requirement['type'] == "achievement" : achievement_ids.append(requirement['id'])
                    elif requirement['type'] == "custom" : requirements = requirement['data']
                
                # if no achievement ids were found, send it as None in the constructor.
                if achievement_ids == [] : achievement_ids = None

                # make the actual objective object...
                ce_objective = CE_Objective(objective['id'], objective['community'], objective['description'],
                                            objective['points'], objective['name'], requirements, achievement_ids,
                                            objective['pointsPartial'])
                
                # ...and assign it to the correct array.
                if ce_objective.is_community() : all_community_objectives.append(ce_objective)
                else : all_primary_objectives.append(ce_objective)

            # now that we have all objectives, we can make the object...
            ce_game = CE_Game(game['id'], game['name'], game['platform'], game['platformId'], False,
                              all_primary_objectives, all_community_objectives, self._timestamp_to_unix(game['updatedAt']))
            # ... and append it to the list.
            all_games.append(ce_game)
        return all_games
    

    def get_api_page_data(self, type : Literal["user", "game"], ce_id : str) -> CE_User | CE_Game | None :
        """Returns either a :class:`CE_User` or a :class:`CE_Game` from `ce_id` depending on `type`."""
        # if type is user
        if type == "user" :
            json_response = json.loads((requests.get(f"https://cedb.me/api/user/{ce_id}")).text)

            # Go through all of their games and make CE_User_Game's out of them.
            user_games : list[CE_User_Game] = []
            for game in json_response['userGames'] :
                user_games.append(CE_User_Game(game['game']['id'], []))
                
            # Now go through all their objectives and make CE_User_Objective's out of them.
            for objective in json_response['userObjectives'] :
                user_points = objective['objective']['points'] if not objective['partial'] else objective['objective']['pointsPartial']
                new_objective = CE_User_Objective(objective['objective']['id'], objective['objective']['gameId'], objective['objective']['community'], user_points)

                # now that we have the objective
                # we need to assign it to the correct game
                for ce_game in user_games :
                    if ce_game.get_ce_id() == new_objective.get_game_ce_id() : 
                        ce_game.add_user_objective(new_objective)
                        break

            return CE_User(None, json_response['id'], None)
        
    def _mongo_to_game() :
        primary_objectives : list[CE_Objective] = []

