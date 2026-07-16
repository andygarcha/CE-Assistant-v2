from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Literal, get_args

import Modules.hm as hm

if TYPE_CHECKING:
    from Classes.CE_Game import CEGame
    from Classes.CE_User import CEUser
    from utils.game_utils import CATEGORIES

logger = logging.getLogger(__name__)

roll_cooldowns: dict[str, int | None | dict[int, int]] = {
    "Destiny Alignment": hm.months_to_days(1),
    "Soul Mates": {1: 7 * 10, 2: 7 * 8, 3: 7 * 6, 4: 7 * 4, 5: 7 * 2},
    "Teamwork Makes the Dream Work": hm.months_to_days(3),
    "One Hell of a Day": 7,
    "One Hell of a Week": hm.months_to_days(1),
    "One Hell of a Month": hm.months_to_days(3),
    "Two Week T2 Streak": None,
    'Two "Two Week T2 Streak" Streak': None,
    "Never Lucky": hm.months_to_days(1),
    "Triple Threat": hm.months_to_days(3),
    "Let Fate Decide": hm.months_to_days(3),
    "Fourward Thinking": None,
}

roll_due_times = {
    "One Hell of a Day": 1,
    "One Hell of a Week": 7,
    "One Hell of a Month": hm.months_to_days(1),
    "Two Week T2 Streak": 7,
    'Two "Two Week T2 Streak" Streak': 7,
    "Never Lucky": None,  # NOTE: needs to be fixed
    "Triple Threat": hm.months_to_days(1),
    "Let Fate Decide": None,  # NOTE: needs to be fixed
    "Fourward Thinking": 7,  # NOTE: this is dynamically updated later
    "Destiny Alignment": None,
    "Soul Mates": {
        "Tier 1": 2,
        "Tier 2": 10,
        "Tier 3": hm.months_to_days(1),
        "Tier 4": hm.months_to_days(2),
        "Tier 5": None,
        "Tier 5+": None,
        "Tier 6": None,
    },
    "Teamwork Makes the Dream Work": hm.months_to_days(1),
}

CASINO_POINTS: dict[str, tuple[int, int] | None] = {
    # roll_name:                              (increase, decrease)
    "One Hell of a Day": (1, 0),
    "One Hell of a Week": (7, -2),
    "One Hell of a Month": (18, -5),
    "Two Week T2 Streak": (4, -1),
    'Two "Two Week T2 Streak" Streak': (12, -2),
    "Never Lucky": (4, -1),
    "Triple Threat": (15, -3),
    "Let Fate Decide": (8, -2),
    "Fourward Thinking": (18, -6),
    "Destiny Alignment": None,  # RELATIVE
    "Soul Mates": None,  # RELATIVE
    "Teamwork Makes the Dream Work": (10, -2),
}

RELATIVE: dict[int, int] = {
    1: 1,
    2: 2,
    3: 4,
    4: 8,
    # anything above is 20
}
"tier: hours"


def relative(tier_num: int) -> int:
    "Returns the relative points given by tier_num."
    return RELATIVE.get(tier_num, 20)


ROLL_STATUS = Literal[
    "current", "won", "failed", "pending", "between_stages", "removed", "won_legacy"
]
"""The status of rolls. 
Current means currently active.
Won means the roll has been completed and was won.
Failed means the roll was failed and was lost.
Pending is our normal 10-minute thing for discord.
BetweenStages is for multi-stage rolls.
Removed means the roll has been manually removed."""


class CERoll:
    """Roll event.

    Parameters
    ----------
    roll_name : `str | hm.roll_event_names`
        The name of the roll event.

    user_ce_id : `str`
        The Challenge Enthusiasts ID of the
        user that initiated the roll.

    games : `list[str]`
        A list of Challenge Enthusiast IDs
        assigned to the rolled games.

    partner_ce_id : `str` (optional)
        The Challenge Enthusiast ID of the
        partner for a co-op roll.

    init_time : `datetime.datetime`
        The datetime of the time this
        roll was initiated.

    due_time : `datetime.datetime` or `None`
        The datetime of the time this
        roll is due.

    completed_time : `datetime.datetime` or `None`
        The datetime of the time this
        roll was completed.

    rerolls : `int` or `None`
        The number of rerolls allowed (or `None`
        if no rerolls are allowed.)

    status : `str`
        The status of this roll. Can be one of these:
        'current', 'won', 'failed', 'pending', 'waiting', 'removed'

    tier_num : `int`
        This is only for Soul Mates. They get to choose their tier.
    """

    # def __init__(
    #     self,
    #     roll_name,
    #     user_ce_id,
    #     partner_ce_id,
    #     games,
    #     status,
    #     time_created,
    #     time_due,
    #     time_completed,
    #     rerolls,
    #     _id,
    #     tier_num
    # ):
    #     """Initializer"""
    #     self._roll_name = roll_name
    #     self._user_ce_id = user_ce_id
    #     self._games = games
    #     self._status = status
    #     self._partner_ce_id = partner_ce_id
    #     self._id = _id
    #     self._init_time = time_created
    #     self._due_time = time_due
    #     self._completed_time = time_completed
    #     self._rerolls = rerolls

    def __init__(
        self,
        roll_name: hm.ALL_ROLL_EVENT_NAMES,
        user_ce_id: str,
        games: list[str] | None,
        status: ROLL_STATUS,
        _id: str,
        partner_ce_id: str | None = None,
        init_time: datetime.datetime | None = None,
        due_time: datetime.datetime | None = None,
        completed_time: datetime.datetime | None = None,
        rerolls: int | None = None,
        is_current: bool = False,
        tier_num: int | None = None,
        tier_num_partner: int | None = None,
        lucky: bool = False,
    ):
        """Initializer for the CE Roll class."""
        self._roll_name: hm.ALL_ROLL_EVENT_NAMES = roll_name
        self._user_ce_id: str = user_ce_id
        if games is None:
            self._games = ["00000000-0000-0000-0000-000000000000"]
        else:
            self._games: list[str] = games
        self._status: ROLL_STATUS = status
        self._partner_ce_id: str | None = partner_ce_id
        self._id: str = _id
        self._tier_num: int | None = tier_num
        self._tier_num_partner: int | None = tier_num_partner
        self._lucky: bool = lucky

        # if the roll isn't being created right now
        # (and therefore is probably being read from Supabase)
        # normalize any string timestamps and don't reset variables
        if not is_current:
            self._init_time = (
                self._normalize_datetime(init_time) if init_time is not None else None
            )
            self._due_time = (
                self._normalize_datetime(due_time) if due_time is not None else None
            )
            self._completed_time = (
                self._normalize_datetime(completed_time)
                if completed_time is not None
                else None
            )
            self._rerolls: int | None = rerolls
            return

        # init time
        if init_time is None:
            self._init_time = hm.get_datetime("now")
        else:
            self._init_time = init_time

        # due time
        if due_time is None and roll_due_times[roll_name] is not None:
            if roll_name == "Soul Mates":
                self._due_time: datetime.datetime | None = hm.get_datetime(
                    days=roll_due_times["Soul Mates"][f"Tier {tier_num}"]
                )
            else:
                self._due_time: datetime.datetime | None = hm.get_datetime(
                    days=roll_due_times[roll_name]
                )
        else:
            self._due_time: datetime.datetime | None = due_time

        # completed time
        self._completed_time = completed_time

        # rerolls
        if self.roll_name == "Fourward Thinking":
            self._rerolls = 0
        else:
            self._rerolls = -1

    def __str__(self) -> str:
        "Turns this object into a string representation."
        return (
            "-- CERoll --"
            + f"\nEvent Name: {self.roll_name}"
            + f"\nDue Time: {self.due_time}"
            + f"\nGames: {self.games}"
            + f"\nUser CE ID: {self.user_ce_id}"
            + f"\nPartner CE ID: {self.partner_ce_id}"
            + f"\nInit Time: {self.init_time}"
            + f"\nCompleted Time: {self.completed_time}"
            + f"\nRerolls: {self.rerolls}"
            + f"\nStatus: {self.status}"
        )

    # ==== private helpers ====

    def _normalize_datetime(self, dt):
        """Convert string or naive datetime to timezone-aware datetime."""
        if dt is None:
            return None
        if isinstance(dt, str):
            try:
                dt = datetime.datetime.fromisoformat(dt)
            except Exception:
                try:
                    dt = hm.cetimestamp_to_datetime(dt)
                except Exception:
                    return None
        if isinstance(dt, datetime.datetime) and dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        return dt

    def _to_timestamp(self, datum) -> int | None:
        if isinstance(datum, datetime.datetime):
            return int(datum.timestamp())
        if isinstance(datum, int):
            return datum
        if isinstance(datum, float):
            return int(datum)
        if datum is None:
            return None
        logger.error("datum %s has type %s.", datum, type(datum))
        return None

    # ==== core properties ====

    @property
    def roll_name(self) -> hm.ALL_ROLL_EVENT_NAMES:
        """Get the name of the roll event."""
        return self._roll_name

    @property
    def user_ce_id(self) -> str:
        """Get the Challenge Enthusiast ID of the roller."""
        return self._user_ce_id

    @property
    def partner_ce_id(self) -> str | None:
        return self._partner_ce_id

    @property
    def games(self):
        """Get the list of games as an array of their Challenge Enthusiast IDs."""
        return self._games

    @property
    def status(self) -> ROLL_STATUS:
        "The status of this roll."
        return self._status

    @property
    def init_time(self):
        """Get the datetime of the time the roll was, well, rolled."""
        return self._init_time

    @property
    def due_time(self) -> datetime.datetime | None:
        """Get the datetime of the time the roll will end."""
        return self._due_time

    @property
    def completed_time(self):
        """Get the datetime of the time the roll was completed
        (will be `None` if active)."""
        return self._completed_time

    @property
    def rerolls(self) -> int | None:
        """If applicable, get the number of rerolls allowed for this roll event."""
        return self._rerolls

    @property
    def winner(self) -> bool:
        "Returns true if this person won the co-op, false if their partner won."
        return self.status == "won"

    @property
    def tier_num(self) -> int | None:
        return self._tier_num

    @property
    def tier_num_partner(self) -> int | None:
        return self._tier_num_partner

    @property
    def id(self) -> str:
        return self._id

    @property
    def lucky(self) -> bool:
        "Designates whether the roll was chosen for Jarvis's bonus (I don't even know what it is)"
        return self._lucky

    # ==== derived / boolean state properties ====

    @property
    def is_co_op(self) -> bool:
        """Returns true if this roll is co-op or pvp."""
        if self.partner_ce_id is not None and self.partner_ce_id != "":
            return True
        return self.roll_name in hm.COOP_ROLL_EVENT_NAMES_TUPLE

    @property
    def is_expired(self) -> bool:
        """Returns true if the roll has expired."""
        if self.due_time is None:
            return False

        dt = self.due_time
        if isinstance(dt, int):
            try:
                dt = datetime.datetime.fromtimestamp(dt, tz=datetime.UTC)
            except (OverflowError, OSError, ValueError) as e:
                logger.error(
                    "Expiration check failed. Due Time: %s, couldn't normalize int timestamp. %s",
                    self.due_time,
                    e,
                )
                return False

        # normalize string timestamps to datetime
        if isinstance(dt, str):
            try:
                dt = datetime.datetime.fromisoformat(dt)
            except Exception:
                try:
                    dt = hm.cetimestamp_to_datetime(dt)
                except Exception as e:
                    logger.error(
                        "Expiration check failed. Due Time: %s, couldn't normalize. %s",
                        self.due_time,
                        e,
                    )
                    return False

        if not isinstance(dt, datetime.datetime):
            logger.error(
                "Expiration check failed. Due Time: %s has unsupported type %s",
                self.due_time,
                type(dt),
            )
            return False

        # ensure timezone-aware for comparison
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)

        return dt < hm.get_datetime("now")

    @property
    def is_completed(self) -> bool:
        "Return true if this roll has been completed."
        return self.completed_time is not None

    @property
    def ends(self) -> bool:
        """Returns true if the roll can end."""
        return self.due_time is not None

    @property
    def ready_for_next(self) -> bool:
        """Returns true if this game is ready for the next game."""
        if not self.is_multi_stage:
            return False

        return self.due_time is None or self.due_time == 0

    @property
    def is_multi_stage(self) -> bool:
        "Returns true if this roll is multi-stage."
        return self.roll_name in get_args(hm.MULTI_STAGE_ROLLS)

    @property
    def is_rerollable(self) -> bool:
        "Returns true if this roll is rerollable."
        return self.roll_name in ["Fourward Thinking"]

    @property
    def in_final_stage(self) -> bool:
        "If this roll is multi-stage, this will return true if this event is in its final stage."
        if not self.is_multi_stage:
            return False
        if self.roll_name == "Two Week T2 Streak":
            return len(self.games) == 2
        if self.roll_name == 'Two "Two Week T2 Streak" Streak':
            return len(self.games) == 4
        if self.roll_name == "Fourward Thinking":
            return len(self.games) == 4
        return False

    @property
    def init_timestamp(self) -> int | None:
        return self._to_timestamp(self.init_time)

    @property
    def due_timestamp(self) -> int | None:
        return self._to_timestamp(self.due_time)

    @property
    def due_discord_timestamp(self) -> str | None:
        """
        Returns a `str` formatted like: <t:1234567890> (or <t:None>).
        """
        return f"<t:{self.due_timestamp}>"

    @property
    def completed_timestamp(self) -> int | None:
        return self._to_timestamp(self.completed_time)

    # ==== setters / mutators ====

    def set_status(self, new_status: ROLL_STATUS):
        "Setter for status"
        self._status = new_status

    @status.setter
    def status(self, new_status: ROLL_STATUS):
        self._status = new_status

    @completed_time.setter
    def completed_time(self, current_time: int | datetime.datetime) -> None:
        """Sets the time of completion for this roll event
        given by `current_time`."""
        self._completed_time = current_time

    @due_time.setter
    def due_time(self, days: int | None) -> None:
        """Sets the due time for `days` days from now."""
        if days is None:
            self._due_time = None
        else:
            self._due_time = hm.get_datetime(days=days)

    @winner.setter
    def winner(self, new_winner: bool):
        "Sets the winner."
        if new_winner:
            self.status = "won"
        else:
            self.status = "failed"

    def increase_rerolls(self, increase: int) -> None:
        """Increase the number of rerolls allowed for this roll event
        given by `increase`."""
        if self._rerolls is None:
            logger.error("Failed to read self.rerolls with Roll ID %s", self._id)
            raise Exception
        self._rerolls += increase

    def increase_due_time(self, increase_in_seconds: int) -> None:
        """Moves the due date of this roll event up
        by `increase_in_seconds` seconds."""
        dt = self._normalize_datetime(self._due_time)
        if dt is not None:
            self._due_time = dt + datetime.timedelta(seconds=increase_in_seconds)

    def reset_due_time(self):
        "Resets the due time."
        # if fourward thinking, assume the new game has been added already.
        if self.roll_name == "Fourward Thinking":
            self._due_time = hm.get_datetime(days=7 * len(self.games))
        # if two week t2 streak, assume the new game has been added already.
        elif (
            self.roll_name == "Two Week T2 Streak"
            or self.roll_name == 'Two "Two Week T2 Streak" Streak'
        ):
            self._due_time = hm.get_datetime(days=7)
        # if its not, give it the default
        else:
            self._due_time = hm.get_datetime(days=roll_due_times[self._roll_name])

    def add_game(self, game: str) -> None:
        """Adds the Challenge Enthusiast ID given by `game`
        to this roll's games array."""
        self._games.append(game)

    def remove_game_last(self) -> str:
        "Removes the most recently rolled game. Returns that game's ID."
        return self._games.pop()

    def initiate_next_stage(self) -> None:
        """Resets this roll's' variables for the next
        stage for a multi-stage roll."""
        if self.roll_name not in hm.MULTI_STAGE_ROLLS_TUPLE:
            return

        if (
            self.roll_name == "Two Week T2 Streak"
            or self.roll_name == 'Two "Two Week T2 Streak" Streak'
        ):
            self.due_time = 7
        elif self.roll_name == "Fourward Thinking":
            self.due_time = len(self.games) * 7

    def replace_game(self, original_id: str, replacement_id: str) -> bool:
        """
        Replaces a game in-place in this roll instance.
        Returns false if `original_id` is not in this game.
        """
        if original_id not in self.games:
            return False
        self.games[self.games.index(original_id)] = replacement_id
        return True

    # ==== complex logic ====

    def rolled_categories(self, database_name: list[CEGame]) -> list[CATEGORIES]:
        "Returns a list of the categories that have been rolled so far."

        _categories = set()
        for _game in self.games:
            _game_supa = hm.get_item_from_list(_game, database_name)
            if _game_supa is None:
                raise ValueError(
                    f"Could not find game {_game} in database_name. rolled_categories"
                )
            _categories.update(_game_supa.categories)
        return list(_categories)

    def get_win_message(
        self, database_name: list[CEGame], user: CEUser, partner: CEUser | None
    ) -> str:
        """
        Returns a string to send to #casino-log if this roll is won.
        This also sets the winner property if the roll is co-op.
        """
        # and grab the objects
        if not self.is_co_op:
            partner = None

        # destiny alignment
        if self.roll_name == "Destiny Alignment" and partner is not None:
            game0 = hm.get_item_from_list(self.games[0], database_name)
            if game0 is None:
                logger.error(
                    "Could not find game with ID %s in database_name.", self.games[0]
                )
                raise Exception("Could not find game with ID in database_name.")
            game1 = hm.get_item_from_list(self.games[1], database_name)
            if game1 is None:
                logger.error(
                    "Could not find game with ID %s in database_name.", self.games[1]
                )
                raise Exception("Could not find game with ID in database_name.")

            return (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! "
                + "You have both completed Destiny Alignment together."
                + f"\n- {user.mention} - {game0.name_with_link}"
                + f"\n- {partner.mention} - {game1.name_with_link}"
            )
        # soul mates
        if self.roll_name == "Soul Mates" and partner is not None:
            game0 = hm.get_item_from_list(self.games[0], database_name)
            if game0 is None:
                logger.error(
                    "Could not find game with ID %s in database_name.", self.games[0]
                )
                raise Exception("Could not find game with ID in database_name.")

            return (
                f"Congratulations {user.mention} and {partner.mention}! "
                + "You have both completed Soul Mates together."
                + f"\n- {game0.name_with_link}"
            )
        if self.roll_name == "Teamwork Makes the Dream Work" and partner is not None:
            # get all completed games by both users
            user_completions = user.get_completed_games(database_name)
            partner_completions = partner.get_completed_games(database_name)

            # go through each of them and decide if they were rolled in this game
            user_wins = partner_wins = []
            for compl in user_completions:
                if compl.ce_id in self.games:
                    user_wins.append(compl.ce_id)
            for compl in partner_completions:
                if compl.ce_id in self.games:
                    partner_wins.append(compl.ce_id)

            # and now make the actual string
            return_str = (
                f"Congratulations {user.mention} and {partner.mention}! "
                + "You have both completed Teamwork Makes the Dream Work.\n"
            )

            # go through each game and determine which game was completed by who
            for _game_id in self.games:
                _game_object = hm.get_item_from_list(_game_id, database_name)
                if _game_object is None:
                    logger.error(
                        "Could not find game with ID %s in database_name.", _game_id
                    )
                    raise Exception("Could not find game with ID in database_name.")

                return_str += "- " + _game_object.name_with_link

                if _game_id in user_wins and _game_id in partner_wins:
                    return_str += f" - {user.mention} and {partner.mention}\n"
                elif _game_id not in user_wins and _game_id in partner_wins:
                    return_str += f" - {partner.mention}\n"
                elif _game_id in user_wins and _game_id not in partner_wins:
                    return_str += f" - {user.mention}\n"
                else:
                    return_str += "\n"
            return return_str

        if self.roll_name == "One Hell of a Month":
            return_str = f"Congratulations <@{user.discord_id}>! You have beaten One Hell of a Month!"

            # get completions and their ids
            user_completions = user.get_completed_games(database_name)
            user_wins = []
            for game in user_completions:
                if game.ce_id in self.games:
                    user_wins.append(game.ce_id)
            for game_id in self.games:
                if game_id not in user_wins:
                    continue
                game = hm.get_item_from_list(game_id, database_name)
                if game is None:
                    logger.error(
                        "Could not find game with ID %s in database_name.", game_id
                    )
                    raise Exception("Could not find game with ID in database_name.")
                if game_id not in user_wins:
                    return_str += "\n- " + game.game_name + " 🟥"
                return_str += "\n- " + game.game_name + " " + game.category_emojis
            return return_str

        s = f"Congratulations {user.mention}! You have beaten {self.roll_name}."
        for game_id in self.games:
            game_object = hm.get_item_from_list(game_id, database_name)
            if game_object is None:
                logger.error(
                    "Could not find game with ID %s in database_name.", game_id
                )
                raise Exception("Could not find game with ID in database_name.")
            s += f"\n- {game_object.name_with_link}"
        return s

    def get_fail_message(
        self, database_name: list[CEGame], user: CEUser, partner: CEUser | None
    ) -> str:
        """
        Returns a string to send to #casino if this roll is failed.

        Parameters
        ---
        database_name: `list[CEGame]`
            A list of CEGame objects that will need to be
            referenced in this message.
        user: `CEUser`
            The user who rolled this event.
        partner: `CEUser | None`
            If this is a multi-player event, the user information
            for the partner.

        Returns
        ---
        message: `str`
            The message to be sent to #casino. Examples:
            - Sorry <@12345>, you have failed your Tier 1 in Fourward Thinking. You are now on cooldown
              for Fourward Thinking until <t:12345>.
            - Sorry <@12345> and <@67890>, you have failed your Soul Mates roll. You are now on cooldown for
              Soul Mates until <t:12345>.
            - Sorry <@12345>, you have failed your One Hell of a Day roll (Froggy's Battle). You are now on cooldown
              until <t:12345>
            - Sorry <@12345>, you have failed your Two Week T2 Streak roll. This event has no cooldown!

        """
        if self.roll_name == "Fourward Thinking":
            return (
                f"Sorry {user.mention}, you failed your Tier {len(self.games)} in Fourward Thinking. "
                + f"You are now on cooldown for Fourward Thinking until <t:{self.calculate_cooldown_timestamp()}>."
            )
        if self.is_co_op:
            if partner is None:
                return "Error code 5. Contact andy."
            return (
                f"Sorry {user.mention} and {partner.mention}, you failed your {self.roll_name} roll. "
                + f"You are now on cooldown for {self.roll_name} until <t:{self.calculate_cooldown_timestamp()}>."
            )
        if self.roll_name == "One Hell of a Day":
            game = hm.get_item_from_list(self.games[0], database_name)
            if game is None:
                logger.error(
                    "Could not find game with ID %s in database_name.", self.games[0]
                )
                raise Exception("Could not find game with ID in database_name.")
            return (
                f"Sorry {user.mention}, you failed your {self.roll_name} roll ({game.name_with_link}). "
                + f"You are now on cooldown for {self.roll_name} until <t:{self.calculate_cooldown_timestamp()}>."
            )
        if self.calculate_cooldown_date() is None:
            return (
                f"Sorry {user.mention}, you failed your {self.roll_name} roll. "
                "This event has no cooldown!"
            )
        return (
            f"Sorry <@{user.discord_id}>, you failed your {self.roll_name} roll. "
            + f"You are now on cooldown for {self.roll_name} until <t:{self.calculate_cooldown_timestamp()}>."
        )

    def get_initialization_message(self, database_name: list[CEGame]) -> str | None:
        """
        Creates the message sent when the roll is being rolled.

        This will return the message that's to be sent when the event is
        rolled for the first time (i.e. the user has just run /solo-roll).

        Returns
        ---
        The message to be sent to #casino on rolling
        """
        # get the actual game links
        game_strings: list[str] = []
        for g in self.games:
            _game_object = hm.get_item_from_list(g, database_name)
            if _game_object is None:
                return None
            game_strings.append(_game_object.name_with_link)
        # write the message
        message = (
            f"In your {self.roll_name} roll, "
            f"you rolled the following games: {hm.get_grammar_str(game_strings)}. "
        )
        # message was too long
        if len(message) > 1900:
            message = (
                f"In your {self.roll_name} roll, the games you rolled did not "
                "fit in one message. Please run /check-rolls to see the full list. "
            )
        # tack on at the end
        if self.ends:
            message += (
                f"You have until {self.due_discord_timestamp} to complete this event!"
            )
        else:
            message += "This event has no time limit."
            # TODO: allow for rerolls of co op rolls
            if not self.is_co_op:
                message += " To fail and restart this event, run /solo-roll again!"
        return message

    def get_reup_message(self, database_name: list[CEGame]) -> str | None:
        """
        Creates the message sent when the roll has been re-upped for a new round.

        This will return the message that's to announce
        the new game for the event. For example, if this is a Two Week T2 Streak
        roll, and self.status == "waiting", this will be the message sent to announce
        the second (and final) game in the roll.
        """
        game = hm.get_item_from_list(self.games[-1], database_name)
        if game is None:
            return None
        return (
            f"The next stage of your {self.roll_name} roll is {game.name_with_link}. "
            f"You have until {self.due_discord_timestamp} to complete this. Good luck!"
        )

    def calculate_cooldown_date(self) -> datetime.datetime | None:
        """Calculates the date of which the cooldown should be set
        (or `None` if not applicable)."""

        days: int | None | dict[int, int] = roll_cooldowns[self.roll_name]

        # Fourward thinking: num_games * 2 Weeks + num_rerolls_used * 1 Month
        if self.roll_name == "Fourward Thinking":
            if self._rerolls is None:
                self._rerolls = 0
            rerolls_used = len(self.games) - self._rerolls + 1
            days = len(self.games) * 14 + hm.months_to_days(rerolls_used)

        elif isinstance(days, dict):
            if self.tier_num is None:
                logger.error("Failed to read self.tier_num with Roll ID %s", self._id)
                raise Exception
            days = days[self.tier_num]

        # NOTE all special rules (like fourward thinking) must be above this line.
        elif days is None:
            return None

        return hm.get_datetime(days=days, old_datetime=self.init_time)

    def calculate_cooldown_timestamp(self) -> int | None:
        return self._to_timestamp(self.calculate_cooldown_date())

    def is_won(
        self, database_name: list[CEGame], user: CEUser, partner: CEUser | None = None
    ) -> bool:
        """
        Returns true if this roll instance has been won.
        """
        # if expired, return false
        if self.is_expired:
            return False

        # one hell of a month
        if self.roll_name == "One Hell of a Month":
            categories: dict[str, int] = {}
            for category in get_args(hm.CATEGORIES):
                categories[category] = 0
            for game in user.owned_games:
                if game.ce_id in self.games and game.is_completed(database_name):
                    # assumption here is that no dual-category games were rolled.
                    __category_check = game.get_categories(database_name)
                    if __category_check is None:
                        raise Exception(
                            "The correct game was not passed in through database_name."
                        )
                    if len(__category_check) > 1:
                        raise Exception("Cannot roll a dual-category game.")
                    if len(__category_check) == 0:
                        raise Exception("No categories are registered for this game.")

                    categories[__category_check[0]] += 1

            completed_categories = 0
            for category in categories:
                if categories[category] >= 3:
                    completed_categories += 1
            return completed_categories >= 5

        # teamwork makes the dream work
        if self.roll_name == "Teamwork Makes the Dream Work":
            if partner is None:
                logger.error(
                    "When evaluating if %s is won, partner was None.", self.roll_name
                )
                raise Exception
            for game in self.games:
                if not user.has_completed_game(
                    game, database_name
                ) and not partner.has_completed_game(game, database_name):
                    return False
            return True

        # destiny alignment
        if self.roll_name == "Destiny Alignment":
            if partner is None:
                logger.error(
                    "When evaluating if %s is won, partner was None.", self.roll_name
                )
                raise Exception
            return user.has_completed_game(
                self.games[0], database_name
            ) and partner.has_completed_game(self.games[1], database_name)

        # soul mates
        if self.roll_name == "Soul Mates":
            if partner is None:
                logger.error(
                    "When evaluating if %s is won, partner was None.", self.roll_name
                )
                raise Exception
            return user.has_completed_game(
                self.games[0], database_name
            ) and partner.has_completed_game(self.games[0], database_name)

        # all other rolls
        return all(user.has_completed_game(game, database_name) for game in self.games)

    def casino_increase(self) -> int:
        "Returns the number of casino points the user would gain if the roll is won."

        if self.roll_name not in CASINO_POINTS:
            return 0

        # relative points
        tup = CASINO_POINTS[self.roll_name]
        if tup is None:
            tier = self.tier_num
            if tier is None:
                raise Exception(
                    f"`tier_num` undefined for roll of type {self.roll_name}."
                )
            return relative(tier)

        # normal case
        return tup[0]

    def casino_decrease(self) -> int:
        "Returns the number of casino points the user would lose if the roll is lost."

        # relative points
        tup = CASINO_POINTS[self.roll_name]
        if tup is None:
            tier = self.tier_num
            if tier is None:
                tier = 1  # TODO cheating
            match self.roll_name:
                case "Destiny Alignment":
                    return int(-1 * relative(tier) / 3)
                case "Soul Mates":
                    return int(-1 * relative(tier) / 2)
                case _:
                    logger.error("Weird error #8. Roll ID %s", self._id)
                    raise Exception

        # normal case
        return tup[1]

    # ==== display information ====

    def to_dict(self) -> dict:
        """Turns this object into a dictionary for storage purposes."""
        return {
            "name": self.roll_name,
            "due_time": self.due_time,
            "init_time": self.init_time,
            "completed_time": self.completed_time,
            "games": self.games,
            "user_ce_id": self.user_ce_id,
            "partner_ce_id": self.partner_ce_id,
            "rerolls": self.rerolls,
            "status": self.status,
        }

    def display_str(self, database_name: list[CEGame]) -> str:
        "Turns this object into a string representation to be sent to discord."

        if (
            self.games
            == self.partner_ce_id
            == self.due_time
            == self.completed_time
            == self.rerolls
            is None
        ):
            return "Completed before CE Assistant's existance."

        # set up string
        string = ""

        # init time
        string += f"Rolled on <t:{self.init_timestamp}>, "

        # due time
        if self.ends:
            string += f"due on <t:{self.due_timestamp}>, "

        # completed time
        if self.is_completed:
            string += f"completed on <t:{self.completed_timestamp}>, "

        # partner?
        if self.is_co_op:
            string += f"partnered with <@{self.partner_ce_id}>, "

            # winner?
            if self.is_completed:
                string += f"won by {'you' if self.winner else 'partner'}, "

        # rerolls
        if self.is_rerollable:
            string += f"{self.rerolls} reroll(s) remaining, "

        # you're done. remove the ", "
        string = string[:-2]

        # rolled games
        if self.games is not None:
            # go get all the games from self.games
            games = [hm.get_item_from_list(game, database_name) for game in self.games]

            # now setup the string
            string += "\nRolled games: "
            for game in games:
                if game is None:
                    string += "'ERROR', "
                else:
                    string += (
                        f"[{game.game_name}](https://cedb.me/game/{game.ce_id}/), "
                    )

            # you're done. remove the ", "
            string = string[:-2]

        return string
