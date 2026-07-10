import Modules.hm as hm


class CEObjective:
    """An objective tied to any game on Challenge Enthusiasts."""

    def __init__(
        self,
        ce_id: str,
        objective_type: hm.OBJECTIVE_TYPES,
        description: str,
        point_value: int,
        name: str,
        game_ce_id: str,
        requirements: str | None = None,
        achievement_ce_ids: list[str] | None = None,
        point_value_partial: int = 0,
    ):
        self._ce_id = ce_id
        self._objective_type: hm.OBJECTIVE_TYPES = objective_type
        self._description = description
        self._game_ce_id = game_ce_id
        self._point_value = point_value
        self._point_value_partial = point_value_partial
        self._name = name

        if requirements == "":
            self._requirements = None
        else:
            self._requirements = requirements

        if achievement_ce_ids == []:
            self._achievement_ce_ids = None
        else:
            self._achievement_ce_ids = achievement_ce_ids

    def __str__(self):
        """String representation of this objective."""
        return (
            "--- CEObjective ---"
            + f"\nObjective Name: {self.name}"
            + f"\nPoint Value: {self.point_value}"
            + f"\nPartial Point Value: {self.partial_points}"
            + f"\nObjective CE ID: {self.ce_id}"
            + f"\nGame's CE ID: {self.game_ce_id}"
            + f"\nObjective Type: {self.type}"
            + f"\nAchievements: {self.achievement_ce_ids}"
            + f"\nRequirements: {self.requirements}"
        )

    # ==== core properties ====

    @property
    def point_value(self) -> int:
        """Returns the total point value of this objective."""
        return self._point_value

    @property
    def partial_points(self) -> int:
        """Returns the number of partial points this game has (`0` or `None` if there are none)."""
        return self._point_value_partial

    @property
    def ce_id(self) -> str:
        """Returns the Challenge Enthusiast ID related to this objective."""
        return self._ce_id

    @property
    def type(self) -> hm.OBJECTIVE_TYPES:
        """Returns the type of objective."""
        return self._objective_type

    @property
    def type_short(self) -> str:
        "Returns this game's type as a short (PO, CO, SO)"
        return self.type[0] + "O"

    @property
    def description(self) -> str:
        """Returns the description associated with this objective."""
        return self._description

    @property
    def name(self) -> str:
        """Returns the name of this objective."""
        return self._name

    @property
    def name_uncleared(self) -> str:
        "Returns the name of this objective without the 'UNCLEARED' nonsense."
        if not self.is_uncleared():
            return self.name
        if self.name[-11 : len(self.name)] == "(UNCLEARED)":
            return self.name[0:-12]
        if self.name[-10 : len(self.name)] == "(UNVALUED)":
            return self.name[0:-11]
        return self.name

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
    def game_ce_id(self) -> str:
        """The Challenge Enthusiast ID associated with this objective's game."""
        return self._game_ce_id

    # ==== boolean properties ====

    def has_partial(self) -> bool:
        """Returns true if this game has partial points, false if not."""
        return self._point_value_partial is not None and self._point_value_partial != 0

    def is_uncleared(self) -> bool:
        """Returns true if this objective is UNCLEARED."""
        return (
            self._point_value == 0
            or "(UNCLEARED)" in self.name
            or "(UNVALUED)" in self.name
        )

    def equals(self, new_objective: "CEObjective") -> bool:
        "Returns true if the two objectives have the same values."
        if not isinstance(new_objective, CEObjective):
            return False
        if (
            self.achievement_ce_ids is None
            and new_objective.achievement_ce_ids is not None
        ):
            return False
        if (
            self.achievement_ce_ids is not None
            and new_objective.achievement_ce_ids is None
        ):
            return False
        return (
            self.point_value == new_objective.point_value
            and self.type == new_objective.type
            and self.description == new_objective.description
            and self.requirements == new_objective.requirements
            and self.ce_id == new_objective.ce_id
            and self.partial_points == new_objective.partial_points
            and self.name == new_objective.name
            and hm.achievements_are_equal(
                self.achievement_ce_ids, new_objective.achievement_ce_ids
            )
        )

    # ==== idk where you belong ====

    def to_dict(self) -> dict:
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
        return {
            "name": self.name,
            "ce_id": self.ce_id,
            "value": self.point_value,
            "description": self.description,
            "game_ce_id": self.game_ce_id,
            "type": self.type,
            "achievements": self.achievement_ce_ids,
            "requirements": self.requirements,
            "partial_value": self.partial_points,
        }
