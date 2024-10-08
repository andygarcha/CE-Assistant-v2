import datetime
from typing import Literal, get_args

import Modules.hm as hm

roll_cooldowns : dict[str, int] = {
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
    'Never Lucky' : None, #NOTE: needs to be fixed
    'Triple Threat' : hm.months_to_days(1),
    'Let Fate Decide' : None, #NOTE: needs to be fixed
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

def relative(tier_num : int) -> int :
    "Returns the relative points given by tier_num."
    match(tier_num) :
        case 1 : return 1
        case 2 : return 2
        case 3 : return 4
        case 4 : return 8
        case _ : return 20

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

    winner : `bool` or `None`
        The winner of this event, if it's PvP.
        True if this user, False if partner.

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
                 winner = None,
                 is_current : bool = False):
        self._roll_name : str = roll_name
        self._user_ce_id : str = user_ce_id
        self._games : list[str] = games
        self._partner_ce_id : str = partner_ce_id
        self._winner : bool = winner

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
        if due_time == None and roll_due_times[self._roll_name] is not None:
            self._due_time = hm.get_unix(days=roll_due_times[self._roll_name])
        elif due_time == None and roll_due_times[self._roll_name] is None :
            self._due_time = None
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
            if self.roll_name == "Fourward Thinking" : self._rerolls = 0
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
    
    @property
    def winner(self) -> bool :
        "Returns true if this person won the co-op, false if their partner won."
        return self._winner
    
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
        if days == None : self._due_time = None
        else: self._due_time = hm.get_unix(days=days)
    
    def reset_due_time(self) :
        "Resets the due time."
        # if fourward thinking, assume the new game has been added already.
        if self.roll_name == "Fourward Thinking" : 
            self._due_time = hm.get_unix(days=7*len(self.games))
        # if two week t2 streak, assume the new game has been added already.
        elif self.roll_name == "Two Week T2 Streak" or self.roll_name == "Two \"Two Week T2 Streak\" Streak" :
            self._due_time = hm.get_unix(days=7)
        # if its not, give it the default
        else :
            self._due_time = hm.get_unix(days=roll_due_times[self._roll_name])

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
                days=len(self.games)*7
            )

    @winner.setter
    def winner(self, new_winner : bool) :
        "Sets the winner."
        self._winner = new_winner


    # ------ other methods ------

    def is_co_op(self) -> bool :
        """Returns true if this roll is co-op or pvp."""
        return (
            (self.partner_ce_id != None and self.partner_ce_id != "")
            or self.roll_name in hm.COOP_ROLL_EVENT_NAMES
        )
    
    def is_pvp(self) -> bool :
        "Returns true if this roll is PvP."
        return self.roll_name in hm.PVP_ROLL_EVENT_NAMES
    
    def is_expired(self) -> bool :
        """Returns true if the roll has expired."""
        if self.due_time == None : return False
        return self.due_time < hm.get_unix('now')

    def is_completed(self) -> bool :
        "Return true if this roll has been completed."
        return self.completed_time is not None
    
    def ends(self) -> bool :
        """Returns true if the roll can end."""
        return self.due_time != None
    
    def ready_for_next(self) -> bool :
        """Returns true if this game is ready for the next game."""
        if not self.is_multi_stage() : return False
        
        return self.due_time == None or self.due_time == 0
    
    def is_multi_stage(self) -> bool :
        "Returns true if this roll is multi-stage."
        return self.roll_name in get_args(hm.MULTI_STAGE_ROLLS)
    
    def is_rerollable(self) -> bool :
        "Returns true if this roll is rerollable."
        return self.roll_name in ["Fourward Thinking"]
    
    def in_final_stage(self) -> bool :
        "If this roll is multi-stage, this will return true if this event is in its final stage."
        if not self.is_multi_stage() : return False
        if self.roll_name == "Two Week T2 Streak" : return len(self.games) == 2
        if self.roll_name == "Two \"Two Week T2 Streak\" Streak" : return len(self.games) == 4
        if self.roll_name == "Fourward Thinking" : return len(self.games) == 4

    def rolled_categories(self, database_name : list) -> list[str] :
        "Returns a list of the categories that have been rolled so far."
        # type casting
        from Classes.CE_Game import CEGame
        database_name : list[CEGame] = database_name

        return list(set([hm.get_item_from_list(game, database_name).category for game in self.games]))
    
    def get_win_message(self, database_name : list, database_user : list) -> str :
        """Returns a string to send to #casino-log if this roll is won."""
        import Modules.Mongo_Reader as Mongo_Reader
        from Classes.CE_User import CEUser
        from Classes.CE_Game import CEGame

        # pull the databases
        database_name : list[CEGame] = database_name
        database_user : list[CEUser] = database_user

        # and grab the objects
        user : CEUser = hm.get_item_from_list(self.user_ce_id, database_user)
        if self.is_co_op() : 
            partner : CEUser = hm.get_item_from_list(self.partner_ce_id, database_user)
        else :
            partner = None
        
        if self.roll_name == "Destiny Alignment" :
            return (
                f"Congratulations <@{user.discord_id}> and <@{partner.discord_id}>! " +
                "You have completed Destiny Alignment together. Sorry, but the backend is a little fucked: but here's one of the games! " +
                f"\n- <@{user.discord_id}> - {hm.get_item_from_list(self.games[0], database_name).game_name}"
            )
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
                self._winner = True
                return f"Congratulations to <@{user.discord_id}> for beating <@{partner.discord_id}> in Winner Takes All!\n- {game_name}"
            elif user_wins and partner_wins :
                return (f"<@{user.discord_id}> <@{partner.discord_id}> yall both won winner takes all?" + 
                        " i'm confused someone ping andy pls")
            elif not user_wins and partner_wins :
                self._winner = False
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
                self._winner = True
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
                self._winner = False
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
                s += f"\n- {game_name.game_name}"
            return s

            
    def get_fail_message(self, database_name : list, database_user : list) -> str :
        """Returns a string to send to #casino if this roll is failed."""
        #TODO: finish this function

        # imports and type hinting
        from Classes.CE_Game import CEGame
        from Classes.CE_User import CEUser
        database_name : list[CEGame] = database_name
        database_user : list[CEUser] = database_user

        # and grab the objects
        user : CEUser = hm.get_item_from_list(self.user_ce_id, database_user)
        if self.is_co_op() : 
            partner : CEUser = hm.get_item_from_list(self.partner_ce_id, database_user)
        else :
            partner = None

        if self.roll_name == "Fourward Thinking" :
            return (
                f"Sorry <@{user.discord_id}>, you failed your Tier {len(self.games)} in Fourward Thinking. " +
                f"You are now on cooldown for Fourward Thinking until <t:{self.calculate_cooldown_date()}>."
            )
        else :
            return (
                f"Sorry <@{user.discord_id}>, you failed your {self.roll_name} roll. " +
                f"You are now on cooldown for {self.roll_name} until <t:{self.calculate_cooldown_date()}>."
            )
    
    def calculate_cooldown_date(self, database_name : list = None) -> int | None :
        """Calculates the date of which the cooldown should be set
        (or `None` if not applicable)."""

        # imports and type casting
        if database_name is not None: 
            from Classes.CE_Game import CEGame
            database_name : list[CEGame] = database_name

        if self.roll_name == "Fourward Thinking" :
            if self.rerolls is None : self._rerolls = 0
            rerolls_used = len(self.games) - (self.rerolls + 1)
            days = len(self.games)*14 + hm.months_to_days(rerolls_used)
            return hm.get_unix(days=days, old_unix=self.init_time)
        
        elif self.roll_name == "Soul Mates" :
            game = hm.get_item_from_list(self.games[0], database_name)
            match(game.get_tier_num()) :
                case 1 : return hm.get_unix(10*7, old_unix=self.init_time)
                case 2 : return hm.get_unix(8*7, old_unix=self.init_time)
                case 3 : return hm.get_unix(6*7, old_unix=self.init_time)
                case 4 : return hm.get_unix(4*7, old_unix=self.init_time)
                case _ : return hm.get_unix(2*7, old_unix=self.init_time)
        
        if roll_cooldowns[self.roll_name] is None : return None
        return hm.get_unix(days=roll_cooldowns[self.roll_name], old_unix=self.init_time)

    def is_won(self, database_name : list, database_user : list) -> bool :
        """Returns true if this roll instance has been won."""
        # imports
        from Classes.CE_User import CEUser
        from Classes.CE_Game import CEGame
        import Modules.Mongo_Reader as Mongo_Reader

        # if expired, return false
        if (self.is_expired()) : return False

        # type hinting
        database_user : list[CEUser] = database_user
        database_name : list[CEGame] = database_name

        # get objects
        user = hm.get_item_from_list(self.user_ce_id, database_user)
        if self.is_co_op() : partner = hm.get_item_from_list(self.partner_ce_id, database_user)
        
        # one hell of a month
        if(self.roll_name == "One Hell of a Month") :
            categories : dict[str, int] = {}
            for category in get_args(hm.CATEGORIES) :
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
        
        # destiny alignment
        elif(self.roll_name == "Destiny Alignment") :
            return (
                user.has_completed_game(self.games[0], database_name) and
                partner.has_completed_game(self.games[1], database_name)
            )
        
        # soul mates
        elif(self.roll_name == "Soul Mates") :
            return (
                user.has_completed_game(self.games[0], database_name) and
                partner.has_completed_game(self.games[0], database_name)
            )
        
        # game theory
        elif(self.roll_name == "Game Theory") :
            return (
                user.has_completed_game(self.games[0], database_name) and
                partner.has_completed_game(self.games[1], database_name)
            )
        
            """
            # multistage rolls
            elif(self.is_multi_stage() and not self.in_final_stage()) : return False
            """

        # all other rolls
        else :
            for game in self.games :
                if not user.has_completed_game(game, database_name) : return False
            return True
        
        #TODO: finish this function
        return NotImplemented
        
    def casino_increase(self, database_name : list = None) -> int :
        "Returns the number of casino points the user would gain if the roll is won."

        # imports and type casting
        if database_name is not None :
            from Classes.CE_Game import CEGame
            database_name : list[CEGame] = database_name
            tier = hm.get_item_from_list(self.games[0], database_name).get_tier_num()

        # matches
        match(self.roll_name) :
            case "One Hell of a Day" : return 1
            case "One Hell of a Week" : return 7
            case "One Hell of a Month" : return 18
            case "Two Week T2 Streak" : return 4
            case "Two \"Two Week T2 Streak\" Streak" : return 12
            case "Never Lucky" : return 4
            case "Triple Threat" : return 15
            case "Let Fate Decide" : return 8
            case "Fourward Thinking" : return 18
            case "Destiny Alignment" : return relative(tier)
            case "Soul Mates" : return relative(tier)
            case "Teamwork Makes the Dream Work" : return 10
            case "Winner Takes All" : return relative(tier)
            case "Game Theory" : return 4
    
    def casino_decrease(self, database_name : list = None) -> int :
        "Returns the number of casino points the user would lose if the roll is lost."

        # imports and type casting
        if database_name is not None :
            from Classes.CE_Game import CEGame
            database_name : list[CEGame] = database_name
            tier = hm.get_item_from_list(self.games[0], database_name).get_tier_num()

        # matches
        match(self.roll_name) :
            case "One Hell of a Day" : return 0
            case "One Hell of a Week" : return -2
            case "One Hell of a Month" : return -5
            case "Two Week T2 Streak" : return -1
            case "Two \"Two Week T2 Streak\" Streak" : return -2
            case "Never Lucky" : return -1
            case "Triple Threat" : return -3
            case "Let Fate Decide" : return -2
            case "Fourward Thinking" : return -6
            case "Destiny Alignment" : return int(-1*relative(tier) / 3)
            case "Soul Mates" : return int(-1*relative(tier) / 2)
            case "Teamwork Makes the Dream Work" : return -2
            case "Winner Takes All" : return -1*relative(tier)
            case "Game Theory" : return -4



# ---------------- extra class stuff ----------------
        

    def to_dict(self) -> dict :
        """Turns this object into a dictionary for storage purposes."""
        return {
            "Event Name" : self.roll_name,
            "Due Time" : self.due_time,
            "Games" : self.games,
            "User ID" : self.user_ce_id,
            "Partner ID" : self.partner_ce_id,
            "Init Time" : self.init_time,
            "Completed Time" : self.completed_time,
            "Rerolls" : self.rerolls,
            "Winner" : self.winner
        }
    
    def __str__(self) -> str :
        "Turns this object into a string representation."
        return (
            "-- CERoll --" +
            f"\nEvent Name: {self.roll_name}" +
            f"\nDue Time: {self.due_time}" +
            f"\nGames: {self.games}" +
            f"\nUser CE ID: {self.user_ce_id}" + 
            f"\nPartner CE ID: {self.partner_ce_id}" +
            f"\nInit Time: {self.init_time}" +
            f"\nCompleted Time: {self.completed_time}" +
            f"\nRerolls: {self.rerolls}",
            f"\nWinner: {self.winner}"
        )
    
    def display_str(self, database_name : list, database_user : list) -> str :
        "Turns this object into a string representation to be sent to discord."

        # import and type hinting
        from Classes.CE_Game import CEGame
        from Classes.CE_User import CEUser
        database_name : list[CEGame] = database_name
        database_user : list[CEUser] = database_user

        if (
            self.games == self.partner_ce_id == self.due_time == self.completed_time == self.rerolls == None
            ) :
            return "Completed before CE Assistant's existance."

        # set up string
        string = ""

        # init time
        string += f"Rolled on <t:{self.init_time}>, "

        # due time
        if self.ends() :
            string += f"due on <t:{self.due_time}>, "
        
        # completed time
        if self.is_completed() :
            string += f"completed on <t:{self.completed_time}>, "
        
        # partner?
        if self.is_co_op() :
            partner = hm.get_item_from_list(self.partner_ce_id, database_user)
            string += f"partnered with <@{partner.discord_id}>, "

            # winner?
            if self.is_completed() :
                string += f"won by {'you' if self.winner else 'partner'}, "
        
        # rerolls
        if self.is_rerollable() :
            string += f"{self.rerolls} reroll(s) remaining, "

        # you're done. remove the ", "
        string = string[:-2]
        
        # rolled games
        if self.games is not None:
            # go get all the games from self.games
            games = [hm.get_item_from_list(game, database_name) for game in self.games]

            # now setup the string
            string += "\nRolled games: "
            for game in games :
                if game is None :
                    string += f"'ERROR', "
                else :
                    string += f"[{game.game_name}](https://cedb.me/game/{game.ce_id}/), "

            # you're done. remove the ", "
            string = string[:-2]
        
        return string