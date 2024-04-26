from typing import Literal
from CE_Objective import CE_Objective

class CE_Game:
    """A game that's on Challenge Enthusiasts."""
    def __init__(self,
                 ce_id : str,
                 game_name : str,
                 platform : str,
                 platform_id : str,
                 is_special : bool,
                 primary_objectives : list[CE_Objective],
                 community_objectives : list[CE_Objective],
                 last_updated : int):
        self._ce_id = ce_id
        self._game_name = game_name
        self._platform = platform
        self._platform_id = platform_id
        self._is_special = is_special
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
    
    # ----------- setters -----------
    def add_objective(self, type : Literal["Primary", "Community"], objective : CE_Objective) :
        """Adds an objective to the game's objective arrays."""
        if type == "Primary" : self._primary_objectives.append(objective)
        elif type == "Community" : self._community_objectives.append(objective)
    

    # --------- helper functions ------------
    def is_t0(self) -> bool :
        """Returns true if the game is a Tier 0."""
        return self.get_total_points() == 0