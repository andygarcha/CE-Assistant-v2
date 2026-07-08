from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, get_args

from Modules import hm

if TYPE_CHECKING:
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser
    from Classes.CE_User_Game import CEUserGame

logger = logging.getLogger(__name__)


class GameData(ABC):
    """This is a superclass for SteamData, RAData, and any other game types that may be added later."""

    # TODO: make this actually work as a superclass
    @property
    @abstractmethod
    def raw_data(self) -> dict:
        "Returns the raw dict data."

    @property
    @abstractmethod
    def name(self) -> str:
        "Returns the name of this game."

    @property
    @abstractmethod
    def app_id(self) -> int:
        "Returns the App ID for this game."


class SteamData(GameData):
    """This class houses the data pulled from a Steam App ID page, so we don't have to work with the raw .json data again."""

    def __init__(self, data: dict):
        self.__data = data

    @property
    def raw_data(self) -> dict:
        "Returns the raw .json data."
        key = next(iter(self.__data.keys()))
        return self.__data[key]["data"]

    @property
    def name(self) -> str:
        "Returns the name of this game."
        return self.raw_data["name"]

    @property
    def app_id(self) -> int:
        "Returns the Steam App ID of this game."
        return self.raw_data["steam_appid"]

    @property
    def is_free(self) -> bool:
        "Returns true if this game is free."
        return self.raw_data["is_free"]

    @property
    def base_price(self) -> float:
        "Returns this game's base price."
        if self.is_free:
            return 0
        return self.raw_data["price_overview"]["initial"] / 100

    @property
    def current_price(self) -> float:
        "Returns this game's current price."
        if self.is_free:
            return 0
        return self.raw_data["price_overview"]["final"] / 100

    @property
    def base_price_formatted(self) -> str:
        "Returns this game's base price as a string - e.g. $19.99."
        if self.is_free:
            return "$0.00"
        return self.raw_data["price_overview"]["initial_formatted"]

    @property
    def current_price_formatted(self) -> str:
        "Returns this game's base price as a string - e.g. $19.99."
        if self.is_free:
            return "$0.00"
        try:
            return self.raw_data["price_overview"]["final_formatted"]
        except Exception as e:
            logger.exception(e)
            return "Price Error."

    @property
    def release_date(self) -> str:
        "Returns this game's release date."
        return self.raw_data["release_date"]["date"]

    @property
    def unreleased(self) -> bool:
        "Returns true if this game has not been released yet."
        return self.raw_data["release_date"]["coming_soon"]

    @property
    def header_image(self) -> str:
        "The link to the header image for this game."
        return self.raw_data["header_image"]

    @property
    def capsule_image(self) -> str:
        "The link to the capsule image for this game."
        return self.raw_data["capsule_image"]

    @property
    def capsule_imagev5(self) -> str:
        "I'm gonna be honest, I have no idea what this is."
        return self.raw_data["capsule_imagev5"]


class CECompletion:
    "An object to hold the CE Completion data."

    def __init__(self, data: dict):
        self.__data = data

    @property
    def raw_data(self) -> dict:
        "Returns this object as a dict."
        return self.__data

    @property
    def completions(self) -> int:
        "Returns the number of people who have completed this game."
        return self.raw_data["completed"]

    @property
    def started(self) -> int:
        "Returns the number of people who have progress in this game."
        return self.raw_data["started"]

    @property
    def total(self) -> int:
        "The total number of owners for this game."
        return self.raw_data["total"]

    @property
    def no_progress(self) -> int:
        "The number of people who have no progress in this game."
        return self.total - self.started - self.completions

    def completion_percentage(self) -> str | None:
        "The percentage of people who have completed this game - e.g. 4.19%."
        if self.total == 0:
            return None
        percentage = (self.completions / self.total) * 100
        percentage = round(percentage, 2)
        return f"{percentage}%"

    def description(self) -> str:
        """Returns the completion description. \n
        Example 1:
        Full CE Completions: 19 (8.67% of 219 owners)

        Example 2:
        Full CE Completions: 0 (Percentage N/A)
        """
        percentage = self.completion_percentage()
        if percentage is None:
            return f"Full CE Completions: {self.completions} (Percentage N/A)"
        return f"Full CE Completions: {self.completions} ({percentage} of {self.total} owners)"


# just makes shit easier
__ra_prefix: str = "https://media.retroachievements.org"


class RAData(GameData):
    "Container object for RetroAchievements API data."

    def __init__(self, data: dict):
        self.__data = data

    @property
    def raw_data(self) -> dict:
        "The raw data of the object."
        return self.__data

    @property
    def app_id(self) -> int:
        "The RetroAchievements ID for this game."
        return self.raw_data["ID"]

    @property
    def name(self) -> str:
        "The name of this game."
        return self.raw_data["Title"]

    @property
    def image_icon(self) -> str:
        "The link to the icon."
        return __ra_prefix + self.raw_data["ImageIcon"]

    @property
    def image_title(self) -> str:
        "The link to the title image."
        return __ra_prefix + self.raw_data["ImageTitle"]

    @property
    def image_ingame(self) -> str:
        "The link to the in-game screenshot."
        return __ra_prefix + self.raw_data["ImageIngame"]

    @property
    def image_boxart(self) -> str:
        "The link to the box art image."
        return __ra_prefix + self.raw_data["ImageBoxArt"]

    @property
    def release_date(self) -> str:
        "The release date."
        return self.raw_data["Released"]

    @property
    def console_name(self) -> str:
        "The name of the console this game is on."
        return self.raw_data["ConsoleName"]

    @property
    def console_id(self) -> int:
        "The RetroAchievements ID for the console this game is on."
        return self.raw_data["ConsoleID"]

    @property
    def parent_game_id(self) -> int | None:
        "The ID of the parent game, if one exists."
        return self.raw_data["ParentGameID"]

    @property
    def num_players(self) -> int:
        "The number of distinct players of this game."
        return self.raw_data["NumDistinctPlayers"]


class CRData:
    """
    A wrapper class for a user's CR. This class calculates per-category CR
    and Total CR.

    Category CR Formula
    ---
    Games in a category are sorted by points descending. Each game contributes:

        cr += min(points, 1000) * 0.90^i

    where i is the game's index in that sorted list (0-based). Multi-category
    games are counted in every category they belong to for this calculation.

    Total CR Formula
    ---
    All games are sorted by points descending. A running power counter is kept
    per category, starting at 0. For each game, the contribution to each of its
    categories is:

        contribution = min(points, 1000) * 0.90^(category_power)

    The category_power for each of the game's categories is then incremented,
    regardless of whether that category ends up being the best one. Only the
    maximum contribution across all of a game's categories is added to the
    total CR:

        total_cr += max(contribution per category)

    This means multi-category games advance the power counter (reducing future
    multipliers) in ALL their categories, but only their single best contribution
    counts toward the total. This matches the CE site's implementation.
    """

    @staticmethod
    def calculate_cr(games: list) -> float:
        "Helper function that contains the CR equation."

        # set some constants before we begin.
        CR_MULTIPLIER = 0.90  # the multiplier
        CR_GAME_CAP = (
            1000  # the cap of how much an individual game is allowed to contribute
        )

        # calculate the actual cr
        cr: float = 0.0
        for i, point_value in enumerate(games):
            # if the game's value is higher than the cap, set it to the cap
            point_value = min(point_value, CR_GAME_CAP)

            # do the calculation
            cr += (CR_MULTIPLIER**i) * (float(point_value))

        # and now round it to two decimal places
        cr = round(cr, 2)

        # and return it.
        return cr

    @staticmethod
    def calculate_total_cr(
        all_games: list[tuple[int, list[hm.CATEGORIES]]],
    ) -> float:
        """
        Calculates Total CR.
        See CRData's docstring for information on how this is calculated.

        Parameters
        ---
        all_games: `list[tuple[int, list[hm.CATEGORIES]]]`
            All games as (points, categories) tuples, sorted by points DESC.
            Multi-cat games advance the power counter for ALL their categories,
            but only their max per-category contribution counts toward total CR.
        """
        powers: dict[str, int] = dict.fromkeys(get_args(hm.CATEGORIES), 0)
        total_cr: float = 0.0

        for points, categories in all_games:
            max_contribution: float = 0.0
            for cat in categories:
                contribution = min(points, 1000) * (0.90 ** powers[cat])
                powers[cat] += 1
                max_contribution = max(max_contribution, contribution)
            total_cr += max_contribution

        return round(total_cr, 2)

    def __init__(self, owned_games: list[CEUserGame], database_name: list[CEGame]):
        cr_groups_multicat: dict[str, list[int]] = {
            cat: [] for cat in get_args(hm.CATEGORIES)
        }
        all_games: list[tuple[int, list[hm.CATEGORIES]]] = []

        for game in owned_games:
            mongo_game = hm.get_item_from_list(game.ce_id, database_name)
            if mongo_game is None:
                continue

            pts = game.get_user_points()
            for _cat in mongo_game.categories:
                cr_groups_multicat[_cat].append(pts)

            all_games.append((pts, mongo_game.categories))

        # per-category CRs use the full multicat list (games counted in all their categories)
        final_dict = {
            key: self.calculate_cr(sorted(cr_groups_multicat[key], reverse=True))
            for key in cr_groups_multicat
        }
        self.__final_cr_dict: dict[str, float] = final_dict

        # total CR: process all games sorted DESC, max per-category contribution per game
        self.__total_cr = self.calculate_total_cr(
            sorted(all_games, key=lambda x: x[0], reverse=True)
        )

    @property
    def cr_dict(self) -> dict[str, float]:
        return self.__final_cr_dict

    @property
    def action_cr(self) -> float:
        return self.cr_dict["Action"]

    @property
    def arcade_cr(self) -> float:
        return self.cr_dict["Arcade"]

    @property
    def bullethell_cr(self) -> float:
        return self.cr_dict["Bullet Hell"]

    @property
    def firstperson_cr(self) -> float:
        return self.cr_dict["First-Person"]

    @property
    def platformer_cr(self) -> float:
        return self.cr_dict["Platformer"]

    @property
    def strategy_cr(self) -> float:
        return self.cr_dict["Strategy"]

    @property
    def total_cr(self) -> float:
        return self.__total_cr

    def cr_string(self) -> str:
        "A string representation meant to send in a profile embed."
        # set up the return string
        return_str: str = ""

        # constant to denote how many CRs should be displayed per line
        LINE_BREAK_LIMIT = 3

        # iterate and add to it as necessary
        for i, category in enumerate(self.cr_dict):
            # make a line break if necessary
            if i % LINE_BREAK_LIMIT == 0:
                return_str += "\n"

            # now add the actual values
            return_str += f"{hm.get_emoji(category)}: {self.cr_dict[category]}  "  # type: ignore

        # add the total CR
        return_str += f"\nTotal: {self.total_cr}"

        # and now return
        return return_str


class CEIndividualValueInput:
    def __init__(self, user_ce_id: str, value: int):
        self.__user_ce_id = user_ce_id
        self.__value = value

    @property
    def user_ce_id(self):
        "The CE ID of the user who made the input."
        return self.__user_ce_id

    @property
    def value(self):
        "What this user thinks the objective should be valued at."
        return self.__value

    def set_value(self, value):
        "Sets the input's `value` attribute to argument `value`."
        self.__value = value
        pass

    def to_dict(self):
        return {"user_ce_id": self.user_ce_id, "recommendation": self.value}

    def to_string(self, database_user: list[CEUser]):
        # grab user object
        user = hm.get_item_from_list(self.user_ce_id, database_user)
        if user is None:
            raise Exception(f"Could not find user {self.user_ce_id} in database user.")

        # now return
        return f"  - [{user.display_name}]({user.get_ce_link()}): {self.value}\n"


class CEValueInput:
    def __init__(
        self,
        objective_ce_id: str,
        individual_value_inputs: list[CEIndividualValueInput],
    ):
        self.__objective_ce_id = objective_ce_id
        self.__individual_value_inputs = individual_value_inputs

    @property
    def objective_ce_id(self):
        "The CE ID of the objective the value input is about."
        return self.__objective_ce_id

    @property
    def individual_value_inputs(self):
        "The list of value inputs for this objective."
        return self.__individual_value_inputs

    # == individual eval stuff ==

    def add_individual_input(self, user_id: str, value: int):
        "Adds an individual input. Handles cases where the user has previously made an input for this objective."
        if self.user_has_individual_input(user_id):
            self.replace_individual_input(user_id, value)
        else:
            self.add_new_individual_input(user_id, value)

    def add_new_individual_input(self, user_id: str, value: int):
        """Adds a new individual input.
        Does NOT handle case when the user has previously made an input for this objective."""
        self.__individual_value_inputs.append(
            CEIndividualValueInput(user_ce_id=user_id, value=value)
        )
        return

    def user_has_individual_input(self, user_id: str):
        "Returns true if the user whose ce id is passed as `user_id` has an individual value input for this value."
        return self.index_of_individual_input(user_id) != -1

    def get_individual_input(self, user_id: str):
        "Returns the individual input of a user for this value input."
        return self.__individual_value_inputs[self.index_of_individual_input(user_id)]

    def replace_individual_input(self, user_id: str, value: int):
        "Replaces a user's previous input with a new one."
        self.__individual_value_inputs[
            self.index_of_individual_input(user_id)
        ].set_value(value)

    def index_of_individual_input(self, user_id: str) -> int:
        "Returns the index of the individual input for a user (or -1 if one doesn't exist)."
        for i, individual_value_input in enumerate(self.__individual_value_inputs):
            if individual_value_input.user_ce_id == user_id:
                return i
        return -1

    # == other methods ==

    def average(self) -> float:
        values = [
            individual_value_input.value
            for individual_value_input in self.individual_value_inputs
        ]
        average = float(sum(values)) / float(len(values))
        return round(average, 2)

    def average_is_okay(self, database_name: list[CEGame], game_id: str) -> bool:
        "Will return true if this average is not within a scary enough range for the mods to change."
        # imports
        game_object = hm.get_item_from_list(game_id, database_name)
        if game_object is None:
            raise Exception(
                f"Could not find game {game_id} in database name {len(database_name)=}"
            )
        objective_object = game_object.get_objective(self.objective_ce_id)
        if objective_object is None:
            raise Exception(
                f"Could not find objective {self.objective_ce_id} in game {game_id}."
            )

        "This variable determines what percentage range the average can be within the actual value."
        VALID_RANGE = 50

        return hm.is_within_percentage(
            self.average(), VALID_RANGE, objective_object.point_value
        )

    # == to dict and to string ==

    def to_dict(self):
        value_array = [value.to_dict() for value in self.individual_value_inputs]
        return {"objective_ce_id": self.objective_ce_id, "evaluations": value_array}

    def to_string(
        self, database_name: list[CEGame], database_user: list[CEUser], game_id: str
    ):
        game = hm.get_item_from_list(game_id, database_name)
        if game is None:
            raise Exception(f"Could not find game with ID {game_id} in database name.")

        objective = game.get_objective(self.objective_ce_id)
        if objective is None:
            raise Exception(
                f"Could not find objective with ID {self.objective_ce_id} from game {game_id}."
            )

        returned_string: str = ""

        returned_string += f"- Objective: {objective.name} "
        returned_string += f"({objective.point_value} {hm.get_emoji('Points')})\n"
        for individual_value_input in self.individual_value_inputs:
            returned_string += individual_value_input.to_string(database_user)
        returned_string += f"  - Average: {self.average()}\n"
        return returned_string

    def to_string_simple(self, database_name: list[CEGame], game_id: str) -> str:
        "Returns a much simpler string."

        game = hm.get_item_from_list(game_id, database_name)
        if game is None:
            raise Exception(f"Could not find game with ID {game_id} in database name.")

        objective = game.get_objective(self.objective_ce_id)
        if objective is None:
            raise Exception(
                f"Could not find objective with ID {self.objective_ce_id} from game {game_id}."
            )

        return "- Objective: {} ({} {})\n  - Average: {} ({} valuation(s))\n".format(
            objective.name,
            objective.point_value,
            hm.get_emoji("Points"),
            self.average(),
            len(self.individual_value_inputs),
        )


class CECurateInput:
    def __init__(self, user_ce_id: str, curate: int):
        self.__user_ce_id = user_ce_id
        self.__curate = curate

    @property
    def user_ce_id(self) -> str:
        "The CE ID of the user who made the input."
        return self.__user_ce_id

    @property
    def curate(self) -> int:
        """Whether or not this user thinks the game should be curated or not.
        0: Don't Curate
        1: Curate
        2: Indifferent"""
        return self.__curate

    def curate_meaning(self) -> str:
        match self.curate:
            case 0:
                return "Don't Curate"
            case 1:
                return "Curate"
            case 2:
                return "Indifferent"
            case _:
                return "Failure"

    def set_curate(self, curate: int):
        "Sets this object's curate attribute to `curate` argument."
        self.__curate = curate

    def to_dict(self):
        return {"user_ce_id": self.user_ce_id, "curate": self.curate}

    def to_string(self, database_user: list[CEUser]):
        # grab user object
        user = hm.get_item_from_list(self.user_ce_id, database_user)
        if user is None:
            raise Exception(
                f"Could not find user with ID {self.user_ce_id} in database name."
            )

        return f"- {user.mention()}: {self.curate_meaning()}\n"


class CETagInput:
    def __init__(self, user_ce_id: str, tags: list[str]):
        self.__user_ce_id = user_ce_id
        self.__tags = tags

    @property
    def user_ce_id(self):
        "The CE ID of the user who made the input."
        return self.__user_ce_id

    @property
    def tags(self):
        "The list of tags this user selected. Maximum of 5."
        return self.__tags

    def to_dict(self):
        return {"user_ce_id": self.user_ce_id, "tags": self.tags}


class CEInput:
    def __init__(
        self,
        game_ce_id: str,
        value_inputs: list[CEValueInput],
        curate_inputs: list[CECurateInput],
        tag_inputs: list[CETagInput],
    ):
        self.__game_ce_id = game_ce_id
        self.__value_inputs = value_inputs
        self.__curate_inputs = curate_inputs
        self.__tag_inputs = tag_inputs

    @property
    def ce_id(self):
        "The CE ID of the game associated with this input."
        return self.__game_ce_id

    @property
    def value_inputs(self):
        "The list of value inputs for this game."
        return self.__value_inputs

    @property
    def curate_inputs(self):
        "The list of curate inputs for this game."
        return self.__curate_inputs

    @property
    def tag_inputs(self):
        "The list of tag inputs for this game."
        return self.__tag_inputs

    # === value input stuff ==

    def has_value_input(self, objective_id: str) -> bool:
        "Returns true if there already is a `CEValueInput` for this objective."
        for value_input in self.value_inputs:
            if value_input.objective_ce_id == objective_id:
                return True
        return False

    def get_value_input(self, objective_id: str) -> CEValueInput | None:
        "Returns the `CEValueInput` associated with objective_id, or `None` if none exists."
        for value_input in self.value_inputs:
            if value_input.objective_ce_id == objective_id:
                return value_input
        return None

    def index_of_value_input(self, objective_id: str):
        "Returns the index of the value input with ce-id `objective_id` (or -1 if it doesn't exist)."
        for i, value_input in enumerate(self.__value_inputs):
            if value_input.objective_ce_id == objective_id:
                return i

        return -1

    def replace_value_input(self, objective_id: str, value_input: CEValueInput):
        index = self.index_of_value_input(objective_id)
        self.__value_inputs[index] = value_input
        pass

    def add_value_input(self, objective_id: str, user_id: str, value: int):
        "Adds a new value input for this game."
        # if we already have a *value input* for this objective, just add the
        # individual value input we just made.
        if self.has_value_input(objective_id):
            value_input = self.get_value_input(objective_id)
            if value_input is None:
                raise Exception(
                    f"Could not get value input from game {self.ce_id} objective {objective_id}"
                )
            value_input.add_individual_input(user_id=user_id, value=value)
            self.replace_value_input(objective_id, value_input)

        # if we don't already have a value input for this objective,
        # make a new one and add it to the array.
        else:
            value_input = CEValueInput(
                objective_ce_id=objective_id, individual_value_inputs=[]
            )
            value_input.add_new_individual_input(user_id=user_id, value=value)
            self.__value_inputs.append(value_input)
        pass

    # == curate input stuff ==

    def average_curate(self) -> str:
        "Returns the percentage of people who think this game should be curated. Example: '62.35%'"
        return f"{round(self.average_curate_num(), 2)}%"

    def average_curate_num(self) -> float:
        "Returns the percentage of people who think this game should be curated. Example: '62.35%'"
        if self.curator_count() == 0:
            return 0
        inputs = [curate_input.curate for curate_input in self.curate_inputs]
        average = (
            float(inputs.count(1)) / float(inputs.count(0) + inputs.count(1)) * 100
        )
        return average

    def curator_count(self) -> int:
        "Returns the number of people who have given curator inputs."
        return len(self.curate_inputs)

    def user_has_selected_yes(self, user_id: str) -> bool:
        "Returns true if this user has selected yes in the past."
        for curate_input in self.__curate_inputs:
            if curate_input.user_ce_id == user_id and curate_input.curate == 1:
                return True
        return False

    def user_has_selected_no(self, user_id: str) -> bool:
        "Returns true if this user has selected no in the past."
        for curate_input in self.__curate_inputs:
            if curate_input.user_ce_id == user_id and curate_input.curate == 0:
                return True
        return False

    def user_has_selected_indifferent(self, user_id: str) -> bool:
        "Returns true if this user has selected no in the past."
        for curate_input in self.__curate_inputs:
            if curate_input.user_ce_id == user_id and curate_input.curate == 2:
                return True
        return False

    def add_curate_input(self, user_id: str, curate: int):
        "Adds or overwrites a curate input."
        if self.has_curate_input(user_id):
            self.replace_curate_input(user_id, curate)
        else:
            self.add_new_curate_input(user_id, curate)
        pass

    def add_new_curate_input(self, user_id: str, curate: int):
        "Adds a new curate input."
        self.__curate_inputs.append(CECurateInput(user_ce_id=user_id, curate=curate))
        pass

    def has_curate_input(self, user_id: str):
        "Returns true if this user has already made a curate input."
        return self.index_of_curate_input(user_id) != -1

    def index_of_curate_input(self, user_id: str):
        "Returns the index of the curate input from this user (or -1 if none exists)."
        for i, curate_input in enumerate(self.__curate_inputs):
            if curate_input.user_ce_id == user_id:
                return i
        return -1

    def get_curate_input(self, user_id: str):
        "Returns the curate input given by a the user id."
        return self.__curate_inputs[self.index_of_curate_input(user_id)]

    def replace_curate_input(self, user_id: str, curate: int):
        "Adjusts the curate input accordingly."
        if not self.has_curate_input(user_id):
            raise Exception(
                "Tried replacing a curate input - but the user doesn't have one!"
            )

        self.__curate_inputs[self.index_of_curate_input(user_id)].set_curate(curate)
        pass

    def is_curatable(self):
        "Returns true if this game belongs on the curator."
        MINIMUM_CURATE_VOTES = 10
        MINIMUM_CURATE_PERCENTAGE = 75

        return (
            self.curator_count() >= MINIMUM_CURATE_VOTES
            and self.average_curate_num() >= MINIMUM_CURATE_PERCENTAGE
        )

    # == to dict and to string ==

    def to_dict(self):
        # value_array = [value.to_dict() for value in self.value_inputs]
        # curate_array = [curate.to_dict() for curate in self.curate_inputs]
        # tag_array = [tag.to_dict() for tag in self.tag_inputs]
        return {
            "ce_id": self.ce_id,
            "value": [value.to_dict() for value in self.value_inputs],
            "curate": [curate.to_dict() for curate in self.curate_inputs],
            "tags": [tag.to_dict() for tag in self.tag_inputs],
        }

    def to_string(
        self, database_name: list[CEGame], database_user: list[CEUser]
    ) -> str:
        # grab the game object
        game = hm.get_item_from_list(self.ce_id, database_name)
        if game is None:
            raise Exception(
                f"Could not find game with ID {self.ce_id} in database_name."
            )

        returned_string: str = ""

        # show game name
        returned_string += f"Game: {game.name_with_link}\n"

        # show value inputs
        returned_string += "Value Inputs:\n"
        for value_input in self.value_inputs:
            returned_string += value_input.to_string(
                database_name, database_user, self.ce_id
            )

        # show curate inputs
        returned_string += "Curate Inputs:\n"
        for curate_input in self.curate_inputs:
            returned_string += curate_input.to_string(database_user)
        returned_string += f"- Curate Percentage: {self.average_curate()}\n"

        # show tag inputs
        returned_string += "Tag Inputs:\n"
        returned_string += "- Tag Inputs are not yet available."  # TODO: tag

        return returned_string

    def to_string_simple(self, database_name: list[CEGame]) -> str:
        "Returns this Input as a simple string."

        # grab the game object
        game = hm.get_item_from_list(self.ce_id, database_name)
        if game is None:
            raise Exception(
                f"Could not find game with ID {self.ce_id} in database_name."
            )

        returned_string: str = ""

        # show game name
        returned_string += f"Game: {game.name_with_link}\n"

        # show value inputs
        returned_string += "Value Inputs:\n"
        for value_input in self.value_inputs:
            returned_string += value_input.to_string_simple(database_name, self.ce_id)

        # show curate inputs
        returned_string += "Curate Inputs:\n"
        returned_string += f"- Curate Percentage: {self.average_curate()}\n"

        # show tag inputs
        returned_string += "Tag Inputs:\n"
        returned_string += "- Tag Inputs are not yet available."  # TODO: tag

        return returned_string
