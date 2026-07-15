import Modules.hm as hm


class CEUserObjective:
    """A class for an objective held by a user. Extends the :class:`CEObjective` class."""

    def __init__(
        self,
        ce_id: str,
        game_ce_id: str,
        type: hm.OBJECTIVE_TYPES,
        partial: bool,
        point_value: int,
        point_value_partial: int,
        name: str = "",
    ):
        self._type: hm.OBJECTIVE_TYPES = type
        self._ce_id = ce_id
        self._game_ce_id = game_ce_id
        self._partial = partial
        self._point_value = point_value
        self._point_value_partial = point_value_partial
        self._name = name

    def __str__(self) -> str:
        return (
            "-- CEUserObjective --"
            f"\nObjective Name: {self.name}"
            f"\nObjective CE ID: {self.ce_id}"
            f"\nGame CE ID: {self.game_ce_id}"
            f"\nObjective Type: {self.type}"
            f"\nUser Points: {self.user_points}"
        )

    # ==== core properties ====

    @property
    def user_points(self) -> int:
        """Returns the number of points this user has for this objective,
        derived live from the objective's current point value."""
        return self._point_value_partial if self._partial else self._point_value

    @property
    def partial(self) -> bool:
        """Returns whether this user's completion of this objective is partial."""
        return self._partial

    @property
    def ce_id(self) -> str:
        """Returns the Challenge Enthusiast ID related to this objective."""
        return self._ce_id

    @property
    def type(self) -> hm.OBJECTIVE_TYPES:
        """Returns the type of this Objective (e.g. Community, Primary)."""
        return self._type

    @property
    def type_short(self) -> str:
        """Returns this as a short type (e.g. PO, SO)"""
        return f"{self._type[0]}O"

    @property
    def game_ce_id(self) -> str:
        """Returns the Challenge Enthusiast ID related to the game this objective belongs to."""
        return self._game_ce_id

    @property
    def name(self) -> str:
        """Returns the name of this objective."""
        return self._name

    # ==== idk where this goes ====
    def to_dict_supabase(self, user_ce_id: str) -> dict:
        return {
            "user_ce_id": user_ce_id,
            "objective_ce_id": self.ce_id,
            "partial": self.partial,
            "updated_at_CE": None,
        }

    def to_dict(self) -> dict:
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
        return {
            "name": self.name,
            "ce_id": self.ce_id,
            "game_ce_id": self.game_ce_id,
            "type": self.type,
            "user_points": self.user_points,
        }
