import json
from typing import Literal

import requests
from CE_Objective import CE_Objective

class CE_Game:
    """A game that's on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 game_name : str,
                 platform : str,
                 platform_id : str,
                 category : str,
                 primary_objectives : list[CE_Objective],
                 community_objectives : list[CE_Objective],
                 last_updated : int):
        self._ce_id = ce_id
        self._game_name = game_name
        self._platform = platform
        self._platform_id = platform_id
        self._category = category
        self._primary_objectives = primary_objectives
        self._community_objectives = community_objectives
        self._last_updated = last_updated

    # ----------- getters -------------
    
    def get_total_points(self) -> int :
        """Returns the total number of points this game has."""
        total_points = 0
        for objective in self._primary_objectives :
            total_points += objective.get_point_value()
        
        return total_points
    
    def get_ce_id(self) -> str :
        """Returns the Challenge Enthusiasts ID associated with this game."""
        return self._ce_id
    
    def get_game_name(self) -> str :
        """Returns the name of this game."""
        return self._game_name
    
    def get_platform(self) -> str :
        """Returns the platform this game is hosted on."""
        return self._platform
    
    def get_platform_id(self) -> str :
        """Returns the ID value of this game on its platform."""
        return self._platform_id
    
    def get_category(self) -> str :
        """Returns the category of this game (e.g. Action, Arcade, Strategy)."""
        return self._category
    
    def get_primary_objectives(self) -> list[CE_Objective] : 
        """Returns the array of CE_Objectives that are Primary."""
        return self._primary_objectives
    
    def get_community_objectives(self) -> list[CE_Objective] :
        """Returns the array of CE_Objectives that are Community."""
        return self._community_objectives
    
    def get_last_updated(self) -> int :
        """Returns the unix timestamp of the last time this game was updated."""
        return self._last_updated
    
    # ----------- setters -----------
    def add_objective(self, type : Literal["Primary", "Community"], objective : CE_Objective) :
        """Adds an objective to the game's objective arrays."""
        if type == "Primary" : self._primary_objectives.append(objective)
        elif type == "Community" : self._community_objectives.append(objective)
    

    # --------- helper functions ------------
    def is_t0(self) -> bool :
        """Returns true if the game is a Tier 0."""
        return self.get_total_points() == 0
    
    def get_tier(self) -> str :
        """Returns the tier (e.g. `"Tier 1"`) of this game."""
        total_points = self.get_total_points()
        if total_points >= 200 : return "Tier 5"
        elif total_points >= 80 : return "Tier 4"
        elif total_points >= 40 : return "Tier 3"
        elif total_points >= 20 : return "Tier 2"
        elif total_points > 0 : return "Tier 1"
        else : return "Tier 0"

    def get_price(self) -> float :
        """Returns the current price (in USD) on the platform of choice."""
        if self.get_platform() == "steam" :
            api_response = requests.get("https://store.steampowered.com/api/appdetails?",
                                        params = {'appids' : self.get_platform_id(), 'cc' : 'US'})
            json_response = json.loads(api_response.text)

            steam_id = str(self.get_platform_id())

            if json_response[steam_id]['data']['is_free'] : 
                return 0
            elif 'price_overview' in json_response[steam_id]['data'] :
                return float(json_response[steam_id]['data']['price_overview']['final_formatted'][1::])
            else :
                return None
            
    def get_steamhunters_data(self) -> int | None :
        """Returns the average completion time on SteamHunters, or `None` if a) not a Steam game or b) no SteamHunters data."""
        if self.get_platform() != "steam" : return None
        api_response = requests.get(f"https://steamhunters.com/api/apps/{self.get_platform_id()}")
        json_response = json.loads(api_response.text)

        if 'medianCompletionTime' in json_response :
            return int(json_response['medianCompletionTime'] / 60)
        else :
            return None

    
    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        primary_objective_dict = []
        community_objective_dict = []
        for objective in self.get_primary_objectives() :
            if objective.is_community() :
                community_objective_dict.append(objective.to_dict)
            else :
                primary_objective_dict.append(objective.to_dict())
        return {
            self.get_ce_id() : {
                "Name" : self.get_game_name(),
                "CE ID" : self.get_ce_id(),
                "Platform" : self.get_platform(),
                "Platform ID" : self.get_platform_id(),
                "Category" : self.get_category(),
                "Primary Objectives" : primary_objective_dict,
                "Community Objectives" : community_objective_dict,
                "Last Updated" : self.get_last_updated()
            }
        }