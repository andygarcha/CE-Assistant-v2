from collections.abc import Mapping

# -- local --
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEGame
from utils.game_utils import CATEGORIES


class CEUserGame:
    """A game that a user owns. This class extends the :class:`CEGame` class."""

    def __init__(self, ce_id: str, user_objectives: list[CEUserObjective], name: str):
        self._ce_id = ce_id
        self._user_objectives = user_objectives
        self._name = name

    # ----------- getters -----------

    def get_user_points(self):
        """Returns the total number of points this user has in this game."""
        total_points = 0
        for objective in self.user_objectives:
            total_points += objective.user_points
        return total_points

    @property
    def ce_id(self):
        """Returns the Challenge Enthusiast ID associated with this game."""
        return self._ce_id

    @property
    def user_objectives(self):
        """Returns all user Objectives in this game."""
        return self._user_objectives

    def get_user_primary_objectives(self) -> list[CEUserObjective]:
        """Returns the array of Primary :class:`CEUserObjective`'s
        associated with this game. NOTE: Though this should never happen,
        this *will* include any 'Uncleared' POs that this user has."""
        p = []
        for obj in self.user_objectives:
            if obj.type == "Primary":
                p.append(obj)
        return p

    def get_user_points_primary(self):
        "Returns the total number of points this user has from POs in this game... INCLUDING uncleared POs."
        total_points = 0
        for objective in self.get_user_primary_objectives():
            total_points += objective.user_points
        return total_points

    def get_user_community_objectives(self) -> list[CEUserObjective]:
        """Returns the array of Community :class:`CEUserObjective`'s
        associated with this game."""
        p = []
        for obj in self.user_objectives:
            if obj.type == "Community":
                p.append(obj)
        return p

    def has_completed_objective(self, objective_id: str, points: int) -> bool:
        "Returns true if this user has completed the specified objective."
        for obj in self.user_objectives:
            if obj.ce_id == objective_id and obj.user_points == points:
                return True
        return False

    @property
    def name(self):
        """Returns the name of this game."""
        return self._name

    # --------- setters -----------

    def add_user_objective(self, objective: CEUserObjective):
        """Adds a user objective to the object's user_objective's array."""
        self._user_objectives.append(objective)

    # ----------- other methods ------------

    async def get_regular_game(self) -> CEGame | None:
        """Returns the regular :class:`CEGame` object associated with this game.
        \n**NOTE**: uses bad method"""
        import Modules.CEAPIReader as CEAPIReader

        return await CEAPIReader.get_game(self.ce_id)

    def is_completed(
        self, database_name: list[CEGame] | Mapping[str, CEGame] | CEGame
    ) -> bool:
        """Returns true if this game has been completed, false if not."""
        if isinstance(database_name, CEGame):
            return self.__is_completed_helper(database_name)
        if isinstance(database_name, Mapping):
            game = database_name.get(self.ce_id)
            if game is None:
                return False
            return self.__is_completed_helper(game)
        if isinstance(database_name, list):
            for game in database_name:
                if game.ce_id == self.ce_id:
                    return self.__is_completed_helper(game)
        return False

    def __is_completed_helper(self, game: CEGame):
        """Only Primary Objectives should count towards completion.
        We cannot simply count the number of POs, as some may be *partial*.
        We also simply cannot check the user points, since this would skip uncleareds.
        """
        user_pos = self.get_user_primary_objectives()
        game_pos = game.get_primary_objectives(include_uncleareds=True)

        user_points = self.get_user_points_primary()
        game_points = game.get_po_points(include_uncleareds=True)

        if len(user_pos) == 0:
            return False
        if len(user_pos) != len(game_pos):
            return False
        if user_points != game_points:
            return False
        return True

        # Completion should be based on each valued Primary objective being fully met.
        required_primary = game.get_primary_objectives(include_uncleareds=False)
        if len(required_primary) == 0:
            return False

        # Deduplicate by objective id in case storage has duplicate rows; keep max points.
        user_primary_points: dict[str, int] = {}
        for objective in self.get_user_primary_objectives():
            prev = user_primary_points.get(objective.ce_id, 0)
            if objective.user_points > prev:
                user_primary_points[objective.ce_id] = objective.user_points

        for objective in required_primary:
            user_points = user_primary_points.get(objective.ce_id)
            if user_points is None:
                return False
            if user_points < objective.point_value:
                return False

    def get_category_v2(self, database_name: list[CEGame]) -> list[CATEGORIES] | None:
        """Returns the category of this game."""
        for _game in database_name:
            if _game.ce_id == self.ce_id:
                return _game.categories
        return None

    def to_dict_supabase(self, user_ce_id: str):
        return {
            "user_ce_id": user_ce_id,
            "game_ce_id": self.ce_id,
            "updated_at_CE": None,
        }

    def to_dict_supabase_objectives(self, user_ce_id: str):
        return [o.to_dict_supabase(user_ce_id) for o in self.user_objectives]

    def to_dict(self):
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
        objectives: list[dict] = []
        for objective in self.user_objectives:
            objectives.append(objective.to_dict())
        return {"name": self.name, "ce_id": self.ce_id, "objectives": objectives}

    def __str__(self):
        "Returns a string version of this CEUserGame."
        return (
            "-- CEUserGame --"
            + "\nName: "
            + self.name
            + "\nGame CE ID: "
            + self.ce_id
            + "\nObjectives: "
            + str(self.user_objectives)
        )
