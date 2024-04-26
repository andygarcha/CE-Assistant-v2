import datetime
from typing import Literal
from CE_Game import CE_Game

class CE_Roll:
    """Roll event."""
    _roll_event_names = Literal["One Hell of a Day", "One Hell of a Week", "One Hell of a Month",
                         "Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak", "Never Lucky",
                         "Triple Threat", "Let Fate Decide", "Fourward Thinking", "Russian Roulette",
                         "Destiny Alignment", "Soul Mates", "Teamwork Makes the Dream Work", "Winner Takes All",
                         "Game Theory"]
    def __init__(self,
                 roll_name : _roll_event_names,
                 init_time,
                 due_time,
                 completed_time,
                 games,
                 partner_ce_id,
                 cooldown_days,
                 rerolls):
        self._roll_name : str = roll_name
        self._init_time : int = init_time
        self._due_time : int = due_time
        self._completed_time : int = completed_time
        self._games : list[str] = games
        self._partner_ce_id : str = partner_ce_id
        self._cooldown_days : int = cooldown_days
        self._rerolls : int = rerolls

    # ------- getters -------

    def get_roll_name(self):
        """Get the name of the roll event."""
        return self._roll_name
    
    def get_init_time(self):
        """Get the unix timestamp of the time the roll was, well, rolled."""
        return self._init_time
    
    def get_due_time(self):
        """Get the unix timestamp of the time the roll will end."""
        return self._due_time
    
    def get_completed_time(self):
        """Get the unix timestamp of the time the roll was completed (will be `None` if active)."""
        return self._completed_time
    
    def get_games(self) :
        """Get the list of games as an array of their Challenge Enthusiast IDs."""
        return self._games
    
    def get_partner_ce_id(self) :
        """Get the Challenge Enthusiast ID of the partner in this roll (if one exists)."""
        return self._partner_ce_id
    
    def get_cooldown_days(self) :
        """Get the number of cooldown days associated with this roll event."""
        return self._cooldown_days
    
    def get_rerolls(self) :
        """If applicable, get the number of rerolls allowed for this roll event."""
        return self._rerolls
    
    # ------ setters -------

    def increase_cooldown_days(self, increase : int) -> None :
        """Increase the number of cooldown days for this roll event given by `increase`."""
        self._cooldown_days += increase

    def increase_rerolls(self, increase : int) -> None :
        """Increase the number of rerolls allowed for this roll event given by `increase`."""
        self._rerolls += increase

    def set_completion_time(self, current_time : int) -> None :
        """Sets the time of completion for this roll event given by `current_time`."""
        self._completed_time = current_time

    # ------ other methods ------
    def is_expired(self) -> bool :
        return self.get_due_time() < self._get_current_unix()
    
    # ------ private methods ------
    def _get_current_unix() -> int :
        dt = datetime.datetime.now(datetime.timezone.utc)

        dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()