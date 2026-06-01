from Classes.CE_Objective import CEObjective
from Classes.OtherClasses import CECompletion
import Modules.hm as hm
from Modules import http_session
import logging


logger = logging.getLogger(__name__)

TIER_THRESHOLDS = [
    (800, 7),  # T7
    (400, 6),  # T6
    (200, 5),  # T5
    (80, 4),  # T4
    (40, 3),  # T3
    (20, 2),  # T2
    (5, 1),  # T1
]


class CEGame:
    """A game that's on Challenge Enthusiasts."""

    def __init__(
        self,
        ce_id: str,
        game_name: str,
        platform: hm.PLATFORM_NAMES,
        platform_id: str,
        categories: list[hm.CATEGORIES],
        objectives: list[CEObjective],
        last_updated: None = None,
        banner: str = "",
    ):
        self._ce_id = ce_id
        self._game_name = game_name
        self._platform: hm.PLATFORM_NAMES = platform
        self._platform_id = platform_id
        self._categories = categories
        self._objectives = objectives
        self._banner = banner

    def __str__(self):
        "Returns the string representation of this object."
        return (
            "-- CEGame --"
            + "\nGame Name: "
            + self.game_name
            + "\nGame CE ID: "
            + self.ce_id
            + "\nTotal Points: "
            + str(self.get_total_points())
            + "\nPlatform: "
            + self.platform
            + "\nPlatform ID: "
            + str(self.platform_id)
            + "\nCategories: "
            + self.categories_string
            + "\nObjectives: "
            + str([objective.__str__() for objective in self.all_objectives])
        )

    # ==== core properties ====

    @property
    def ce_id(self) -> str:
        """Returns the Challenge Enthusiasts ID associated with this game."""
        return self._ce_id

    @property
    def game_name(self) -> str:
        """Returns the name of this game."""
        return self._game_name

    @property
    def platform(self) -> hm.PLATFORM_NAMES:
        """Returns the platform this game is hosted on."""
        return self._platform

    @property
    def platform_id(self) -> str:
        """Returns the ID value of this game on its platform."""
        return self._platform_id

    @property
    def categories(self) -> list[hm.CATEGORIES]:
        """Returns the categories of this game (e.g. Action, Arcade, Strategy)."""
        return self._categories

    @property
    def all_objectives(self) -> list[CEObjective]:
        """Returns the array of all `CEObjectives` in this game."""
        return self._objectives

    # ==== objective methods ====

    def get_primary_objectives(self, include_uncleareds=False) -> list[CEObjective]:
        """Returns the array of CEObjectives that are Primary.\n
        NOTE: This does not return uncleared objectives, unless you set `include_uncleareds = True`!"""
        p = []
        for objective in self.all_objectives:
            if objective.type == "Primary" and (
                not objective.is_uncleared() or include_uncleareds
            ):
                p.append(objective)
        return p

    def get_secondary_objectives(self, include_uncleareds=False) -> list[CEObjective]:
        "Returns an array of all secondary objectives."
        o = []
        for objective in self.all_objectives:
            if objective.type == "Secondary" and (
                not objective.is_uncleared() or include_uncleareds
            ):
                o.append(objective)
        return o

    def get_community_objectives(self) -> list[CEObjective]:
        """Returns the array of CEObjectives that are Community."""
        p = []
        for objective in self.all_objectives:
            if objective.type == "Community":
                p.append(objective)
        return p

    def get_uncleared_objectives(self) -> list[CEObjective]:
        "Returns an array of all uncleared objectives."
        o = []
        for objective in self.all_objectives:
            if objective.is_uncleared() and objective.type in ["Primary", "Secondary"]:
                o.append(objective)
        return o

    def get_badge_objectives(self) -> list[CEObjective]:
        "Returns an array of all badge objectives."
        o = []
        for objective in self.all_objectives:
            if objective.type == "Badge":
                o.append(objective)
        return o

    def get_objective(self, ce_id: str) -> CEObjective | None:
        """Returns the :class:`CEObjective` object associated
        with `ce_id`, or `None` if none exist."""
        for objective in self.all_objectives:
            if objective.ce_id == ce_id:
                return objective
        return None

    # ==== point totals ====

    def get_total_points(self) -> int:
        """Returns the total number of points this game has.\n
        NOTE: This does include uncleared points, as well as Primary and Secondary!"""

        INCLUDE_UNCLEAREDS: bool = True

        total_points = 0
        for objective in self.all_objectives:
            if objective.is_uncleared() and not INCLUDE_UNCLEAREDS:
                continue
            total_points += objective.point_value

        return total_points

    def get_po_points(self, include_uncleareds=False) -> int:
        """The total number of points in Primary Objectives.
        `include_uncleareds` (off by default) allows you to specify if
        uncleareds should be counted or not. As of now, uncleareds are
        worth 0 points so it won't matter, but we are implementing this
        now in the event of a future change."""
        total_points = 0
        # if we want to skip uncleareds, just filter them out in .get_primary_objectives()
        for objective in self.get_primary_objectives(
            include_uncleareds=include_uncleareds
        ):
            total_points += objective.point_value
        return total_points

    def get_so_points(self, include_uncleareds=False) -> int:
        "The total number of points in Secondary Objectives."
        total_points = 0
        for objective in self.get_secondary_objectives(include_uncleareds=include_uncleareds):
            total_points += objective.point_value
        return total_points

    # ==== tier methods ====

    @property
    def tier(self) -> str:
        """Returns the tier (e.g. `"Tier 1"`) of this game."""
        return f"Tier {self.tier_num}"

    @property
    def tier_num(self) -> int:
        """Returns the tier as an int. Tier 1 is 1, Tier 2 is 2, etc."""
        points = self.get_po_points(
            include_uncleareds=False
        )  # don't include uncleareds
        for threshold, tier in TIER_THRESHOLDS:
            if points >= threshold:
                return tier
        return 0

    @property
    def is_t0(self) -> bool:
        """Returns true if the game is a Tier 0."""
        return self.get_total_points() == 0

    @property
    def is_role_t4(self) -> bool:
        "Returns true if this game is a Role T4 (has a discord role associated with it)"
        po_points = self.get_po_points(include_uncleareds=False)
        return self.tier_num == 4 and po_points >= 150

    @property
    def is_t5plus(self) -> bool:
        "Returns true if this game is Tier 5 or above."
        return self.tier_num >= 5

    # ==== derived properties ====

    @property
    def has_uncleared(self) -> bool:
        """Returns true if this game has an uncleared objective."""
        for objective in self.all_objectives:
            if objective.is_uncleared():
                return True
        return False

    @property
    def has_uncleared_po(self) -> bool:
        """Returns true if this game has an Uncleared Primary Objective."""
        for objective in self.get_primary_objectives(include_uncleareds=True):
            if objective.is_uncleared():
                return True
        return False

    @property
    def has_uncleared_so(self) -> bool:
        """Returns true if this game has an Uncleared Secondary Objective."""
        for objective in self.get_secondary_objectives():
            if objective.is_uncleared():
                return True
        return False

    @property
    def ce_link(self) -> str:
        "Returns the link to the Challenge Enthusiasts page."
        return f"https://cedb.me/game/{self.ce_id}"

    @property
    def category_emojis(self) -> str:
        "Returns the category emojis for this game."
        _string = ""
        for cat in self.categories:
            _string += hm.get_emoji(cat)
        return _string

    @property
    def tier_emoji(self) -> str:
        "Returns the tier emoji for this game."
        return "" + hm.get_emoji(self.tier)  # type: ignore

    @property
    def emojis(self) -> str:
        "Returns the tier and category emojis for this game."
        return self.tier_emoji + self.category_emojis

    @property
    def name_with_link(self) -> str:
        "Returns the name with a link."
        return f"[{self.game_name}](https://cedb.me/game/{self.ce_id})"

    @property
    def categories_num(self) -> list[int]:
        "[Action, First-Person, Strategy] --> [1, 4, 6]"
        _nums = []
        for cat in self.categories:
            match cat:
                case "Action":
                    _nums.append(1)
                case "Arcade":
                    _nums.append(2)
                case "Bullet Hell":
                    _nums.append(3)
                case "First-Person":
                    _nums.append(4)
                case "Platformer":
                    _nums.append(5)
                case "Strategy":
                    _nums.append(6)
        return _nums

    @property
    def categories_string(self) -> str:
        "[Arcade, First-Person, Strategy] --> Arcade, First-Person, Strategy"
        return ", ".join(self.categories)

    # ==== mutators ====

    def add_objective(self, objective: CEObjective):
        """Adds an objective to the game's objective arrays."""
        self._objectives.append(objective)

    # ==== async / network ====

    async def get_raw_ce_data(self) -> dict:
        "Returns the raw CE data."
        session = await http_session.get_session()
        async with session.get(f"https://cedb.me/api/game/{self.ce_id}") as response:
            return await response.json()

    async def get_ce_api_game(self) -> "CEAPIGame":
        "Returns the CEAPIGame."
        return CEAPIGame(
            ce_id=self.ce_id,
            game_name=self.game_name,
            platform=self.platform,
            platform_id=self.platform_id,
            categories=self.categories,
            objectives=self.all_objectives,
            last_updated=None,
            full_data=await self.get_raw_ce_data(),
        )

    async def get_price_async(self) -> float | None:
        """Returns the current price (in USD) on the platform of this game."""
        if self.platform != "steam":
            return None

        session = await http_session.get_session()
        async with session.get(
            "https://store.steampowered.com/api/appdetails?",
            params={"appids": self.platform_id, "cc": "US"},
        ) as response:
            json_response = await response.json()

            steam_id = str(self.platform_id)

            if json_response[steam_id]["data"]["is_free"]:
                return 0
            elif "price_overview" in json_response[steam_id]["data"]:
                return float(
                    json_response[steam_id]["data"]["price_overview"][
                        "final_formatted"
                    ][1::]
                )
            else:
                return None
        return None

    async def get_steamhunters_data_async(self) -> int | None:
        if self.platform != "steam":
            return None
        session = await http_session.get_session()
        async with session.get(
            f"https://steamhunters.com/api/apps/{self.platform_id}"
        ) as response:
            raw_text = await response.text()
            if response.status != 200 or raw_text == "null" or raw_text == "":
                return None
            try:
                json_response = await response.json()
            except Exception as e:
                logger.error(
                    "SteamHunters response failed for Game ID: %s and Name: %s. Exception: %s",
                    self.ce_id,
                    self.game_name,
                    e,
                )
                return 999999

            if "medianCompletionTime" in json_response:
                return int(int(json_response["medianCompletionTime"]) / 60)
            else:
                return None

    async def get_completion_data(self) -> CECompletion:
        """Returns the completion data for this game."""

        session = await http_session.get_session()
        async with session.get(
            f"https://cedb.me/api/game/{self.ce_id}/leaderboard"
        ) as response:
            json_response = await response.json()

            completions, started, owners = (0,) * 3

            total_points = self.get_total_points()
            for user in json_response:
                if user["points"] == total_points:
                    completions += 1
                elif user["points"] != 0:
                    started += 1
                owners += 1

            return CECompletion(
                {"completed": completions, "started": started, "total": owners}
            )

    # ==== idk where you belong ====

    def to_dict(self) -> dict:
        """Turns this object into a dictionary for storage purposes."""
        objectives = []
        for objective in self.all_objectives:
            objectives.append(objective.to_dict())
        return {
            "name": self.game_name,
            "ce_id": self.ce_id,
            "platform": self.platform,
            "platform_id": self.platform_id,
            "categories": self.categories,
            "objectives": objectives,
            "banner": self._banner,
        }


class CEAPIGame(CEGame):
    """A game that's been pulled from the CE API."""

    def __init__(
        self,
        ce_id: str,
        game_name: str,
        platform: hm.PLATFORM_NAMES,
        platform_id: str,
        categories: list[hm.CATEGORIES],
        objectives: list[CEObjective],
        last_updated: None,
        full_data,
        banner="",
    ):
        super().__init__(
            ce_id,
            game_name,
            platform,
            platform_id,
            categories,
            objectives,
            None,
            banner,
        )
        self.__full_data = full_data

    @property
    def full_data(self):
        "Return the full API data."
        return self.__full_data

    @property
    def icon(self) -> str:
        "The icon for this game."
        return self.full_data["icon"]

    @property
    def is_finished(self) -> bool:
        "The game is not `unfinished`."
        return self.full_data["isFinished"]

    @property
    def information(self) -> str:
        "The information for this game."
        return self.full_data["information"]

    @property
    def header(self) -> str:
        "The header for this game."
        return self.full_data["header"]
