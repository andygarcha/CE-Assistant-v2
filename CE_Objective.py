from typing import Literal
import hm

class CEObjective:
    """An objective tied to any game on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 objective_type : hm.objective_types,
                 description : str,
                 point_value : int,
                 name : str,
                 game_ce_id : str,
                 requirements : str | None = None,
                 achievement_ce_ids : list[str] | None = None,
                 point_value_partial : int = 0):
        self._ce_id = ce_id
        self._objective_type = objective_type
        self._description = description
        self._game_ce_id = game_ce_id
        self._point_value = point_value
        self._point_value_partial = point_value_partial
        self._name = name

        if requirements == "" : 
            self._requirements = None
        else : 
            self._requirements = requirements

        if achievement_ce_ids == [] :
            self._achievement_ce_ids = None
        else :
            self._achievement_ce_ids = achievement_ce_ids
    
    # -------------- getters -----------------

    def get_point_value(self) -> int :
        """Returns the total point value of this objective."""
        return self._point_value
        
    def get_partial_points(self) -> int :
        """Returns the number of partial points this game has (`0` or `None` if there are none)."""
        return self._point_value_partial
    
    def get_ce_id(self) -> str :
        """Returns the Challenge Enthusiast ID related to this objective."""
        return self._ce_id
    
    def get_type(self) -> hm.objective_types:
        """Returns the type of objective."""
        return self._objective_type
    
    def get_description(self) -> str:
        """Returns the description associated with this objective."""
        return self._description
    
    def get_name(self) -> str:
        """Returns the name of this objective."""
        return self._name
    
    def get_requirements(self) -> str | None:
        """Returns the requirements associated with this objective 
        (or `None` if none exists)."""
        return self._requirements
    
    def get_achievement_ce_ids(self) -> list[str] | None:
        """Returns a list of Challenge Enthusiast IDs associated 
        with the achievements (or `None` if no achievements exist)."""
        return self._achievement_ce_ids
    
    # -------------- setters ----------------

    def set_type(self, type : hm.objective_types) :
        """Takes in the type and sets the objective's type to it."""
        self._objective_type = type

    def set_game_id(self, game_id : str) -> None :
        """Takes in a string `game_id` and sets the local value to such."""
        self._game_ce_id = game_id
    
    # -------------- helper methods -------------
    
    def has_partial(self) -> bool :
        """Returns true if this game has partial points, false if not."""
        return self._point_value_partial != None and self._point_value_partial != 0
    
    def is_uncleared(self) -> bool :
        """Returns true if this game is UNCLEARED."""
        return self._point_value == 1

    def to_dict(self) -> dict :
        """Returns this objective as a :class:`dict` for storage purposes.
        Example: 
        ```
        {
            "Name" : "I just keep getting better and better.",
            "Point Value" : 35,
            "Description" : "Prove yourself.",
            "CE ID" : "a351dce1-ee51-4b55-a05b-38a74854a8be",
            "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
            "Type" : "Badge",
            "Achievements" : ["a351dce1-ee51-4b55-a05b-38a74854a8be"],
            "Requirements" : "Send proof to #proof-submission",
            "Partial Points" : 10
        }"""
        objective_dict = {
            "Name" : self.get_name(),
            "Point Value" : self.get_point_value(),
            "Description" : self.get_description(),
            "CE ID" : self.get_ce_id(),
            'Type' : self.get_type()
        }
        if self.get_achievement_ce_ids() != None : 
            objective_dict['Achievements'] = self.get_achievement_ce_ids()
        if self.get_requirements() != None :
            objective_dict['Requirements'] = self.get_requirements()
        if self.has_partial() :
            objective_dict['Partial Points'] = self.get_partial_points()
        return objective_dict