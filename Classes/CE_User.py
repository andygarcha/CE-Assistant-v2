import datetime
import logging
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast, get_args

import aiohttp

import Modules.hm as hm
from Classes.CE_Game import CEGame
from Classes.CE_Roll import CERoll
from Classes.CE_User_Game import CEUserGame
from Classes.OtherClasses import CRData
from Modules import http_session

MUTELIST_CEIDS = ["e790e8f0-f67e-4646-8fa9-de436b2c8d5e"]  # athenavenny

RANK_THRESHOLDS = [
    (10000, 8),  # EX
    (7500, 7),  # SSS
    (5000, 6),  # SS
    (2500, 5),  # S
    (1000, 4),  # A
    (500, 3),  # B
    (250, 2),  # C
    (50, 1),  # D
]

logger = logging.getLogger(__name__)


class CEUser:
    """Class for the Challenge Enthusiast user."""

    def __init__(
        self,
        discord_id: int,
        ce_id: str,
        owned_games: list[CEUserGame],
        rolls: list[CERoll],
        display_name: str,
        avatar: str,
        last_updated: datetime.datetime,
        steam_id: str = "a",
    ):
        self._discord_id: int = discord_id
        self._ce_id: str = ce_id
        self._owned_games: list[CEUserGame] = owned_games
        self._rolls: list[CERoll] = rolls
        self._display_name: str = display_name
        self._avatar: str = avatar
        self._last_updated: datetime.datetime = last_updated
        self._steam_id: str = steam_id

    # ==== core properties ====

    @property
    def ce_id(self):
        """Returns the Challenge Enthusiasts ID associated with this user."""
        return self._ce_id

    @property
    def discord_id(self):
        """Returns the Discord ID associated with this user."""
        return self._discord_id

    @discord_id.setter
    def discord_id(self, input: int) -> None:
        """Sets this object's Discord ID according to `input`."""
        self._discord_id = input

    @property
    def display_name(self):
        "Returns the display name of this user."
        return self._display_name

    @property
    def avatar(self):
        "Returns the avatar of this user."
        return self._avatar

    @property
    def last_updated(self) -> datetime.datetime:
        "Returns the last updated time."
        return self._last_updated

    @last_updated.setter
    def last_updated(self, last_updated: datetime.datetime) -> None:
        "Setter for last updated."
        self._last_updated = last_updated

    # ==== identity / formatting ====

    @property
    def mention(self):
        "Returns the Discord ID with brackets (Example: '<@1234>')."
        return f"<@{self.discord_id}>"

    @property
    def display_name_with_link(self):
        return f"[{self.display_name}](<https://cedb.me/user/{self.ce_id}>)"

    @property
    def ce_link(self) -> str:
        "Returns the link to this user's Challenge Enthusiasts page."
        return f"https://cedb.me/user/{self.ce_id}"

    # ==== scoring ====

    def casino_score(self, rolls: list[CERoll]):
        """Returns the casino score associated with this user."""
        _casino_score = 0
        for roll in rolls:
            if roll.status == "failed":
                _casino_score += roll.casino_decrease()
            elif roll.status == "won":
                _casino_score += roll.casino_increase()
        return _casino_score

    @property
    def total_points(self):
        """Returns the total amount of points this user has."""
        total_points: int = 0
        for game in self._owned_games:
            total_points += game.user_points
        return total_points

    @property
    def rank(self) -> str:
        """Returns the current rank for this user."""
        ranks = ["E", "D", "C", "B", "A", "S", "SS", "SSS", "EX"]
        return f"{ranks[self.rank_num]} Rank"

    @property
    def rank_num(self) -> int:
        """
        Returns the rank as an int.
        - E Rank is 0
        - D Rank is 1
        - C Rank is 2
        - B Rank is 3
        - A Rank is 4
        - S Rank is 5
        - SS Rank is 6
        - SSS Rank is 7
        - EX Rank is 8
        """
        points = self.total_points
        for threshold, rank in RANK_THRESHOLDS:
            if points >= threshold:
                return rank
        return 0

    # ==== owned games ====

    @property
    def owned_games(self):
        """Returns a list of :class:`CEUserGame`s that this user owns."""
        return self._owned_games

    @owned_games.setter
    def owned_games(self, games):
        """Sets the 'owned games' to `games`."""
        self._owned_games = games

    def get_owned_game(self, ce_id: str) -> CEUserGame | None:
        """Returns the :class:`CEUserGame` object associated
        `ce_id`, or `None` if this user doesn't own it."""
        for game in self.owned_games:
            if game.ce_id == ce_id:
                return game
        return None

    def remove_owned_game(self, ce_id: str) -> bool:
        for i, game in enumerate(self.owned_games):
            if game.ce_id == ce_id:
                self.owned_games.pop(i)
                return True
        return False

    def replace_owned_game(self, game: CEUserGame) -> bool:
        for i, owned_game in enumerate(self.owned_games):
            if owned_game.ce_id == game.ce_id:
                self.owned_games[i] = game
                return True
        return False

    def owned_games_as_cegames(self, database_name: list[CEGame]) -> list[CEGame]:
        "Returns a list of this user's owned games as `CEGame`s."
        o: list[CEGame] = []
        for game in database_name:
            for owned_game in self.owned_games:
                if game.ce_id == owned_game.ce_id:
                    o.append(game)
        return o

    def get_completed_games(self, database_name: Sequence[CEGame]) -> list[CEGame]:
        """Returns a list of :class:`CEGame`'s that this user has completed."""
        if database_name is None:
            raise ValueError("Argument 'database_name' is None.")
        if None in database_name:
            raise ValueError("Argument 'database_name' contains None.")

        games_by_ce_id: dict[str, CEGame] = {}
        for game in database_name:
            games_by_ce_id.setdefault(game.ce_id, game)

        completed_games: list[CEGame] = []
        for game_user in self.owned_games:
            game_data = games_by_ce_id.get(game_user.ce_id)
            if game_data is None:
                logger.error(
                    "Could not find a game in database_name for %s", game_user.ce_id
                )
                continue
            if game_user.is_completed(game_data):
                completed_games.append(game_data)
        return completed_games

    def get_completed_games_all(
        self, database_name: Sequence[CEGame]
    ) -> tuple[list[CEGame], list[CEGame]]:
        """
        Returns two lists of `CEGame`s: completed games, and overcompleted games.
        """

        games_by_ce_id: dict[str, CEGame] = {}
        for game in database_name:
            games_by_ce_id.setdefault(game.ce_id, game)

        completed_games: list[CEGame] = []
        overcompleted_games: list[CEGame] = []
        for game_user in self.owned_games:
            game_data = games_by_ce_id.get(game_user.ce_id)
            if game_data is None:
                logger.error(
                    "Could not find a game in database_name for %s", game_user.ce_id
                )
                continue
            if game_user.is_completed(game_data):
                completed_games.append(game_data)
                if game_user.is_overcompleted(game_data):
                    overcompleted_games.append(game_data)
        return completed_games, overcompleted_games

    def get_objective(self, objective_id: str):
        "Takes in an ID and returns the CEUserObjective associated with it."
        for game in self.owned_games:
            for objective in game.user_objectives:
                if objective_id == objective.ce_id:
                    return objective

        return None

    def get_cr(self, database_name: list[CEGame]) -> CRData:
        "Returns the CR class."
        return CRData(owned_games=self.owned_games, database_name=database_name)

    def has_completed_game(self, game_id: str, database_name: list[CEGame]):
        "Returns true if this user has completed this game, returns false otherwise."
        for user_game in self.owned_games:
            if user_game.ce_id == game_id:
                return user_game.is_completed(database_name)
        return False

    def owns_game(self, game_id: str) -> bool:
        """Returns true if this user owns the game with
        Challenge Enthusiast ID `game_id`."""
        return any(game.ce_id == game_id for game in self.owned_games)

    def has_points(self, game_id: str) -> bool:
        """Returns true if this user has points in this game."""
        for game in self.owned_games:
            if game.ce_id == game_id:
                return game.user_points != 0
        return False

    def has_po_points(self, game_id: str) -> bool:
        """Returns true if this user has points in Primary Objectives in this game."""
        for game in self.owned_games:
            if game.ce_id == game_id:
                return game.primary_points != 0
        return False

    def completions(self, database_name: list[CEGame]) -> int:
        "Returns the number of completions this user has."
        games_by_ce_id: dict[str, CEGame] = {}
        for game in database_name:
            games_by_ce_id.setdefault(game.ce_id, game)
        completions = 0
        for owned_game in self.owned_games:
            if owned_game.is_completed(database_name=games_by_ce_id):
                completions += 1
        return completions

    # ==== moderation ====

    @property
    def is_muted(self) -> bool:
        """Returns true if the user is on the mutelist. Messages about this user should not
        be sent in #user-log or #casino-log."""
        return self.ce_id in MUTELIST_CEIDS

    # ==== network ====

    async def get_api_user(self) -> "CEAPIUser | None":
        "Returns the CEAPIUser."
        session = await http_session.get_session()
        async with session.get(f"https://cedb.me/api/user/{self.ce_id}/") as response:
            if response.status != 200:
                return None
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                return None

            return CEAPIUser(
                discord_id=self.discord_id,
                ce_id=self.ce_id,
                owned_games=self.owned_games,
                rolls=self.rolls,
                full_data=data,
                display_name=self.display_name,
                avatar=self.avatar,
                last_updated=self.last_updated,
            )

    # ======== rolls ======== #

    @property
    def rolls(self) -> list[CERoll]:
        "Returns an array of `CERoll`s."
        return self._rolls

    @property
    def past_rolls(self) -> list[CERoll]:
        return [
            roll
            for roll in self.rolls
            if (roll.status == "won" or roll.status == "failed")
        ]

    # ==== current rolls ==== #

    @property
    def current_rolls(self) -> list[CERoll]:
        """Returns an array of :class:`CERoll`'s
        that this user is currently participating in."""
        return [roll for roll in self.rolls if roll.status == "current"]

    def add_current_roll(self, roll: CERoll) -> None:
        """Adds `roll` to this user's Current Rolls section."""
        roll.set_status("current")
        self._rolls.append(roll)

    def fail_current_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES):
        "Fails a current roll associated with `roll_name`."
        if roll_name not in get_args(hm.ALL_ROLL_EVENT_NAMES):
            raise ValueError(
                f"Argument 'roll_name' in fail_current_roll is {roll_name}. User: {self.ce_id}"
            )

        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "current":
                self._rolls[i].status = "failed"
                return

        raise ValueError(f"User {self.ce_id} has no current roll {roll_name}.")

    def win_current_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES):
        "Wins a current roll associated with `roll_name`. Also sets completion time."
        if roll_name not in get_args(hm.ALL_ROLL_EVENT_NAMES):
            raise ValueError(
                f"Argument 'roll_name' in win_current_roll is {roll_name}. User: {self.ce_id}"
            )

        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "current":
                self._rolls[i].status = "won"
                self._rolls[i].completed_time = hm.get_datetime("now")
                return

        raise ValueError(f"User {self.ce_id} has no current roll {roll_name}.")

    def remove_current_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> None:
        "Removes `roll_name` from this user."
        if roll_name not in get_args(hm.ALL_ROLL_EVENT_NAMES):
            raise ValueError(
                f"Argument 'roll_name' in remove_current_roll is {roll_name}. User: {self.ce_id}"
            )

        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "current":
                self._rolls[i].status = "removed"
                return

        raise ValueError(f"User {self.ce_id} has no current roll {roll_name}.")

    def update_current_roll(self, roll: CERoll) -> bool:
        "Replaces the user's roll with a new one. Returns true if it works, false if not."
        if type(roll) is not CERoll:
            raise TypeError(
                f"Argument 'roll' is of type {type(roll)}. User: {self.ce_id}"
            )
        for i, event in enumerate(self.rolls):
            if event.roll_name == roll.roll_name and event.status == "current":
                self._rolls[i] = roll
                return True

        raise ValueError(
            f"No current roll was found with name {roll.roll_name} to be replaced."
        )

    def has_current_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> bool:
        """Returns true if this user is currently working on `roll_name`."""
        return any(event.roll_name == roll_name for event in self.current_rolls)

    def get_current_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> CERoll | None:
        "REturns the `CERoll` associated with `roll_name`."
        for event in self.current_rolls:
            if event.roll_name == roll_name:
                return event
        return None

    def has_current_roll_with(
        self, partner_ce_id, roll_name: hm.ALL_ROLL_EVENT_NAMES
    ) -> bool:
        """Returns true if this user has a DA roll with requested partner."""
        for event in self.current_rolls:
            if (event.roll_name == roll_name) and (
                event.partner_ce_id == partner_ce_id
            ):
                return True
        return False

    def count_current_rolls(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> int:
        """Returns the count of current DA rolls."""
        x = 0
        for event in self.current_rolls:
            if event.roll_name == roll_name:
                x += 1
        return x

    # ==== completed rolls ==== #

    @property
    def completed_rolls(self) -> list[CERoll]:
        """Returns an array of :class:`CERoll`'s
        that this user has previously completed."""
        return [
            roll
            for roll in self.rolls
            if roll.status == "won" or roll.status == "won_legacy"
        ]

    def add_completed_roll(self, roll: CERoll) -> None:
        """Adds `roll` to this user's Completed Rolls section."""
        roll.status = "won"
        self._rolls.append(roll)

    def remove_completed_rolls(self, roll_name: hm.ALL_ROLL_EVENT_NAMES):
        "Removes all completed rolls associated with roll_name."
        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "won":
                self._rolls[i].set_status("removed")

    def has_completed_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> bool:
        """Returns true if this user has completed `roll_name`."""
        return any(event.roll_name == roll_name for event in self.completed_rolls)

    def get_completed_rolls(
        self, roll_name: hm.ALL_ROLL_EVENT_NAMES
    ) -> list[CERoll] | None:
        """Returns the `CERoll` associated with `roll_name`."""
        r = [event for event in self.completed_rolls if event.roll_name == roll_name]
        if len(r) != 0:
            return r
        return None

    # ==== pending rolls ==== #

    @property
    def pending_rolls(self) -> list[CERoll]:
        """Returns an array of :class:`CECooldown`'s
        that this user stores in their Pending Rolls section."""
        return [roll for roll in self.rolls if roll.status == "pending"]

    def add_pending(self, event_name: hm.ALL_ROLL_EVENT_NAMES) -> None:
        """Adds `pending` to this user's Pending section."""
        self._rolls.append(
            CERoll(
                roll_name=event_name,
                user_ce_id=self.ce_id,
                games=None,
                status="pending",
                init_time=hm.get_datetime("now"),
                due_time=hm.get_datetime(minutes=10),
                _id=str(uuid.uuid4()),
            )
        )

    def remove_pending(self, pending: hm.ALL_ROLL_EVENT_NAMES):
        "Removes the pending from this user."
        for i, p in enumerate(self.rolls):
            if p.roll_name == pending and p.status == "pending":
                del self._rolls[i]
                break

    def get_pending(self, pending: hm.ALL_ROLL_EVENT_NAMES) -> CERoll | None:
        for p in self.rolls:
            if p.roll_name == pending and p.status == "pending":
                return p
        return None

    def has_pending(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> bool:
        """Returns true if this user is currently on pending for `roll_name`."""
        return any(pending.roll_name == roll_name for pending in self.pending_rolls)

    # ==== failed rolls ==== #

    @property
    def failed_rolls(self) -> list[CERoll]:
        return [roll for roll in self.rolls if roll.status == "failed"]

    def remove_failed_rolls(self, roll_name: hm.ALL_ROLL_EVENT_NAMES):
        "removes all failed rolls associated with roll_name."
        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "failed":
                del self._rolls[i]

    # ==== waiting rolls ==== #

    def has_waiting_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> bool:
        "Returns true if this user has a waiting roll."
        for roll in self.rolls:
            if roll.roll_name == roll_name and roll.status == "between_stages":
                return True
        return False

    def get_waiting_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> CERoll | None:
        "Returns the waiting roll."
        for roll in self.rolls:
            if roll.roll_name == roll_name and roll.status == "between_stages":
                return roll
        return None

    def update_waiting_roll(self, roll: CERoll) -> None:
        "Updates a waiting roll."
        for i, self_roll in enumerate(self.rolls):
            if (
                roll.roll_name == self_roll.roll_name
                and self_roll.status == "between_stages"
            ):
                self._rolls[i] = roll
                return

        roll.set_status("between_stages")
        self._rolls.append(roll)

    def unwait_waiting_roll(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> None:
        "Sets the waiting roll to current."
        for i, roll in enumerate(self.rolls):
            if roll.roll_name == roll_name and roll.status == "between_stages":
                self._rolls[i].status = "current"
                return

        raise ValueError(f"No waiting roll of name {roll_name} was found.")

    # ==== cooldowns ==== #

    def has_cooldown(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> bool:
        """Returns true if this user is currently on cooldown for `roll_name`."""
        # check infinite time rolls
        cooldown_time = self.get_cooldown_time(roll_name)
        return cooldown_time is not None and cooldown_time > hm.get_datetime("now")

    def get_cooldown_time(
        self, roll_name: hm.ALL_ROLL_EVENT_NAMES
    ) -> datetime.datetime | None:
        """Returns the datetime of the date `roll_name`'s cooldown ends
        (or `None` if not applicable.)"""
        # check infinite time rolls
        for roll in self.current_rolls:
            if roll.roll_name == roll_name:
                if roll.ends:
                    break
                return roll.calculate_cooldown_date()

        for roll in self.failed_rolls:
            if roll.roll_name == roll_name:
                cooldown_date = roll.calculate_cooldown_date()
                if cooldown_date is not None and cooldown_date > hm.get_datetime("now"):
                    return cooldown_date
        return None

    def get_cooldown_timestamp(self, roll_name: hm.ALL_ROLL_EVENT_NAMES) -> int | None:
        """
        Returns the UNIX Timestamp of the datetime that `roll_name`'s cooldown ends.
        If the user does not have a cooldown in this event, this will return None.
        """
        cooldown = self.get_cooldown_time(roll_name)
        if cooldown is None:
            return None
        return int(cooldown.timestamp())

    def had_cooldown(
        self, roll_name: hm.ALL_ROLL_EVENT_NAMES, old_time: datetime.datetime
    ) -> bool:
        """Returns true if this user was on cooldown for `roll_name` at `old_time`."""
        cooldown_time = self.get_cooldown_time(roll_name)
        return cooldown_time is not None and cooldown_time > old_time

    def clear_cooldowns(self):
        "Removes all cooldowns."
        raise NotImplementedError("There is no way to clear cooldowns anymore.")

    # ==== serialization ====

    def to_dict_supabase(self) -> dict:
        return {
            "ce_id": self.ce_id,
            "discord_id": self.discord_id,
            "display_name": self.display_name,
            "image_avatar": self.avatar,
            "updated_at_CE": self.last_updated,
            "created_at_CE": None,
            "steam_id": self._steam_id,
        }

    def to_dict_supabase_games(self) -> list[dict]:
        return [g.to_dict_supabase(self.ce_id) for g in self.owned_games]

    def to_dict_supabase_objectives(self) -> list[dict]:
        _objectives = []
        for game in self.owned_games:
            _objectives.extend(game.to_dict_supabase_objectives(self.ce_id))
        return _objectives

    def to_dict(self) -> dict:
        """Returns this user as a dictionary as used in the MongoDB database."""
        owned_games_array: list[dict] = []
        for game in self.owned_games:
            owned_games_array.append(game.to_dict())
        rolls_array = [roll.to_dict() for roll in self.rolls]

        return {
            "ce_id": self.ce_id,
            "discord_id": self.discord_id,
            "owned_games": owned_games_array,
            "rolls": rolls_array,
            "display-name": self.display_name,
            "avatar": self.avatar,
            "last_updated": self.last_updated,
            "steam_id": self._steam_id,
        }

    def __str__(self):
        "Returns the string representation about this CEUser."

        owned_games_array: list[dict] = []
        for game in self.owned_games:
            owned_games_array.append(game.to_dict())
        current_rolls_array: list[dict] = []
        for roll in self.current_rolls:
            current_rolls_array.append(roll.to_dict())
        completed_rolls_array: list[dict] = []
        for roll in self.completed_rolls:
            completed_rolls_array.append(roll.to_dict())
        pendings_array: list[dict] = []
        for pending in self.pending_rolls:
            pendings_array.append(pending.to_dict())

        return (
            "-- CEUser --"
            + "\nCE ID: "
            + self.ce_id
            + "\nDiscord ID: "
            + str(self.discord_id)
            + "\nOwned Games: "
            + str(owned_games_array)
            + "\nCurrent Rolls: "
            + str(current_rolls_array)
            + "\nCompleted Rolls: "
            + str(completed_rolls_array)
            + "\nPendings: "
            + str(pendings_array)
        )


class CEAPIUser(CEUser):
    "A user that's been pulled from the Challenge Enthusiasts API."

    def __init__(
        self,
        discord_id: int,
        ce_id: str,
        owned_games: list[CEUserGame],
        rolls: list[CERoll],
        full_data,
        display_name: str,
        avatar: str,
        last_updated: datetime.datetime,
        steam_id="b",
    ):
        super().__init__(
            discord_id,
            ce_id,
            owned_games,
            rolls,
            display_name,
            avatar,
            last_updated,
            steam_id,
        )
        self.__full_data = full_data

    @property
    def full_data(self):
        "Return the full API data."
        return self.__full_data

    @property
    def is_admin(self) -> bool:
        "Returns true if this user is an admin."
        return self.full_data["isAdmin"]

    @property
    def join_date(self) -> str:
        "Returns the string of when this user was created. Example: 2022-08-09T03:11:22.000Z"
        return self.full_data["createdAt"]

    @property
    def api_user_objectives(self) -> list:
        "Returns the list of api user objectives as a list."
        return self.full_data["userObjectives"]

    @property
    def api_user_games(self) -> list:
        "Returns the list of api games as a list."
        return self.full_data["userGames"]

    @property
    def api_tier_summary(self) -> list:
        return self.full_data["userTierSummaries"]

    def most_recent_objectives(self):
        "Returns a list of `CEObjective`s."

        # make a constant
        NUM_OF_OBJECTIVES = 3

        # imports
        if TYPE_CHECKING:
            from Classes.CE_User_Objective import CEUserObjective

        # grab all the data
        ce_ids: list[str] = []
        completion_dates: list[datetime.datetime] = []
        game_names: list[str] = []
        for objective in self.full_data["userObjectives"]:
            ce_ids.append(objective["objective"]["id"])
            completion_dates.append(hm.cetimestamp_to_datetime(objective["updatedAt"]))
            game_names.append(objective["objective"]["game"]["name"])

        # make sure they didn't request too much
        if len(ce_ids) < NUM_OF_OBJECTIVES:
            return None

        # sort and shear them to the number requested
        ordered_pairs = sorted(
            zip(completion_dates, ce_ids, game_names, strict=False), reverse=True
        )[0:NUM_OF_OBJECTIVES]

        # now get the objects and zip them with the completion dates
        objective_tuples: list[
            tuple[CEUserObjective | str, datetime.datetime, str]
        ] = []
        for pair in ordered_pairs:
            objective_object = self.get_objective(pair[1])
            objective_tuples.append(
                (
                    objective_object if objective_object is not None else pair[1],
                    pair[0],
                    pair[2],
                )
            )

        return objective_tuples

    def most_recent_objectives_str(self) -> str:
        "Returns the string for the most recent objectives."

        # pull the data
        objective_tuples = self.most_recent_objectives()
        if objective_tuples is None:
            return "Database out of sync! if this continues ping andy"

        # set up return
        return_str: str = ""

        # loop!
        for item in objective_tuples:
            # pull the actual items from the tuple
            objective = item[0]
            game_name = item[2]

            if isinstance(objective, str):
                return_str += (
                    f"Error, please ping andy. obj: {objective} game: {game_name}\n"
                )
                continue

            # add to the return string
            return_str += (
                f"{objective.name} ({objective.user_points} {hm.get_emoji('Points')}) "
                + f"- [{game_name}](https://cedb.me/game/{objective.game_ce_id}/)\n"
            )

        return return_str

    def monthly_report_str(self) -> str:
        "Returns a string report of the points this user has gained in the last two months."
        curr_month_points = 0
        prev_month_points = 0

        now = datetime.datetime.now(datetime.UTC)
        current_month_datetime = datetime.datetime(
            year=now.year, month=now.month, day=1, tzinfo=datetime.UTC
        )
        previous_month_datetime = datetime.datetime(
            year=(now.year if now.month != 1 else now.year - 1),
            month=(now.month - 1 if now.month != 1 else 12),
            day=1,
            tzinfo=datetime.UTC,
        )

        for api_objective in self.api_user_objectives:
            if (
                hm.cetimestamp_to_datetime(api_objective["updatedAt"])
                >= current_month_datetime
            ):
                if api_objective["partial"]:
                    curr_month_points += api_objective["objective"]["pointsPartial"]
                else:
                    curr_month_points += api_objective["objective"]["points"]
            elif (
                hm.cetimestamp_to_datetime(api_objective["updatedAt"])
                >= previous_month_datetime
            ):
                if api_objective["partial"]:
                    prev_month_points += api_objective["objective"]["pointsPartial"]
                else:
                    prev_month_points += api_objective["objective"]["points"]

        return (
            f"Points this month ({hm.current_month_str()}): {curr_month_points} {hm.get_emoji('Points')}\n"
            + f"Points last month ({hm.previous_month_str()}): {prev_month_points} {hm.get_emoji('Points')}"
        )

    def tier_genre_summary_str(self) -> str:
        "Returns a string report of the Tier and Genre Summary string to be sent."
        t1s, t2s, t3s, t4s, t5s = (0,) * 5
        genre_dict: dict[str, int] = {}

        # get the data
        total = -1
        for tier in self.api_tier_summary:
            genre_name = hm.genre_id_to_name(tier["genreId"])
            if genre_name is None:
                logger.error(
                    "Tried to find a category name for %s, returned None",
                    tier["genreId"],
                )
                raise Exception
            if genre_name == "Total":
                t1s = tier["tier1"]
                t2s = tier["tier2"]
                t3s = tier["tier3"]
                t4s = tier["tier4"]
                t5s = tier["tier5"]
                total = t1s + t2s + t3s + t4s + t5s
                continue
            genre_dict[genre_name] = tier["total"]

        # yeah
        LINE_BREAK_LIMIT = 3

        # set up categories
        return_str: str = ""
        i: int = 0
        for i, genre_name in enumerate(genre_dict):
            # syntax
            if i % LINE_BREAK_LIMIT == 0:
                return_str += "\n"

            # add the actual emoji and value
            return_str += f"{hm.get_emoji(cast('hm.CATEGORIES', genre_name))}: {genre_dict[genre_name]}\t"

        # set up tiers
        return_str += "\n"
        return_str += f"{hm.get_emoji('Tier 1')}: {t1s}\t{hm.get_emoji('Tier 2')}: {t2s}\t{hm.get_emoji('Tier 3')}: {t3s} \n"
        return_str += f"{hm.get_emoji('Tier 4')}: {t4s}\t{hm.get_emoji('Tier 5')}: {t5s}\tTotal: {total}"

        # and now return.
        return return_str
