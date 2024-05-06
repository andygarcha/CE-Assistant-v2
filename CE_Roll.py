import datetime
from typing import Literal

import hm

roll_cooldowns = {
    'Destiny Alignment' : hm.months_to_days(1),
    'Soul Mates' : {
        1 : 7*10,
        2 : 7*8,
        3 : 7*6,
        4 : 7*4,
        5 : 7*2
    },
    'Teamwork Makes the Dream Work' : hm.months_to_days(3),
    'Winner Takes All' : hm.months_to_days(3),
    'Game Theory' : hm.months_to_days(1),
    'One Hell of a Day' : 14,
    'One Hell of a Week' : hm.months_to_days(1),
    'One Hell of a Month' : hm.months_to_days(3),
    'Two Week T2 Streak' : None,
    'Two "Two Week T2 Streak" Streak' : 7, #NOTE: this cant be right
    'Never Lucky' : hm.months_to_days(1),
    'Triple Threat' : hm.months_to_days(3),
    'Let Fate Decide' : hm.months_to_days(3),
    'Fourward Thinking' : 0 #NOTE: what the fuck do i do here
}

roll_due_times = {

}

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

    cooldown_date : `int` (only for storage purposes)
        Do not use this when instantiating a new roll.\n
        Only to be used when storing and grabbing
        this roll from the MongoDB database.

    init_time : `int`
        The unix timestamp of the time this
        roll was initiated.

    due_time : `int` or `None`
        The unix timestamp of the time this
        roll is due.

    completed_time : `int` or `None`
        The unix timestamp of the time this
        roll was completed.

    rerolls : `int` or `None`
        The number of rerolls allowed (or `None`
        if no rerolls are allowed.)

    is_current : `bool`
        Set this to true if you're declaring a
        new current roll.
    """

    def __init__(self,
                 roll_name : hm.roll_event_names,
                 user_ce_id : str,
                 games : list[str],
                 partner_ce_id : str = None,
                 init_time : int = None,
                 due_time = None,
                 completed_time = None,
                 rerolls = None,
                 is_current : bool = False):
        self._roll_name : str = roll_name
        self._user_ce_id : str = user_ce_id
        self._games : list[str] = games
        self._partner_ce_id : str = partner_ce_id

        # if the roll isn't being created right now
        # (and therefore is probably being read from MongoDB)
        # don't reset all the variables
        if not is_current : 
            self._init_time = None
            self._due_time = None
            self._completed_time = None
            self._rerolls = None
            return

        # if the roll is being created right now...
        # set init_time to right now
        if init_time == None :
            self._init_time = hm.get_unix('now')
        else :
            self._init_time = init_time

        # set the due time to the correct time
        if due_time == None :
            self._due_time = hm.get_unix(days=roll_due_times[self._roll_name])
        else :
            self._due_time = due_time

        # and set completed time to non-existent
        # (is this redundant code? am i stupid?)
        if completed_time == None :
            self._completed_time = None
        else :
            self._completed_time = completed_time

        if rerolls == None :
            self._rerolls = None
        else :
            self._rerolls = rerolls

    # ------- getters -------

    def get_roll_name(self) -> hm.roll_event_names :
        """Get the name of the roll event."""
        return self._roll_name
    
    def get_user_ce_id(self) -> str :
        """Get the Challenge Enthusiast ID of the roller."""
        return self._user_ce_id
    
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
    
    def get_rerolls(self) :
        """If applicable, get the number of rerolls allowed for this roll event."""
        return self._rerolls
    
    # ------ setters -------

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

    def set_due_time(self, days : int) -> None :
        """Sets the due time for `days` days from now."""
        self._due_time = hm.get_unix(days=days)

    def add_game(self, game : str) -> None :
        """Adds the Challenge Enthusiast ID given by `game`
        to this roll's games array."""
        self._games.append(game)



    # ------ other methods ------

    def is_co_op(self) -> bool :
        """Returns true if this roll is co-op."""
        return self.get_partner_ce_id() != None and self.get_partner_ce_id() != ""
    
    def is_expired(self) -> bool :
        """Returns true if the roll has expired."""
        return self.get_due_time() < hm.get_current_unix()
    
    def ends(self) -> bool :
        """Returns true if the roll can end."""
        return self.get_due_time() != None
    
    def ready_for_next(self) -> bool :
        """Returns true if this game is ready for the next game."""
        if self.get_roll_name() not in [
            "Two Week T2 Streak", "Two \"Two Week T2 Streak\" Streak", "Fourward Thinking"
        ] :
            return False
        
        return self.get_due_time() == None or self.get_due_time() == 0
        
    
    def get_win_message(self) -> str :
        """Returns a string to send to #casino-log if this roll is won."""
        #TODO: finish this function
        return NotImplemented

    def get_fail_message(self) -> str :
        """Returns a string to send to #casino if this roll is failed."""
        #TODO: finish this function
        return NotImplemented
    
    def calculate_cooldown_date(self) -> int | None :
        """Calculates the date of which the cooldown should be set
        (or `None` if not applicable.)"""
        if self.get_roll_name() == "Fourward Thinking" :
            return NotImplemented   #TODO: finish this !
        elif self.get_roll_name() == "Soul Mates" :
            return NotImplemented   #TODO : finish this too!
        
        return roll_cooldowns[self.get_roll_name()]

    async def is_won(self) -> bool :
        """Returns true if this roll instance has been won."""
        from CE_User import CEUser
        import Mongo_Reader
        if (self.is_expired()) : return False
        users = await Mongo_Reader.get_mongo_users()
        user = hm.get_item_from_list(self.get_user_ce_id(), users)

        return NotImplemented
        """
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
        
        #TODO: finish this function
        """
        

    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        d = {}
        if self.get_roll_name() != None : d['Event Name'] = self.get_roll_name()
        if self.get_due_time() != None : d['Due Time'] = self.get_due_time()
        if self.get_games() != None : d['Games'] = self.get_games()
        if self.get_partner_ce_id() != None : 
            d['Partner ID'] = self.get_partner_ce_id()
        if self.get_user_ce_id() != None :
            d['User ID'] = self.get_user_ce_id()
        if self.get_init_time() != None :
            d['Init Time'] = self.get_init_time()
        if self.get_completed_time() != None :
            d['Completed Time'] = self.get_completed_time()
        if self.get_rerolls() != None :
            d['Rerolls'] = self.get_rerolls()
        return d