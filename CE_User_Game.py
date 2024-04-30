from typing import Literal
from CE_Objective import CEObjective
from CE_User_Objective import CEUserObjective
from CE_Game import CEGame


class CEUserGame():
    """A game that a user owns. This class extends the :class:`CEGame` class."""
    def __init__(self,
                 ce_id : str,
                 user_primary_objectives : list[CEUserObjective],
                 user_community_objectives : list[CEUserObjective],
                 name : str
                ):
        self._ce_id = ce_id
        self._user_primary_objectives = user_primary_objectives
        self._user_community_objectives = user_community_objectives
        self._name = name

    # ----------- getters -----------
    
    def get_user_points(self) :
        """Returns the total number of points this user has in this game."""
        total_points = 0
        for objective in self._user_primary_objectives :
            total_points += objective.get_user_points()
        return total_points
    
    def get_ce_id(self) :
        """Returns the Challenge Enthusiast ID associated with this game."""
        return self._ce_id
    
    def get_user_primary_objectives(self) :
        """Returns the array of Primary :class:`CEUserObjective`'s 
        associated with this game."""
        return self._user_primary_objectives
    
    def get_user_community_objectives(self) :
        """Returns the array of Community :class:`CEUserObjective`'s 
        associated with this game."""
        return self._user_community_objectives
    
    def get_name(self) :
        """Returns the name of this game."""
        return self._name
    
    # --------- setters -----------

    def add_user_objective(self, objective : CEUserObjective) :
        """Adds a user objective to the object's user_objective's array."""
        if not objective.is_community() : 
            self._user_primary_objectives.append(objective)
        elif objective.is_community() : 
            self._user_community_objectives.append(objective)
        
    # ----------- other methods ------------

    def get_regular_game(self) -> CEGame :
        """Returns the regular :class:`CEGame` object associated with this game."""
        import CEAPIReader
        return CEAPIReader.get_api_page_data("game", self.get_ce_id())
    
    def is_completed(self) -> bool :
        """Returns true if this game has been completed, false if not."""
        #TODO: finish this function!

    def get_category(self) -> str :
        """Returns the category of this game."""
        return self.get_regular_game().get_category()
    
    def to_dict(self) :
        """Returns this game as a dictionary as used in the MongoDB database.
        Example:
        ```
        {
            "Name" : "Neon White",
            "CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
            "Primary Objectives" : [
                {
                    "Name" : "I just keep getting better and better.",
                    "CE ID" : "a351dce1-ee51-4b55-a05b-38a74854a8be",
                    "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                    "Community" : False,
                    "User Points" : 20
                },
                {
                    "Name" : "Demon Exterminator",
                    "CE ID" : "2a7ad593-4afd-4470-b709-f5ac6b4487e5",
                    "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                    "Community" : False,
                    "User Points" : 35
                }
            ],
            "Community Objectives" : []
        }
        ```
        """
        primary_objective_array : list[dict] = []
        for objective in self.get_user_primary_objectives() :
            primary_objective_array.append(objective.to_dict())
        community_objective_array : list[dict] = []
        for objective in self.get_user_community_objectives() :
            community_objective_array.append(objective.to_dict())
        return {
            'Name' : self.get_name(),
            'CE ID' : self.get_ce_id(),
            'Primary Objectives' : primary_objective_array,
            'Community Objectives' : community_objective_array,
        }