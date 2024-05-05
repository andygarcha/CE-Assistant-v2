from CE_Objective import CEObjective
import hm

class CEUserObjective:
    """A class for an objective held by a user. Extends the :class:`CEObjective` class."""
    def __init__(self,
                 ce_id : str,
                 game_ce_id : str,
                 type : hm.objective_types,
                 user_points : int,
                 name : str = ""):
        self._type = type
        self._ce_id = ce_id
        self._game_ce_id = game_ce_id
        self._user_points = user_points
        self._name = name
    
    # -------- getters ----------

    def get_user_points(self) -> int :
        """Returns the number of points this user has for this objective."""
        return self._user_points
    
    def get_ce_id(self) -> str :
        """Returns the Challenge Enthusiast ID related to this objective."""
        return self._ce_id
    
    def get_type(self) -> hm.objective_types :
        """Returns the type of this Objective (e.g. Community, Primary)."""
        return self._type
    
    def get_game_ce_id(self) -> str :
        """Returns the Challenge Enthusiast ID related to the game this objective belongs to."""
        return self._game_ce_id
    
    def get_name(self) -> str :
        """Returns the name of this objective."""
        return self._name
    
    # ---------- setters -------------
    
    def set_name(self, name : str) -> None :
        """Sets the name of this objective to `name`."""
        self._name = name
    
    # --------- other methods ---------
    def to_dict(self) -> dict :
        """Turns this objective into a dictionary for MongoDB purposes.
        Example: 
        ```
        {
            "Name" : "I just keep getting better and better.",
            "CE ID" : "a351dce1-ee51-4b55-a05b-38a74854a8be",
            "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
            "Type" : "Badge",
            "User Points" : 20
        }"""
        d = {
            'Name' : self.get_name(),
            'CE ID' : self.get_ce_id(),
            'Game CE ID' : self.get_game_ce_id(),
            'Type' : self.get_type(),
            'User Points' : self.get_user_points()
        }
        return d