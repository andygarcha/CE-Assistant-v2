from typing import Literal
from CE_Objective import CE_Objective
from CE_Objective_User import CE_Objective_User
from CE_Game import CE_Game
from CE_API_Reader import CE_API_Reader

class CE_Game_User(CE_Game):
    """A game that a user owns. This class extends the :class:`CE_Game` class."""
    def __init__(self,
                 ce_id : str,
                 game_name : str,
                 platform : str,
                 platform_id : str,
                 is_special : bool,
                 primary_objectives : list[CE_Objective],
                 community_objectives : list[CE_Objective],
                 last_updated : int,
                 user_primary_objectives : list[CE_Objective_User]):
        super().__init__(ce_id,
                 game_name,
                 platform,
                 platform_id,
                 is_special,
                 primary_objectives,
                 community_objectives,
                 last_updated)
        self._user_primary_objectives = user_primary_objectives

    # ----------- getters -----------
    
    def get_user_points(self) :
        """Returns the total number of points this user has in this game."""
        total_points = 0
        for objective in self._user_primary_objectives :
            total_points += objective.get_user_points()
        return total_points
    
    def get_user_primary_objectives(self) :
        """Returns the array of :class:`CE_Objective_User`'s associated with this game."""
        return self._user_primary_objectives
    
    # --------- setters -----------
    def add_user_objective(self, type : Literal["Primary"], objective : CE_Objective_User) :
        """Adds a user objective to the object's user_objective's array."""
        self._user_primary_objectives.append(objective)
    
    # ----------- other methods ------------
    def to_dict(self) :
        """Returns this game as a dictionary as used in the MongoDB database."""
        objective_dict : list[dict] = []
        for objective in self.get_user_primary_objectives() :
            objective_dict.append(objective.to_dict())

        game_dict = {}

        if len(objective_dict) != 0 :
            game_dict['Primary Objectives'] = objective_dict

        return {self.get_ce_id() : game_dict}