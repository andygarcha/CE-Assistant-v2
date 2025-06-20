import Modules.hm as hm

class CEObjective:
    """An objective tied to any game on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 objective_type : hm.OBJECTIVE_TYPES,
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

    @property
    def point_value(self) -> int :
        """Returns the total point value of this objective."""
        return self._point_value
        
    @property
    def partial_points(self) -> int :
        """Returns the number of partial points this game has (`0` or `None` if there are none)."""
        return self._point_value_partial
    
    @property
    def ce_id(self) -> str :
        """Returns the Challenge Enthusiast ID related to this objective."""
        return self._ce_id
    
    @property
    def type(self) -> hm.OBJECTIVE_TYPES:
        """Returns the type of objective."""
        return self._objective_type
    
    def get_type_short(self) -> str :
        "Returns this game's type as a short (PO, CO, SO)"
        match(self.type) :
            case "Primary" : return "PO"
            case "Secondary" : return "SO"
            case "Badge" : return "BO"
            case "Community" : return "CO"
    
    @property
    def description(self) -> str:
        """Returns the description associated with this objective."""
        return self._description
    
    @property
    def name(self) -> str:
        """Returns the name of this objective."""
        return self._name
    
    def uncleared_name(self) -> str :
        "Returns the name of this objective without the 'UNCLEARED' nonsense."
        if not self.is_uncleared() : return self.name
        if self.name[-11:len(self.name)] == "(UNCLEARED)" : return self.name[0:-12]
        if self.name[-10:len(self.name)] == "(UNVALUED)" : return self.name[0:-11]
    
    @property
    def requirements(self) -> str | None:
        """Returns the requirements associated with this objective 
        (or `None` if none exists)."""
        return self._requirements
    
    @property
    def achievement_ce_ids(self) -> list[str] | None:
        """Returns a list of Challenge Enthusiast IDs associated 
        with the achievements (or `None` if no achievements exist)."""
        return self._achievement_ce_ids
    
    @property
    def game_ce_id(self) -> str :
        """The Challenge Enthusiast ID associated with this objective's game."""
        return self._game_ce_id
    
    # -------------- setters ----------------

    @type.setter
    def type(self, type : hm.OBJECTIVE_TYPES) :
        """Takes in the type and sets the objective's type to it."""
        self._objective_type = type

    @game_ce_id.setter
    def game_ce_id(self, game_id : str) :
        """Takes in a string `game_id` and sets the local value to such."""
        self._game_ce_id = game_id
    
    # -------------- helper methods -------------
    
    def has_partial(self) -> bool :
        """Returns true if this game has partial points, false if not."""
        return self._point_value_partial != None and self._point_value_partial != 0
    
    def is_uncleared(self) -> bool :
        """Returns true if this game is UNCLEARED."""
        return self._point_value == 1
    
    def equals(self, new_objective : 'CEObjective') -> bool :
        "Returns true if the two objectives have the same values."
        if type(new_objective) != CEObjective : return False
        if self.achievement_ce_ids is None and new_objective.achievement_ce_ids is not None : return False
        if self.achievement_ce_ids is not None and new_objective.achievement_ce_ids is None : return False
        return (
            self.point_value == new_objective.point_value and
            self.type == new_objective.type and
            self.description == new_objective.description and
            self.requirements == new_objective.requirements and
            self.ce_id == new_objective.ce_id and
            self.partial_points == new_objective.partial_points and
            self.name == new_objective.name and 
            hm.achievements_are_equal(self.achievement_ce_ids, new_objective.achievement_ce_ids)
        )

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
            "Requirements" : "Send proof to #proof-submission.",
            "Partial Points" : 10
        }"""
        objective_dict = {
            "name" : self.name,
            "ce_id" : self.ce_id,
            "value" : self.point_value,
            "description" : self.description,
            "game_ce_id" : self.game_ce_id,
            'type' : self.type,
            "achievements" : self.achievement_ce_ids,
            "requirements" : self.requirements,
            "partial_value" : self.partial_points
        }
        return objective_dict
    
    def __str__(self) :
        """String representation of this objective."""
        return (
            "--- CEObjective ---" +
            f"\nObjective Name: {self.name}" +
            f"\nPoint Value: {self.point_value}" +
            f"\nPartial Point Value: {self.partial_points}" +
            f"\nObjective CE ID: {self.ce_id}" +
            f"\nGame's CE ID: {self.game_ce_id}" +
            f"\nObjective Type: {self.type}" +
            f"\nAchievements: {self.achievement_ce_ids}" +
            f"\nRequirements: {self.requirements}"
        )