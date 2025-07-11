
# -- local --
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEGame


class CEUserGame():
    """A game that a user owns. This class extends the :class:`CEGame` class."""
    def __init__(self,
                 ce_id : str,
                 user_objectives : list[CEUserObjective],
                 name : str
                ):
        self._ce_id = ce_id
        self._user_objectives = user_objectives
        self._name = name

    # ----------- getters -----------
    
    def get_user_points(self) :
        """Returns the total number of points this user has in this game."""
        total_points = 0
        for objective in self.get_user_primary_objectives() :
            total_points += objective.user_points
        return total_points
    
    @property
    def ce_id(self) :
        """Returns the Challenge Enthusiast ID associated with this game."""
        return self._ce_id
    
    @property
    def user_objectives(self) :
        """Returns all user Objectives in this game."""
        return self._user_objectives
    
    def get_user_primary_objectives(self) -> list[CEUserObjective] :
        """Returns the array of Primary :class:`CEUserObjective`'s 
        associated with this game."""
        p = []
        for obj in self.user_objectives :
            if obj.type == "Primary" :
                p.append(obj)
        return p
    
    def get_user_community_objectives(self) -> list[CEUserObjective]:
        """Returns the array of Community :class:`CEUserObjective`'s 
        associated with this game."""
        p = []
        for obj in self.user_objectives :
            if obj.type == "Community" :
                p.append(obj)
        return p
    
    def has_completed_objective(self, objective_id : str, points : int) -> CEUserObjective :
        "Returns true if this user has completed the specified objective."
        for obj in self.user_objectives :
            if obj.ce_id == objective_id and obj.user_points == points : return True
        return False
    
    @property
    def name(self) :
        """Returns the name of this game."""
        return self._name
    
    # --------- setters -----------

    def add_user_objective(self, objective : CEUserObjective) :
        """Adds a user objective to the object's user_objective's array."""
        self._user_objectives.append(objective)
        
    # ----------- other methods ------------

    async def get_regular_game(self) -> CEGame :
        """Returns the regular :class:`CEGame` object associated with this game.
        \n**NOTE**: uses bad method"""
        import Modules.CEAPIReader as CEAPIReader
        return await CEAPIReader.get_api_page_data("game", self.ce_id)
    
    def is_completed(self, database_name : list[CEGame]) -> bool :
        """Returns true if this game has been completed, false if not."""
        for game in database_name :
            if game.ce_id == self.ce_id :
                return game.get_total_points() == self.get_user_points()# and not game.is_t0()
        return False
    
    def get_category_v2(self, database_name : list[CEGame]) :
        """Returns the category of this game."""
        for game in database_name :
            if game.ce_id == self.ce_id :
                return game.category
        return None
    
    def to_dict(self) :
        """Returns this game as a dictionary as used in the MongoDB database.
        Example:
        ```
        {
            "Name" : "Neon White",
            "CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
            "Objectives" : [
                {
                    "Name" : "I just keep getting better and better.",
                    "CE ID" : "a351dce1-ee51-4b55-a05b-38a74854a8be",
                    "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                    "Type" : 'Primary',
                    "User Points" : 20
                },
                {
                    "Name" : "Demon Exterminator",
                    "CE ID" : "2a7ad593-4afd-4470-b709-f5ac6b4487e5",
                    "Game CE ID" : "23dfa792-591a-4f55-99ae-1c34180b22c8",
                    "Type" : "Badge",
                    "User Points" : 35
                }
            ]
        }
        ```
        """
        objectives : list[dict] = []
        for objective in self.user_objectives :
            objectives.append(objective.to_dict())
        return {
            'name' : self.name,
            'ce_id' : self.ce_id,
            'objectives' : objectives
        }
    
    def __str__(self) :
        "Returns a string version of this CEUserGame."
        return (
            "-- CEUserGame --" +
            "\nName: " + self.name +
            "\nGame CE ID: " + self.ce_id +
            "\nObjectives: " + str(self.user_objectives)
        )