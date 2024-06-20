import datetime
from typing import Literal

import Modules.hm as hm

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
                 roll_name : hm.ALL_ROLL_EVENT_NAMES,
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
            self._init_time = init_time
            self._due_time = due_time
            self._completed_time = completed_time
            self._rerolls = rerolls
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

    # ------- properties -------

    @property
    def roll_name(self) -> hm.ALL_ROLL_EVENT_NAMES :
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
    def due_time(self, days : int, reset : bool) -> None :
        """Sets the due time for `days` days from now. 
        Additionally, you can reset the due time to `None`
        with `reset`."""
        if reset :
            self._due_time = None
        else :
            self._due_time = hm.get_unix(days=days)

    def add_game(self, game : str) -> None :
        """Adds the Challenge Enthusiast ID given by `game`
        to this roll's games array."""
        self._games.append(game)

    def initiate_next_stage(self) -> None :
        """Resets this roll's' variables for the next
        stage for a multi-stage roll."""
        if self.roll_name not in hm.MULTI_STAGE_ROLLS : return

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
        return (
            (self.partner_ce_id != None and self.partner_ce_id != "")
            or self.roll_name in hm.COOP_ROLL_EVENT_NAMES
        )
    
    def is_expired(self) -> bool :
        """Returns true if the roll has expired."""
        return self.due_time < hm.get_current_unix()
    
    def ends(self) -> bool :
        """Returns true if the roll can end."""
        return self.due_time != None
    
    def ready_for_next(self) -> bool :
        """Returns true if this game is ready for the next game."""
        if not self.is_multi_stage() : return False
        
        return self.due_time == None or self.due_time == 0
    
    def is_multi_stage(self) -> bool :
        "Returns true if this game is multi-stage."
        return self.roll_name in hm.MULTI_STAGE_ROLLS
    
    def in_final_stage(self) -> bool :
        "If this roll is multi-stage, this will return true if this event is in its final stage."
        if not self.is_multi_stage() : return False
        if self.roll_name == "Two Week T2 Streak" : return len(self.games) == 2
        if self.roll_name == "Two \"Two Week T2 Streak\" Streak" : return len(self.games) == 4
        if self.roll_name == "Fourward Thinking" : return len(self.games) == 4
    
    async def get_win_message(self) -> str :
        """Returns a string to send to #casino-log if this roll is won."""
        #TODO: finish this function
        import Modules.Mongo_Reader as Mongo_Reader
        from Classes.CE_User import CEUser
        from Classes.CE_Game import CEGame

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
                f"\n- <@{user.discord_id}> - {hm.get_item_from_list(self.games[0], database_name).game_name}" +
                f"\n- <@{partner.discord_id}> - {hm.get_item_from_list(self.games[1], database_name).game_name}"
            )
        elif self.roll_name == "Soul Mates" :
            return (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! " +
                "You have both completed Soul Mates together." +
                "\n- " + hm.get_item_from_list(self.games[0], database_name).game_name
            )
        elif self.roll_name == "Teamwork Makes the Dream Work" :
            # get all completed games by both users
            user_completions = user.get_completed_games_2(database_name)
            partner_completions = partner.get_completed_games_2(database_name)

            # go through each of them and decide if they were rolled in this game
            user_wins, partner_wins = [], []
            for compl in user_completions :
                if compl.ce_id in self.games : user_wins.append(compl.ce_id)
            for compl in partner_completions :
                if compl.ce_id in self.games : partner_wins.append(compl.ce_id)

            # and now make the actual string
            return_str = (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! " +
                "You have both completed Teamwork Makes the Dream Work.\n"
            )

            # go through each game and determine which game was completed by who
            for game in self.games :
                game_name = hm.get_item_from_list(game, database_name).game_name
                return_str += "- " + game_name
                if game in user_wins and game in partner_wins :
                    return_str += f" - <@{user.discord_id}> and <@{partner.discord_id}>\n"
                elif game not in user_wins and game in partner_wins :
                    return_str += f" - <@{partner.discord_id}>\n"
                elif game in user_wins and game not in partner_wins :
                    return_str += f" - <@{user.discord_id}>\n"
                else :
                    return_str += f"\n"
            return return_str
        elif self.roll_name == "Winner Takes All" :
            # determine winner
            user_wins = False
            partner_wins = False
            for game in user.get_completed_games_2(database_name) :
                if game.ce_id in self.games : user_wins = True
            for game in user.get_completed_games_2(database_name) :
                if game.ce_id in self.games : partner_wins = True
            
            # send corresponding message
            game_name = hm.get_item_from_list(self.games[0], database_name).game_name
            if user_wins and not partner_wins :
                return f"Congratulations to <@{user.discord_id}> for beating <@{partner.discord_id}> in Winner Takes All!\n- {game_name}"
            elif user_wins and partner_wins :
                return (f"<@{user.discord_id}> <@{partner.discord_id}> yall both won winner takes all?" + 
                        " i'm confused someone ping andy pls")
            elif not user_wins and partner_wins :
                return f"Congratulations to <@{partner.discord_id}> for beating <@{user.discord_id}> in Winner Takes All!\n- {game_name}"
            else :
                print(self)
                return "something's gone wrong with winner takes all. please ping andy!"
        elif self.roll_name == "Game Theory" :
            # determine winner
            user_wins, partner_wins = False, False
            user_game = self.games[0]
            partner_game = hm.get_item_from_list(self.partner_ce_id, database_user).get_current_roll(self.roll_name).games[0]
            for game in user.get_completed_games_2(database_name) :
                if game.ce_id == user_game : user_wins = True
            for game in user.get_completed_games_2(database_name) :
                if game.ce_id == partner_game : partner_wins = True

            # send corresponding message
            user_game_name = hm.get_item_from_list(user_game, database_name).game_name
            partner_game_name = hm.get_item_from_list(partner_game, database_name).game_name
            if user_wins and not partner_wins :
                return (
                    f"Congratulations to <@{user.discord_id}> for beating <@{partner.discord_id}> in Game Theory!" +
                    f"\n- <@{user.discord_id}> - {user_game_name}" +
                    f"\n- <@{partner.discord_id}> - {partner_game_name}"
                )
            elif user_wins and partner_wins :
                return (
                    f"<@{user.discord_id}> <@{partner.discord_id}>, yall both won game theory?" +
                    " i'm confused someone please ping andy"
                )
            elif not user_wins and partner_wins :
                return (
                    f"Congratulations to <@{partner.discord_id}> for beating <@{user.discord_id}> in Game Theory!" +
                    f"\n- <@{partner.discord_id}> - {partner_game_name}" +
                    f"\n- <@{user.discord_id}> - {user_game_name}"
                )
            else :
                print(self)
                return "something's gone wrong with game theory. please ping andy!"
        
        elif self.roll_name == "One Hell of a Month" :
            return_str = f"Congratulations <@{user.discord_id}>! You have beaten One Hell of a Month!"

            # get completions and their ids
            user_completions = user.get_completed_games_2(database_name)
            user_wins = []
            for game in user_completions :
                if game.ce_id in self.games : user_wins.append(game.ce_id)
            for game_id in self.games :
                if game_id not in user_wins : 
                    continue
                game = hm.get_item_from_list(game_id, database_name)
                if game_id not in user_wins :
                    return_str += "\n- " + game.game_name + " 🟥"
                return_str += "\n- " + game.game_name + " " + game.get_category_emoji()
            return return_str

        else :
            s = f"Congratulations <@{user.discord_id}>! You have beaten {self.roll_name}."
            for game in self.games :
                game_name = hm.get_item_from_list(game, database_name)
                s += f"\n- {game_name}"
            
        return NotImplemented

    def get_fail_message(self) -> str :
        """Returns a string to send to #casino if this roll is failed."""
        #TODO: finish this function
        return NotImplemented
    
    def calculate_cooldown_date(self) -> int | None :
        """Calculates the date of which the cooldown should be set
        (or `None` if not applicable)."""
        if self.roll_name == "Fourward Thinking" :
            return NotImplemented   #TODO: finish this !
        elif self.roll_name == "Soul Mates" :
            return NotImplemented   #TODO : finish this too!
        
        return roll_cooldowns[self.roll_name]

    async def is_won(self) -> bool :
        """Returns true if this roll instance has been won."""
        from Classes.CE_User import CEUser
        import Modules.Mongo_Reader as Mongo_Reader
        if (self.is_expired()) : return False
        database_user = await Mongo_Reader.get_mongo_users()
        database_name = await Mongo_Reader.get_mongo_games()
        user = hm.get_item_from_list(self.user_ce_id, database_user)
        if self.is_co_op() : partner = hm.get_item_from_list(self.partner_ce_id, database_user)
        
        # one hell of a month
        if(self.roll_name == "One Hell of a Month") :
            categories : dict[str, int] = {}
            for category in hm.get_categories() :
                categories[category] = 0
            for game in user.owned_games :
                if (game.ce_id in self.games and game.is_completed()) :
                    categories[game.get_category()] += 1
            completed_categories = 0
            for category in categories :
                if categories[category] >= 3 : completed_categories += 1
            return completed_categories >= 5

        # teamwork makes the dream work
        elif(self.roll_name == "Teamwork Makes the Dream Work") :
            for game in self.games :
                if (not user.has_completed_game(game, database_name)
                    and not partner.has_completed_game(game, database_name)) :
                        return False
            return True

        # winner takes all
        elif(self.roll_name == "Winner Takes All") :
            game = self.games[0]
            main_won = (user.has_completed_game(game, database_name))
            partner_won = (partner.has_completed_game(game, database_name))
            return main_won or partner_won
        
        #TODO: finish this function
        return NotImplemented
        
        

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
    
    def __str__(self) -> str :
        "Turns this object into a string representation."
        return (
            "-- CERoll --" +
            "\nEvent Name: " + self.roll_name +
            "\nDue Time: " + self.due_time +
            "\nGames: " + self.games +
            "\nUser CE ID: " + self.user_ce_id + 
            "\nPartner CE ID" + self.partner_ce_id +
            "\nInit Time: " + self.init_time +
            "\nCompleted Time: " + self.completed_time +
            "\nRerolls: " + self.rerolls
        )