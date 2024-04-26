class CE_Objective:
    """An objective tied to any game on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 is_community : bool,
                 description : str,
                 point_value : int,
                 name : str,
                 requirements : str = None,
                 achievement_ce_ids : list[str] = None,
                 point_value_partial : int = 0):
        self._ce_id = ce_id
        self._is_community = is_community
        self._description = description
        self._point_value = point_value
        self._point_value_partial = point_value_partial
        self._name = name
        self._requirements = requirements
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
    
    def is_community(self) -> bool :
        """Returns true if this is a Community Objective, false if not."""
        return self._is_community
    
    def get_description(self) -> str:
        """Returns the description associated with this objective."""
        return self._description
    
    def get_name(self) -> str:
        """Returns the name of this objective."""
        return self._name
    
    def get_requirements(self) -> str | None:
        """Returns the requirements associated with this objective (or `None` if none exists)."""
        return self._requirements
    
    def get_achievement_ce_ids(self) -> list[str] | None:
        """Returns a list of Challenge Enthusiast IDs associated with the achievements (or `None` if no achievements exist)."""
        return self._achievement_ce_ids
    
    # -------------- helper methods -------------
    
    def has_partial(self) -> bool :
        """Returns true if this game has partial points, false if not."""
        return self._point_value_partial != None and self._point_value_partial != 0
