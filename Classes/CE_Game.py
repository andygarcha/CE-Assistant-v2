import json
from typing import Literal

import requests
from Classes.CE_Objective import CEObjective
from Classes.OtherClasses import CECompletion, SteamData
import Modules.hm as hm

class CEGame:
    """A game that's on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 game_name : str,
                 platform : hm.platform_names,
                 platform_id : str,
                 category : str,
                 objectives : list[CEObjective],
                 last_updated : int):
        self._ce_id = ce_id
        self._game_name = game_name
        self._platform = platform
        self._platform_id = platform_id
        self._category = category
        self._objectives = objectives
        self._last_updated = last_updated

    # ----------- getters -------------
    
    def get_total_points(self) -> int :
        """Returns the total number of points this game has."""
        total_points = 0
        for objective in self.get_primary_objectives() :
            total_points += objective.point_value
        
        return total_points
    
    @property
    def ce_id(self) -> str :
        """Returns the Challenge Enthusiasts ID associated with this game."""
        return self._ce_id
    
    @property
    def game_name(self) -> str :
        """Returns the name of this game."""
        return self._game_name
    
    @property
    def platform(self) -> hm.platform_names :
        """Returns the platform this game is hosted on."""
        return self._platform
    
    @property
    def platform_id(self) -> str :
        """Returns the ID value of this game on its platform."""
        return self._platform_id
    
    @property
    def category(self) -> str :
        """Returns the category of this game (e.g. Action, Arcade, Strategy)."""
        return self._category
    
    @property
    def all_objectives(self) -> list[CEObjective] :
        """Returns the array of all `CEObjectives` in this game."""
        return self._objectives
    
    def get_primary_objectives(self) -> list[CEObjective] : 
        """Returns the array of CEObjectives that are Primary."""
        p = []
        for objective in self.all_objectives :
            if objective.type == "Primary" :
                p.append(objective)
        return p
    
    def get_primary_objective(self, ce_id : str) -> CEObjective | None :
        """Returns the :class:`CEObjective` object associated
        with `ce_id`, or `None` if none exist."""
        for objective in self.get_primary_objectives() :
            if objective.ce_id == ce_id : return objective
        return None
    
    def get_community_objectives(self) -> list[CEObjective] :
        """Returns the array of CEObjectives that are Community."""
        p = []
        for objective in self.all_objectives :
            if objective.type == "Community" :
                p.append(objective)
        return p
    
    def get_community_objective(self, ce_id : str) -> CEObjective | None:
        """Returns the :class:`CEObjective` object associated
        with `ce_id`, or `None` if none exist."""
        for objective in self.get_community_objectives() :
            if objective.ce_id == ce_id : return objective
        return None
    
    @property
    def last_updated(self) -> int :
        """Returns the unix timestamp of the last time this game was updated."""
        return self._last_updated
    
    def get_raw_ce_data(self) -> dict :
        "Returns the raw CE data."
        return json.loads(requests.get(f'https://cedb.me/api/game/{self.ce_id}').text)
    
    # ----------- setters -----------

    def add_objective(self, objective : CEObjective) :
        """Adds an objective to the game's objective arrays."""
        self._objectives.append(objective)
        
    @last_updated.setter
    def set_last_updated(self, last_updated : int) -> None :
        """Sets the last updated value to `last_updated`."""
        self._last_updated = last_updated
    

    # --------- helper functions ------------

    def is_t0(self) -> bool :
        """Returns true if the game is a Tier 0."""
        return self.get_total_points() == 0
    
    def is_unfinished(self) -> bool :
        "Returns true if `isFinished` is listed as `false` on the site."
        return not self.get_raw_ce_data()['isFinished']
    
    def get_tier(self) -> str :
        """Returns the tier (e.g. `"Tier 1"`) of this game."""
        total_points = self.get_total_points()
        if total_points >= 1000 : return "Tier 7"
        if total_points >= 500 : return "Tier 6"
        if total_points >= 200 : return "Tier 5"
        elif total_points >= 80 : return "Tier 4"
        elif total_points >= 40 : return "Tier 3"
        elif total_points >= 20 : return "Tier 2"
        elif total_points > 0 : return "Tier 1"
        else : return "Tier 0"

    def get_tier_num(self) -> int :
        "Returns the int value for the tier."
        return int(self.get_tier()[5])
    
    def is_t5plus(self) -> bool :
        "Returns true if this game is Tier 5 or above."
        #          tier num        >= 5
        return self.get_tier_num() >= 5

    def get_price(self) -> float :
        """Returns the current price (in USD) on the platform of choice."""
        if self.platform == "steam" :
            api_response = requests.get("https://store.steampowered.com/api/appdetails?",
                                        params = {'appids' : self.platform_id, 'cc' : 'US'})
            json_response = json.loads(api_response.text)

            steam_id = str(self.platform_id)

            if json_response[steam_id]['data']['is_free'] : 
                return 0
            elif 'price_overview' in json_response[steam_id]['data'] :
                return float(json_response[steam_id]['data']['price_overview']['final_formatted'][1::])
            else :
                return None
        return None
            
    def get_steamhunters_data(self) -> int | None :
        """Returns the average completion time on SteamHunters, or `None` if a) not a Steam game or b) no SteamHunters data."""
        if self.platform != "steam" : return None
        api_response = requests.get(f"https://steamhunters.com/api/apps/{self.platform_id}")
        if api_response.text == "null" or api_response.text == None :
            return None
        json_response = json.loads(api_response.text)

        if 'medianCompletionTime' in json_response :
            return int(int(json_response['medianCompletionTime']) / 60)
        else :
            return None
        
    def get_steam_data(self) -> SteamData | None : 
        """Returns the steam data for this game."""
        if self.platform != 'steam' : return None
        try :
            payload = {'appids' : self.platform_id, 'cc' : 'US'}
            response = requests.get("https://store.steampowered.com/api/appdetails?", 
                                    params = payload)
            return SteamData(json.loads(response.text))
        except :
            return None
        
    def get_completion_data(self) -> CECompletion :
        """Returns the completion data for this game."""
        json_response = json.loads(requests.get(f'https://cedb.me/api/game/{self.ce_id}/leaderboard').text)
        completions, started, owners = (0,)*3

        total_points = self.get_total_points()
        for user in json_response :
            if user['points'] == total_points : completions += 1
            elif user['points'] != 0 : started += 1
            owners += 1

        return CECompletion(
            {
                'completed' : completions,
                'started' : started,
                'total' : owners
            }
        )
    
    # --- emojis ---
    
    def get_category_emoji(self) -> str :
        "Returns the category emoji for this game."
        return "" + hm.get_emoji(self.category)
    
    def get_tier_emoji(self) -> str :
        "Returns the tier emoji for this game."
        return "" + hm.get_emoji(self.get_tier())
        
    def get_emojis(self) -> str :
        "Returns the tier and category emojis for this game."
        return self.get_tier_emoji() + self.get_category_emoji()

    def update(self, json_response : 'CEGame' = None) -> str | None :
        return NotImplemented
        import CEAPIReader
        json_response : dict | 'CEGame'
        """Takes in either a :class:`CEGame` or a :class:`dict`
        and uses that data to update this object.\n
        This method will return a :class:`str` that is to be sent
        to #game-additions if an update was warranted, or `None` if none."""
        if type(json_response) == dict :
            other = CEAPIReader._ce_to_game(json_response)
        elif json_response == None :
            other = CEAPIReader.get_api_page_data('game', self.ce_id)
        else :
            other = json_response

        if self.last_updated >= other.last_updated : 
            return None
        
        update_str = ""
        if self.get_total_points() != other.get_total_points() :
            # use hm.get_emoji("Points")
            update_str += (f"\n- {self.get_total_points()} <:CE_points:1128420207329816597> " +
            f"<:CE_points:1128420207329816597> {other.get_total_points()} " +
            f"<:CE_points:1128420207329816597>")
        #TODO: finish this function


    def has_an_uncleared(self) -> bool :
        """Returns true if this game has an uncleared objective."""
        for objective in self.get_primary_objectives() :
            if objective.is_uncleared() : return True
        return False

    
    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        objectives = []
        for objective in self.all_objectives :
            objectives.append(objective.to_dict())
        return {
            "Name" : self.game_name,
            "CE ID" : self.ce_id,
            "Platform" : self.platform,
            "Platform ID" : self.platform_id,
            "Category" : self.category,
            "Objectives" : objectives,
            "Last Updated" : self.last_updated
        }
    
    def __str__(self) :
        "Returns the string representation of this object."
        return (
            "-- CEGame --" +
            "\nGame Name: " + self.game_name +
            "\nGame CE ID: " + self.ce_id +
            "\nTotal Points: " + self.get_total_points() +
            "\nPlatform: " + self.platform +
            "\nPlatform ID: " + self.platform_id +
            "\nCategory: " + self.category +
            "\nObjectives: " + self.all_objectives +
            "\nLast Updated: " + self.last_updated
        )