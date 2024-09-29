from enum import Enum
from typing import Literal, get_args

import discord

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
    

UPDATEMESSAGE_LOCATIONS = Literal["casino", "casinolog", "privatelog", "gameadditions", "userlog"]

class UpdateMessage() :
    """A class to hold messages that need to be sent after updating users."""

    """
    class Location(Enum) :
        "An enum of locations for messages to be sent."
        CASINO = 0
        PRIVATELOG = 1
        USERLOG = 2
        CASINOLOG = 3
        GAMEADDITIONS = 4
    """

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

class EmbedMessage() :
    """A class to hold embeds and files."""
    def __init__(
            self,
            embed : discord.Embed,
            file : discord.File
            ) :
        self.__embed = embed
        self.__file = file

    @property
    def embed(self) -> discord.Embed :
        "The embed."
        return self.__embed
    
    @property
    def file(self) -> discord.File | None :
        "The file."
        return self.__file

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

class Achievement() :
    "A CE achievement."
    def __init__(
            self,
            ce_id : str,
            name : str
        ) :
        self.__ce_id = ce_id
        self.__name = name

    @property
    def ce_id(self) -> str :
        "The CE ID of this achievement."
        return self.__ce_id
    
    @property
    def name(self) -> str :
        "The name of this achievement."
        return self.__name
    
    def __eq__(self, other) :
        if not isinstance(other, Achievement) : return False
        return self.ce_id == other.ce_id
    
    def __hash__(self) :
        return id(self)
    

class CRData :
    "A wrapper class for a user's CR."

    @staticmethod
    def calculate_cr(games : list) :
        "Helper function that contains the CR equation."

        # set some constants before we begin.
        CR_MULTIPLIER = 0.90        # the multiplier
        CR_GAME_CAP = 1000          # the cap of how much an individual game is allowed to contribute

        # calculate the actual cr
        cr : int = 0
        for i, point_value in enumerate(games) :

            # if the game's value is higher than the cap, set it to the cap
            if point_value > CR_GAME_CAP : point_value = CR_GAME_CAP

            # do the calculation
            cr += (CR_MULTIPLIER**i)*(float(point_value))

        # and now round it to two decimal places
        cr = round(cr, 2)
        
        # and return it.
        return cr


    def __init__(
            self, 
            owned_games : list,
            database_name : list
        ) :

        # imports
        from Modules import hm
        from Classes.CE_Game import CEGame
        from Classes.CE_User_Game import CEUserGame
        owned_games : list[CEUserGame] = owned_games
        database_name : list[CEGame] = database_name

        # iterate through every category and set up an array in the dict
        cr_groups : dict[str, list[int]] = {}
        for category in get_args(hm.CATEGORIES) :
            cr_groups[category] = []

        # now go through all of their games and sort them into their categories
        for i, game in enumerate(owned_games) :
            mongo_game = hm.get_item_from_list(game.ce_id, database_name)
            if mongo_game is None : continue
            cr_groups[mongo_game.category].append(game.get_user_points())

        # now that they've all been sorted, calculate the individual crs, and store THAT dict.
        final_dict = {key : self.calculate_cr(cr_groups[key]) for key in cr_groups}
        self.__final_cr_dict = final_dict

        # finally, get the total CR for this user.
        self.__total_cr = round(sum([final_dict[key] for key in final_dict]), 2)

    
    @property
    def cr_dict(self) -> dict :
        return self.__final_cr_dict
    @property
    def action_cr(self) -> int :
        return self.cr_dict['Action']
    @property 
    def arcade_cr(self) -> int :
        return self.cr_dict['Arcade']
    @property
    def bullethell_cr(self) -> int :
        return self.cr_dict['Bullet Hell']
    @property
    def firstperson_cr(self) -> int :
        return self.cr_dict['First-Person']
    @property
    def platformer_cr(self) -> int :
        return self.cr_dict['Platformer']
    @property
    def strategy_cr(self) -> int :
        return self.cr_dict['Strategy']
    @property
    def total_cr(self) -> int :
        return self.__total_cr

    def cr_string(self) -> str :
        "A string representation meant to send in a profile embed."

        # imports 
        from Modules import hm

        # set up the return string
        return_str : str = ""

        # constant to denote how many CRs should be displayed per line
        LINE_BREAK_LIMIT = 3

        # iterate and add to it as necessary
        for i, category in enumerate(self.cr_dict) :

            # make a line break if necessary
            if i % LINE_BREAK_LIMIT == 0 : return_str += "\n"

            # now add the actual values
            return_str += f"{hm.get_emoji(category)}: {self.cr_dict[category]}  "
        
        # add the total CR
        return_str += f"\nTotal: {self.total_cr}"
        
        # and now return
        return return_str
    




class CEIndividualValueInput :
    def __init__(self, user_ce_id : str, value : int) :
        self.__user_ce_id = user_ce_id
        self.__value = value

    @property
    def user_ce_id(self) :
        "The CE ID of the user who made the input."
        return self.__user_ce_id
    
    @property
    def value(self) :
        "What this user thinks the objective should be valued at."
        return self.__value
    
    def to_dict(self) :
        return {
            "user-ce-id" : self.user_ce_id,
            "recommendation" : self.value
        }
    
class CEValueInput :
    def __init__(self, objective_ce_id : str, individual_value_inputs : list[CEIndividualValueInput]) :
        self.__objective_ce_id = objective_ce_id
        self.__individual_value_inputs = individual_value_inputs

    @property
    def objective_ce_id(self) :
        "The CE ID of the objective the value input is about."
        return self.__objective_ce_id
    
    @property
    def individual_value_inputs(self) :
        "The list of value inputs for this objective."
        return self.__individual_value_inputs
    
    def add_new_individual_input(self, user_id : str, value : int) :
        "Adds a new individual input."
        self.__individual_value_inputs.append(CEIndividualValueInput(
            user_ce_id=user_id,
            value=value
        ))
        return
    
    def to_dict(self) :
        value_array = [value.to_dict() for value in self.individual_value_inputs]
        return {
            "objective-ce-id" : self.objective_ce_id,
            "evaluations" : value_array
        }

class CECurateInput :
    def __init__(self, user_ce_id : str, curate : bool) :
        self.__user_ce_id = user_ce_id
        self.__curate = curate

    @property
    def user_ce_id(self) :
        "The CE ID of the user who made the input."
        return self.__user_ce_id
    
    @property
    def curate(self) :
        "Whether or not this user thinks the game should be curated or not."
        return self.__curate
    
    def to_dict(self) :
        return {
            'user-ce-id' : self.user_ce_id,
            'curate' : self.curate
        }
    
class CETagInput :
    def __init__(self, user_ce_id : str, tags : list[str]) :
        self.__user_ce_id = user_ce_id
        self.__tags = tags
    
    @property
    def user_ce_id(self) :
        "The CE ID of the user who made the input."
        return self.__user_ce_id
    
    @property
    def tags(self) :
        "The list of tags this user selected. Maximum of 5."
        return self.__tags
    
    def to_dict(self) :
        return {
            'user-ce-id' : self.user_ce_id,
            'tags' : self.tags
        }
    
class CEInput :
    def __init__(self, 
                 game_ce_id : str, 
                 value_inputs : list[CEValueInput], 
                 curate_inputs : list[CECurateInput], 
                 tag_inputs : list[CETagInput]) :
        self.__game_ce_id = game_ce_id
        self.__value_inputs = value_inputs
        self.__curate_inputs = curate_inputs
        self.__tag_inputs = tag_inputs

    @property
    def ce_id(self) :
        "The CE ID of the game associated with this input."
        return self.__game_ce_id
    
    @property
    def value_inputs(self) :
        "The list of value inputs for this game."
        return self.__value_inputs
    
    @property
    def curate_inputs(self) : 
        "The list of curate inputs for this game."
        return self.__curate_inputs
    
    @property
    def tag_inputs(self) : 
        "The list of tag inputs for this game."
        return self.__tag_inputs
    
    def has_value_input(self, objective_id : str) -> bool :
        "Returns true if there already is a `CEValueInput` for this objective."
        for value_input in self.value_inputs :
            if value_input.objective_ce_id == objective_id : return True
        return False
    
    def get_value_input(self, objective_id : str) -> CEValueInput | None :
        "Returns the `CEValueInput` associated with objective_id, or `None` if none exists."
        for value_input in self.value_inputs :
            if value_input.objective_ce_id == objective_id : return value_input
        return None
    
    def add_value_input(self, objective_id : str, user_id : str, value : int) :
        "Adds a new value input for this game."
        if self.has_value_input(objective_id) :
            pass
        else :
            new_value_input = CEValueInput(
                objective_ce_id=objective_id,
                individual_value_inputs=[]
            )
            new_value_input.add_new_individual_input(user_id=user_id, value=value)
        self.__value_inputs.append(new_value_input)
        return
    
    def to_dict(self) :
        # value_array = [value.to_dict() for value in self.value_inputs]
        # curate_array = [curate.to_dict() for curate in self.curate_inputs]
        # tag_array = [tag.to_dict() for tag in self.tag_inputs]
        return {
            'ce-id' : self.ce_id,
            'value' : [value.to_dict() for value in self.value_inputs],
            'curate' : [curate.to_dict() for curate in self.curate_inputs],
            'tags' : [tag.to_dict() for tag in self.tag_inputs]
        }
