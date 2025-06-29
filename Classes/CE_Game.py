
import aiohttp
from Classes.CE_Objective import CEObjective
from Classes.OtherClasses import CECompletion
import Modules.hm as hm

class CEGame:
    """A game that's on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 game_name : str,
                 platform : hm.PLATFORM_NAMES,
                 platform_id : str,
                 category : str,
                 objectives : list[CEObjective],
                 last_updated : int,
                 banner : str = ""):
        self._ce_id = ce_id
        self._game_name = game_name
        self._platform = platform
        self._platform_id = platform_id
        self._category = category
        self._objectives = objectives
        self._last_updated = last_updated
        self._banner = banner


    # ----------- getters -------------
    
    def get_total_points(self) -> int :
        """Returns the total number of points this game has.\n
        NOTE: This does not include uncleared points, but includes Primary and Secondary!"""
        total_points = 0
        for objective in self.all_objectives :
            if objective.is_uncleared() : continue
            total_points += objective.point_value
        
        return total_points
    
    def get_po_points(self) -> int :
        "The total number of points in Primary Objectives."
        total_points = 0
        for objective in self.get_primary_objectives() :
            if objective.is_uncleared() : continue
            total_points += objective.point_value
        return total_points

    def get_so_points(self) -> int :
        "The total number of points in Secondary Objectives."
        total_points = 0
        for objective in self.get_secondary_objectives() :
            if objective.is_uncleared() : continue
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
    def platform(self) -> hm.PLATFORM_NAMES :
        """Returns the platform this game is hosted on."""
        return self._platform
    
    @property
    def platform_id(self) -> str :
        """Returns the ID value of this game on its platform."""
        return self._platform_id
    
    @property
    def category(self) -> hm.CATEGORIES :
        """Returns the category of this game (e.g. Action, Arcade, Strategy)."""
        return self._category
    
    @property
    def all_objectives(self) -> list[CEObjective] :
        """Returns the array of all `CEObjectives` in this game."""
        return self._objectives
    
    def get_primary_objectives(self) -> list[CEObjective] : 
        """Returns the array of CEObjectives that are Primary.\n
        NOTE: This does not return uncleared objectives!"""
        p = []
        for objective in self.all_objectives :
            if objective.type == "Primary" and not objective.is_uncleared() :
                p.append(objective)
        return p
    
    def get_community_objectives(self) -> list[CEObjective] :
        """Returns the array of CEObjectives that are Community."""
        p = []
        for objective in self.all_objectives :
            if objective.type == "Community" :
                p.append(objective)
        return p
    
    def get_uncleared_objectives(self) -> list[CEObjective] :
        "Returns an array of all uncleared objectives."
        o = []
        for objective in self.all_objectives :
            if objective.is_uncleared() : 
                o.append(objective)
        return o
    
    def get_badge_objectives(self) -> list[CEObjective] :
        "Returns an array of all badge objectives."
        o = []
        for objective in self.all_objectives :
            if objective.type == "Badge" :
                o.append(objective)
        return o
    
    def get_secondary_objectives(self) -> list[CEObjective] :
        "Returns an array of all secondary objectives."
        o = []
        for objective in self.all_objectives :
            if objective.type == "Secondary" :
                o.append(objective)
        return o
    
    def get_objective(self, ce_id : str) -> CEObjective | None:
        """Returns the :class:`CEObjective` object associated
        with `ce_id`, or `None` if none exist."""
        for objective in self.all_objectives :
            if objective.ce_id == ce_id : return objective
        return None
    
    @property
    def last_updated(self) -> int :
        """Returns the unix timestamp of the last time this game was updated."""
        return self._last_updated
    
    async def get_raw_ce_data(self) -> dict :
        "Returns the raw CE data."
        async with aiohttp.ClientSession(headers={'User-Agent':"andy's-super-duper-bot/0.1"}) as session :
            async with session.get(f'https://cedb.me/api/game/{self.ce_id}') as response :
                return await response.json()
    
    async def get_ce_api_game(self) -> 'CEAPIGame' :
        "Returns the CEAPIGame."
        return CEAPIGame(
            ce_id=self.ce_id,
            game_name=self.game_name,
            platform=self.platform,
            platform_id=self.platform_id,
            category=self.category,
            objectives=self.all_objectives,
            last_updated=self.last_updated,
            full_data=await self.get_raw_ce_data()
        )
    
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

    def is_role_t4(self) -> bool :
        "Returns true if this game is a Role T4 (has a discord role associated with it)"
        return self.get_tier_num() == 4 and self.get_total_points() >= 150
    
    def get_tier(self) -> str :
        """Returns the tier (e.g. `"Tier 1"`) of this game."""
        total_points = self.get_total_points()
        if total_points >= 800 : return "Tier 7"
        if total_points >= 400 : return "Tier 6"
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

    # def get_price(self) -> float :
    #     """Returns the current price (in USD) on the platform of choice."""
    #     print("⚠️ The 'CEGame.get_price()' method is deprecated. Use 'CEGame.get_price_async' instead.")
    #     return None 
    
    #     if self.platform == "steam" :
    #         api_response = requests.get("https://store.steampowered.com/api/appdetails?",
    #                                     params = {'appids' : self.platform_id, 'cc' : 'US'})
    #         json_response = json.loads(api_response.text)

    #         steam_id = str(self.platform_id)

    #         if json_response[steam_id]['data']['is_free'] : 
    #             return 0
    #         elif 'price_overview' in json_response[steam_id]['data'] :
    #             return float(json_response[steam_id]['data']['price_overview']['final_formatted'][1::])
    #         else :
    #             return None
    #     return None
    
    async def get_price_async(self) -> float | None :
        """Returns the current price (in USD) on the platform of this game."""
        if self.platform != "steam" : return None

        async with aiohttp.ClientSession(headers={'User-Agent':"andy's-super-duper-bot/0.1"}) as session :
            async with session.get('https://store.steampowered.com/api/appdetails?',
                                   params={'appids': self.platform_id, 'cc' : 'US'}) as response :
                json_response = await response.json()

                steam_id = str(self.platform_id)
                
                if json_response[steam_id]['data']['is_free'] : return 0
                elif 'price_overview' in json_response[steam_id]['data'] :
                    return float(json_response[steam_id]['data']['price_overview']['final_formatted'][1::])
                else :
                    return None
        return None

            
    # def get_steamhunters_data(self) -> int | None :
    #     """Returns the average completion time on SteamHunters, or `None` if a) not a Steam game or b) no SteamHunters data."""
    #     if self.platform != "steam" : return None
    #     api_response = requests.get(f"https://steamhunters.com/api/apps/{self.platform_id}")
    #     if api_response.text == "null" or api_response.text == None :
    #         return None
    #     try :
    #         json_response = json.loads(api_response.text)
    #     except :
    #         print(f"SteamHunters response failed for {self.name_with_link()}")
    #         return 999999

    #     if 'medianCompletionTime' in json_response :
    #         return int(int(json_response['medianCompletionTime']) / 60)
    #     else :
    #         return None
        
    async def get_steamhunters_data_async(self) -> int | None :
        if self.platform != "steam" : return None
        async with aiohttp.ClientSession(headers={'User-Agent':"andy's-super-duper-bot/0.1"}) as session :
            async with session.get(f"https://steamhunters.com/api/apps/{self.platform_id}") as response :
                if await response.text() == "null" or await response.text() == None :
                    return None
                try :
                    json_response = await response.json()
                except :
                    print(f"SteamHunters response failed for {self.name_with_link()}")
                    return 999999

                if 'medianCompletionTime' in json_response :
                    return int(int(json_response['medianCompletionTime']) / 60)
                else :
                    return None
        
    # def get_steam_data(self) -> SteamData | None : 
    #     """Returns the steam data for this game."""
    #     if self.platform != 'steam' : return None
    #     try :
    #         payload = {'appids' : self.platform_id, 'cc' : 'US'}
    #         response = requests.get("https://store.steampowered.com/api/appdetails?", 
    #                                 params = payload)
    #         return SteamData(json.loads(response.text))
    #     except Exception as e :
    #         print(e)
    #         return None
        
    async def get_completion_data(self) -> CECompletion :
        """Returns the completion data for this game."""

        async with aiohttp.ClientSession(headers={'User-Agent':"andy's-super-duper-bot/0.1"}) as session :
            async with session.get(f'https://cedb.me/api/game/{self.ce_id}/leaderboard') as response :
                json_response = await response.json()

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
    
    def has_an_uncleared(self) -> bool :
        """Returns true if this game has an uncleared objective."""
        for objective in self.all_objectives :
            if objective.is_uncleared() : return True
        return False
    
    def get_ce_link(self) -> str :
        "Returns the link to the Challenge Enthusiasts page."
        return f"https://cedb.me/game/{self.ce_id}"
    
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
            "<:CE_points:1128420207329816597>")
        #TODO: finish this function

    def name_with_link(self) -> str :
        "Returns the name with a link."
        return f"[{self.game_name}](https://cedb.me/game/{self.ce_id})"
    
    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        objectives = []
        for objective in self.all_objectives :
            objectives.append(objective.to_dict())
        return {
            "name" : self.game_name,
            "ce_id" : self.ce_id,
            "platform" : self.platform,
            "platform_id" : self.platform_id,
            "category" : self.category,
            "objectives" : objectives,
            "last_updated" : self.last_updated,
            "banner" : self._banner
        }
    
    def __str__(self) :
        "Returns the string representation of this object."
        return (
            "-- CEGame --" +
            "\nGame Name: " + self.game_name +
            "\nGame CE ID: " + self.ce_id +
            "\nTotal Points: " + str(self.get_total_points()) +
            "\nPlatform: " + self.platform +
            "\nPlatform ID: " + str(self.platform_id) +
            "\nCategory: " + self.category +
            "\nObjectives: " + str([objective.__str__() for objective in self.all_objectives]) +
            f"\nLast Updated: <t:{self.last_updated}>"
        )
    
class CEAPIGame(CEGame) :
    """A game that's been pulled from the CE API."""
    def __init__(
            self,
            ce_id : str,
            game_name : str,
            platform : hm.PLATFORM_NAMES,
            platform_id : str,
            category : hm.CATEGORIES,
            objectives : list[CEObjective],
            last_updated : int,
            full_data,
            banner = ""
        ) :
        super().__init__(ce_id, game_name, platform, platform_id, category, objectives, last_updated, banner)
        self.__full_data = full_data

    @property
    def full_data(self) :
        "Return the full API data."
        return self.__full_data
    
    @property
    def icon(self) -> str :
        "The icon for this game."
        return self.full_data['icon']
    
    @property
    def is_finished(self) -> bool :
        "The game is not `unfinished`."
        return self.full_data['isFinished']
    
    @property
    def information(self) -> str :
        "The information for this game."
        return self.full_data['information']
    
    @property
    def header(self) -> str :
        "The header for this game."
        return self.full_data['header']