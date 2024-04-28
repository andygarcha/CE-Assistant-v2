from CE_Objective import CE_Objective

class CE_User_Objective:
    """A class for an objective held by a user. Extends the :class:`CE_Objective` class."""
    def __init__(self,
                 ce_id : str,
                 game_ce_id : str,
                 is_community : bool,
                 user_points : int,
                 name : str = ""):
        self._is_community = is_community
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
    
    def is_community(self) -> bool :
        """Returns true if this objective is a Community Objective."""
        return self._is_community
    
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
            "d1c48bd5-14cb-444e-9301-09574dfbe86a" : 20
        }"""
        dict = {
            self.get_ce_id() : self.get_user_points()
        }
        return dict