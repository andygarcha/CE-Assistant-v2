from typing import Literal

from Exceptions.ItemNotFoundException import ItemNotFoundException


class GameData() :
    """This is a superclass for SteamData, RAData, and any other game types that may be added later."""
    #TODO: make this actually work as a superclass
    @property
    def raw_data(self) -> dict :
        "Returns the raw dict data."

    @property
    def name(self) -> str :
        "Returns the name of this game."
    
    @property
    def app_id(self) -> str :
        "Returns the App ID for this game."


class SteamData() :
    """This class houses the data pulled from a Steam App ID page, so we don't have to work with the raw .json data again."""
    def __init__(self, data : dict) :
        self.__data = data

    @property
    def raw_data(self) -> dict :
        "Returns the raw .json data."
        key = list(self.__data.keys())[0]
        return self.__data[key]['data']
    
    @property
    def name(self) -> str :
        "Returns the name of this game."
        return self.raw_data['name']
    
    @property
    def app_id(self) -> int :
        "Returns the Steam App ID of this game."
        return self.raw_data['steam_appid']
    
    @property
    def is_free(self) -> bool :
        "Returns true if this game is free."
        return self.raw_data['is_free']
    
    @property
    def base_price(self) -> float :
        "Returns this game's base price."
        if self.is_free : return 0
        return self.raw_data['price_overview']['initial'] / 100

    @property
    def current_price(self) -> float :
        "Returns this game's current price."
        if self.is_free : return 0
        return self.raw_data['price_overview']['final'] / 100
    
    @property
    def base_price_formatted(self) -> str :
        "Returns this game's base price as a string - e.g. $19.99."
        if self.is_free : return "$0.00"
        return self.raw_data['price_overview']['initial_formatted']
    
    @property
    def current_price_formatted(self) -> str :
        "Returns this game's base price as a string - e.g. $19.99."
        if self.is_free : return "$0.00"
        return self.raw_data['price_overview']['final_formatted']
    
    @property
    def release_date(self) -> str :
        "Returns this game's release date."
        return self.raw_data['release_date']['date']
    
    @property
    def unreleased(self) -> bool :
        "Returns true if this game has not been released yet."
        return self.raw_data['release_date']['coming_soon']
    
    @property
    def header_image(self) -> str :
        "The link to the header image for this game."
        return self.raw_data['header_image']
    
    @property
    def capsule_image(self) -> str :
        "The link to the capsule image for this game."
        return self.raw_data['capsule_image']
    
    @property
    def capsule_imagev5(self) -> str :
        "I'm gonna be honest, I have no idea what this is."
        return self.raw_data['capsule_imagev5']
    
class CECompletion() :
    "An object to hold the CE Completion data."
    def __init__(self, data : dict) :
        self.__data = data

    @property
    def raw_data(self) -> dict :
        "Returns this object as a dict."
        return self.__data
    
    @property
    def completions(self) -> int :
        "Returns the number of people who have completed this game."
        return self.raw_data['completed']
    
    @property
    def started(self) -> int :
        "Returns the number of people who have progress in this game."
        return self.raw_data['started']
    
    @property
    def total(self) -> int :
        "The total number of owners for this game."
        return self.raw_data['total']
    
    @property
    def no_progress(self) -> int :
        "The number of people who have no progress in this game."
        return self.total - self.started - self.completions
    
    def completion_percentage(self) -> str :
        "The percentage of people who have completed this game - e.g. 4.19%."
        if self.total == 0 : return None
        percentage = (self.completions / self.total) * 100
        percentage = round(percentage, 2)
        return f"{percentage}%"
    
    def description(self) -> str :
        """Returns the completion description. \n
        Example 1:
        Full CE Completions: 19 (8.67% of 219 owners)

        Example 2:
        Full CE Completions: 0 (Percentage N/A)
        """
        percentage = self.completion_percentage()
        if percentage == None :
            return f"Full CE Completions: {self.completions} (Percentage N/A)"
        return f"Full CE Completions: {self.completions} ({percentage} of {self.total} owners)"
    

# just makes shit easier
__ra_prefix : str = "https://media.retroachievements.org"

class RAData() :
    "Container object for RetroAchievements API data."

    def __init__(self, data : dict) :
        self.__data = data
    
    @property
    def raw_data(self) -> dict :
        "The raw data of the object."
        return self.__data
    
    @property
    def id(self) -> int :
        "The RetroAchievements ID for this game."
        return self.raw_data['ID']
    
    @property
    def name(self) -> str :
        "The name of this game."
        return self.raw_data['Title']
    
    @property
    def image_icon(self) -> str :
        "The link to the icon."
        return __ra_prefix + self.raw_data['ImageIcon']
    
    @property
    def image_title(self) -> str :
        "The link to the title image."
        return __ra_prefix + self.raw_data['ImageTitle']
    
    @property
    def image_ingame(self) -> str :
        "The link to the in-game screenshot."
        return __ra_prefix + self.raw_data['ImageIngame']
    
    @property
    def image_boxart(self) -> str :
        "The link to the box art image."
        return __ra_prefix + self.raw_data['ImageBoxArt']
    
    @property
    def release_date(self) -> str :
        "The release date."
        return self.raw_data['Released']
    
    @property
    def console_name(self) -> str :
        "The name of the console this game is on."
        return self.raw_data['ConsoleName']
    
    @property
    def console_id(self) -> int :
        "The RetroAchievements ID for the console this game is on."
        return self.raw_data['ConsoleID']
    
    @property
    def parent_game_id(self) -> int | None :
        "The ID of the parent game, if one exists."
        return self.raw_data['ParentGameID']
    
    @property
    def num_players(self) -> int :
        "The number of distinct players of this game."
        return self.raw_data['NumDistinctPlayers']
    

UPDATEMESSAGE_LOCATIONS = Literal["casino", "log", "privatelog", "gameadditions"]

class UpdateMessage() :
    """A class to hold messages that need to be sent after updating users."""

    def __init__(self,
                 location : UPDATEMESSAGE_LOCATIONS,
                 message : str
                 ) :
        self.__location = location
        self.__message = message

    @property
    def location(self) -> UPDATEMESSAGE_LOCATIONS :
        "The location to send this message."
        return self.__location
    
    @property
    def message(self) -> str :
        "The message to be sent."
        return self.__message
    

"""
class CEList() :
    
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser
    from Exceptions.ItemNotFoundException import ItemNotFoundException
    def __init__(self, items : list[CEGame] | list[CEUser]) :
        self.__items = items

    @property
    def name(self) -> Literal["database_name", "database_user"] :
        "Returns the type of database this CEList is."

    @property
    def items(self)  :
        return self.__items

    def get_item(self, ce_id) :
        for item in self.items :
            if ce_id == item.ce_id : return item
        raise ItemNotFoundException(f"Could not find item {ce_id} in {self.name}.")
    
class DatabaseName(CEList) :
    from Classes.CE_Game import CEGame

    def __init__(self, items : list[CEGame]) :
        super.__init__(self, items)
    

"""