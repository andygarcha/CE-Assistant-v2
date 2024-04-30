import datetime
from typing import Literal
from CE_Game import CEGame
from CE_User import CEUser
import Mongo_Reader
import hm

roll_cooldowns = {
    'Destiny Alignment' : hm.months_to_days(1),
    'Game Theory' : hm.months_to_days(1),
    'Soul Mates' : hm
    #TODO: finish this
}

roll_due_times = {

}

class CERoll:
    """Roll event."""

    def __init__(self,
                 roll_name : hm.roll_event_names,
                 user_ce_id : str,
                 games : list[str],
                 partner_ce_id : str,
                 cooldown_days = None,
                 init_time = None,
                 due_time = None,
                 completed_time = None,
                 rerolls = None):
        self._roll_name : str = roll_name
        self._user_ce_id : str = user_ce_id
        self._games : list[str] = games
        self._partner_ce_id : str = partner_ce_id

        if cooldown_days == None:
            self._cooldown_days = roll_cooldowns[self._roll_name]
        else :
            self._cooldown_days = cooldown_days
        if init_time == None :
            self._init_time = hm.get_unix('now')
        else :
            self._init_time = init_time
        if due_time == None :
            self._due_time = hm.get_unix(days=roll_due_times[self._roll_name])
        else :
            self._due_time = due_time
        if completed_time == None :
            self._completed_time = None
        else :
            self._completed_time = completed_time
        if rerolls == None :
            self._rerolls = None
        else :
            self._rerolls = rerolls

    # ------- getters -------

    def get_roll_name(self):
        """Get the name of the roll event."""
        return self._roll_name
    
    def get_user_ce_id(self) -> str :
        """Get the Challenge Enthusiast ID of the roller."""
        return self._user_ce_id
    
    #async def get_user_object(self) -> CEUser :
    #    """Returns the :class:`CEUser` object."""
    #    return Mongo_Reader.get_user_from_id(self.get_user_ce_id())
    
    def get_init_time(self):
        """Get the unix timestamp of the time the roll was, well, rolled."""
        return self._init_time
    
    def get_due_time(self):
        """Get the unix timestamp of the time the roll will end."""
        return self._due_time
    
    def get_completed_time(self):
        """Get the unix timestamp of the time the roll was completed 
        (will be `None` if active)."""
        return self._completed_time
    
    def get_games(self) :
        """Get the list of games as an array of their Challenge Enthusiast IDs."""
        return self._games
    
    def get_partner_ce_id(self) :
        """Get the Challenge Enthusiast ID of the partner in this roll 
        (if one exists)."""
        return self._partner_ce_id
    
    #async def get_partner_object(self) -> CEUser :
    #    """Returns the :class:`CEUser` object."""
    #    return Mongo_Reader.get_user_from_id(self.get_partner_ce_id())
    
    def get_cooldown_days(self) :
        """Get the number of cooldown days associated with this roll event."""
        return self._cooldown_days
    
    def get_rerolls(self) :
        """If applicable, get the number of rerolls allowed for this roll event."""
        return self._rerolls
    
    # ------ setters -------

    def increase_cooldown_days(self, increase : int) -> None :
        """Increase the number of cooldown days for this roll event 
        given by `increase`."""
        self._cooldown_days += increase

    def increase_rerolls(self, increase : int) -> None :
        """Increase the number of rerolls allowed for this roll event 
        given by `increase`."""
        self._rerolls += increase

    def set_completed_time(self, current_time : int) -> None :
        """Sets the time of completion for this roll event
        given by `current_time`."""
        self._completed_time = current_time

    def increase_due_time(self, increase_in_seconds : int) -> None :
        """Moves the due date of this roll event up 
        by `increase_in_seconds` seconds."""
        self._due_time += increase_in_seconds

    def is_co_op(self) -> bool :
        """Returns true if this roll is co-op."""
        return self.get_partner_ce_id() != None and self.get_partner_ce_id != ""

    # ------ other methods ------

    def is_expired(self) -> bool :
        """Returns true if the roll has expired."""
        return self.get_due_time() < hm.get_current_unix()
    
    def get_win_message(self) -> str :
        """Returns a string to send to #casino if this roll has won."""
        #TODO: finish this function

    def ends(self) -> bool :
        """Returns true if this roll has a due date, false if not."""
        #TODO: finish this function

    def is_won(self) -> bool :
        """Returns true if this roll instance has been won."""
        from CE_User import CEUser
        if (self.is_expired()) : return False
        main_player : CEUser = self.get_user_object()
        
        if (self.is_co_op()) :
            partner_player : CEUser = self.get_partner_object()
            
        # one hell of a month
        if(self.get_roll_name() == "One Hell of a Month") :
            categories : dict[str, int] = {}
            for category in hm.get_categories() :
                categories[category] = 0
            for game in main_player.get_owned_games() :
                if (game.get_ce_id() in self.get_games()
                    and game.is_completed()) :
                    categories[game.get_category()] += 1
            completed_categories = 0
            for category in categories :
                if categories[category] >= 3 : completed_categories += 1
            return completed_categories >= 5

        # teamwork makes the dream work
        if(self.get_roll_name() == "Teamwork Makes the Dream Work") :
            for game in self.get_games() :
                if ((main_player.get_owned_game(game) == None
                    or not main_player.get_owned_game(game).is_completed())
                    and partner_player.get_owned_game(game) == None
                    or not partner_player.get_owned_game(game).is_completed()) :
                    return False
            return True

        # winner takes all
        if(self.get_roll_name() == "Winner Takes All") :
            game = self.get_games()[0]
            main_won = (main_player.get_owned_game(game) != None
                        and main_player.get_owned_game(game).is_completed())
            partner_won = (partner_player.get_owned_game(game) != None
                           and partner_player.get_owned_game(game).is_completed())
            return main_won or partner_won
        

    def to_dict(self) -> dict :
        d = {}
        if self.get_roll_name() != None : d['Event Name'] = self.get_roll_name()
        if self.get_due_time() != None : d['Due Time'] = self.get_due_time()
        #TODO: finish this