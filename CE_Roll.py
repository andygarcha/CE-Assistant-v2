import datetime
from typing import Literal

import hm

multi_stage_rolls = Literal["Two Week T2 Streak", 
                            "Two \"Two Week T2 Streak\" Streak", 
                            "Fourward Thinking"]

roll_cooldowns = {
    'Destiny Alignment' : hm.months_to_days(1),
    'Soul Mates' : {
        'Tier 1' : 7*10,
        'Tier 2' : 7*8,
        'Tier 3' : 7*6,
        'Tier 4' : 7*4,
        'Tier 5' : 7*2
    },
    'Teamwork Makes the Dream Work' : hm.months_to_days(3),
    'Winner Takes All' : hm.months_to_days(3),
    'Game Theory' : hm.months_to_days(1),

    'One Hell of a Day' : 14,
    'One Hell of a Week' : hm.months_to_days(1),
    'One Hell of a Month' : hm.months_to_days(3),
    'Two Week T2 Streak' : None,
    'Two "Two Week T2 Streak" Streak' : None,
    'Never Lucky' : hm.months_to_days(1),
    'Triple Threat' : hm.months_to_days(3),
    'Let Fate Decide' : hm.months_to_days(3),
    'Fourward Thinking' : None
}

roll_due_times = {
    'One Hell of a Day' : 1,
    'One Hell of a Week' : 7,
    'One Hell of a Month' : hm.months_to_days(1),
    'Two Week T2 Streak' : 7,
    'Two "Two Week T2 Streak" Streak' : 7,
    'Never Lucky' : None,
    'Triple Threat' : hm.months_to_days(1),
    'Let Fate Decide' : None,
    'Fourward Thinking' : 7, #NOTE: this is dynamically updated later

    'Destiny Alignment' : None,
    'Soul Mates' : {
        'Tier 1' : 2,
        'Tier 2' : 10,
        'Tier 3' : hm.months_to_days(1),
        'Tier 4' : hm.months_to_days(2),
        'Tier 5' : None
    }
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

        # set the rerolls to the correct amount
        if rerolls == None :
            self._rerolls = None
        else :
            self._rerolls = rerolls

    # ------- getters -------

    @property
    def roll_name(self) -> hm.roll_event_names :
        """Get the name of the roll event."""
        return self._roll_name
    
    @property
    def user_ce_id(self) -> str :
        """Get the Challenge Enthusiast ID of the roller."""
        return self._user_ce_id
    
    @property
    def init_time(self):
        """Get the unix timestamp of the time the roll was, well, rolled."""
        return self._init_time
    
    @property
    def due_time(self):
        """Get the unix timestamp of the time the roll will end."""
        return self._due_time
    
    @property
    def completed_time(self):
        """Get the unix timestamp of the time the roll was completed 
        (will be `None` if active)."""
        return self._completed_time
    
    @property
    def games(self) :
        """Get the list of games as an array of their Challenge Enthusiast IDs."""
        return self._games
    
    @property
    def partner_ce_id(self) :
        """Get the Challenge Enthusiast ID of the partner in this roll 
        (if one exists)."""
        return self._partner_ce_id
    
    @property
    def rerolls(self) :
        """If applicable, get the number of rerolls allowed for this roll event."""
        return self._rerolls
    
    # ------ setters -------

    def increase_rerolls(self, increase : int) -> None :
        """Increase the number of rerolls allowed for this roll event 
        given by `increase`."""
        self._rerolls += increase

    @completed_time.setter
    def completed_time(self, current_time : int) -> None :
        """Sets the time of completion for this roll event
        given by `current_time`."""
        self._completed_time = current_time

    def increase_due_time(self, increase_in_seconds : int) -> None :
        """Moves the due date of this roll event up 
        by `increase_in_seconds` seconds."""
        self._due_time += increase_in_seconds

    @due_time.setter
    def due_time(self, days : int) -> None :
        """Sets the due time for `days` days from now."""
        self._due_time = hm.get_unix(days=days)

    def add_game(self, game : str) -> None :
        """Adds the Challenge Enthusiast ID given by `game`
        to this roll's games array."""
        self._games.append(game)

    def initiate_next_stage(self) -> None :
        """Resets this roll's' variables for the next
        stage for a multi-stage roll."""
        if self.roll_name not in multi_stage_rolls : return

        if self.roll_name == "Two Week T2 Streak" :
            self.due_time = hm.get_unix(days=7)
        elif self.roll_name == "Two \"Two Week T2 Streak\" Streak" :
            self.due_time = hm.get_unix(days=7)
        elif self.roll_name == "Fourward Thinking" :
            self.due_time = hm.get_unix(
                days= len(self.games)*7
            )




    # ------ other methods ------

    def is_co_op(self) -> bool :
        """Returns true if this roll is co-op."""
        return self.partner_ce_id != None and self.partner_ce_id != ""
    
    def is_expired(self) -> bool :
        """Returns true if the roll has expired."""
        return self.due_time < hm.get_current_unix()
    
    def ends(self) -> bool :
        """Returns true if the roll can end."""
        return self.due_time != None
    
    def ready_for_next(self) -> bool :
        """Returns true if this game is ready for the next game."""
        if self.roll_name not in multi_stage_rolls : return False
        
        return self.due_time == None or self.due_time == 0
    
    async def get_win_message(self) -> str :
        """Returns a string to send to #casino-log if this roll is won."""
        #TODO: finish this function
        import Mongo_Reader
        from CE_User import CEUser
        from CE_Game import CEGame

        # pull the databases
        database_name = await Mongo_Reader.get_mongo_games()
        database_user = await Mongo_Reader.get_mongo_users()

        # and grab the objects
        user : CEUser = hm.get_item_from_list(self.user_ce_id, database_user)
        if self.is_co_op() : 
            partner : CEUser = hm.get_item_from_list(self.partner_ce_id, database_user)
        else :
            partner = None
        
        if self.roll_name == "Destiny Alignment" :
            return (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! " +
                "You have both completed Destiny Alignment together." +
                ("\n- " + hm.get_item_from_list(game, database_name).game_name for game in self.games)
            )
        elif self.roll_name == "Soul Mates" :
            return (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! " +
                "You have both completed Soul Mates together." +
                ("\n- " + hm.get_item_from_list(self.games[0], database_name).game_name) 
            )
        elif self.roll_name == "Teamwork Makes the Dream Work" :
            # get game objects
            game_objects = [game for game in database_name if game.ce_id in self.games]
            user_wins = []
            return (

            )
        return NotImplemented

    def get_fail_message(self) -> str :
        """Returns a string to send to #casino if this roll is failed."""
        #TODO: finish this function
        return NotImplemented
    
    def calculate_cooldown_date(self) -> int | None :
        """Calculates the date of which the cooldown should be set
        (or `None` if not applicable.)"""
        if self.roll_name == "Fourward Thinking" :
            return NotImplemented   #TODO: finish this !
        elif self.roll_name == "Soul Mates" :
            return NotImplemented   #TODO : finish this too!
        
        return roll_cooldowns[self.roll_name]

    async def is_won(self) -> bool :
        """Returns true if this roll instance has been won."""
        from CE_User import CEUser
        import Mongo_Reader
        if (self.is_expired()) : return False
        users = await Mongo_Reader.get_mongo_users()
        user = hm.get_item_from_list(self.user_ce_id, users)

        return NotImplemented
        
        # one hell of a month
        if(self.get_roll_name() == "One Hell of a Month") :
            categories : dict[str, int] = {}
            for category in hm.get_categories() :
                categories[category] = 0
            for game in main_player.get_owned_games() :
                if (game.get_ce_id() in self.games
                    and game.is_completed()) :
                    categories[game.get_category()] += 1
            completed_categories = 0
            for category in categories :
                if categories[category] >= 3 : completed_categories += 1
            return completed_categories >= 5

        # teamwork makes the dream work
        if(self.get_roll_name() == "Teamwork Makes the Dream Work") :
            for game in self.games :
                if ((main_player.get_owned_game(game) == None
                    or not main_player.get_owned_game(game).is_completed())
                    and partner_player.get_owned_game(game) == None
                    or not partner_player.get_owned_game(game).is_completed()) :
                    return False
            return True

        # winner takes all
        if(self.get_roll_name() == "Winner Takes All") :
            game = self.games[0]
            main_won = (main_player.get_owned_game(game) != None
                        and main_player.get_owned_game(game).is_completed())
            partner_won = (partner_player.get_owned_game(game) != None
                           and partner_player.get_owned_game(game).is_completed())
            return main_won or partner_won
        
        #TODO: finish this function
        
        

    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        d = {}
        if self.roll_name != None : d['Event Name'] = self.roll_name
        if self.due_time != None : d['Due Time'] = self.due_time
        if self.games != None : d['Games'] = self.games
        if self.partner_ce_id != None : 
            d['Partner ID'] = self.partner_ce_id
        if self.user_ce_id != None :
            d['User ID'] = self.user_ce_id
        if self.init_time != None :
            d['Init Time'] = self.init_time
        if self.completed_time != None :
            d['Completed Time'] = self.completed_time
        if self.rerolls != None :
            d['Rerolls'] = self.rerolls
        return d
    
