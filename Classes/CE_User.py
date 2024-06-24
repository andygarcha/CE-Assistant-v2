from Classes.CE_Cooldown import CECooldown
from Classes.CE_Roll import CERoll
from Classes.CE_Game import CEGame
from Classes.CE_User_Game import CEUserGame
import Modules.hm as hm


class CEUser:
    """Class for the Challenge Enthusiast user."""
    def __init__(self, 
                 discord_id : int, 
                 ce_id : str, 
                 casino_score : int, 
                 owned_games : list[CEUserGame],
                 current_rolls : list[CERoll], 
                 completed_rolls : list[CERoll], 
                 pending_rolls : list[CERoll], 
                 cooldowns : list[CERoll]):
        self._discord_id : int = discord_id
        self._ce_id : str = ce_id
        self._casino_score : int = casino_score
        self._owned_games : list[CEUserGame] = owned_games
        self._current_rolls : list[CERoll] = current_rolls
        self._completed_rolls : list[CERoll] = completed_rolls
        self._pending_rolls : list[CERoll] = pending_rolls
        self._cooldowns : list[CERoll] = cooldowns

    # ------------ getters -------------

    @property
    def ce_id(self) :
        """Returns the Challenge Enthusiasts ID associated with this user."""
        return self._ce_id
    
    @property
    def discord_id(self) :
        """Returns the Discord ID associated with this user."""
        return self._discord_id
    
    @property
    def casino_score(self) :
        """Returns the casino score associated with this user."""
        return self._casino_score

    def get_total_points(self):
        """Returns the total amount of points this user has."""
        total_points : int = 0
        for game in self._owned_games:
            total_points += game.get_user_points()
        return total_points
    
    def get_rank(self) -> str :
        """Returns the current rank for this user."""
        total_points = self.get_total_points()
        if total_points >= 10000 : return "EX Rank"
        elif total_points >= 7500 : return "SSS Rank"
        elif total_points >= 5000 : return "SS Rank"
        elif total_points >= 2500 : return "S Rank"
        elif total_points >= 1000 : return "A Rank"
        elif total_points >= 500 : return "B Rank"
        elif total_points >= 250 : return "C Rank"
        elif total_points >= 50 : return "D Rank"
        else : return "E Rank"

    @property
    def owned_games(self):
        """Returns a list of :class:`CEUserGame`s that this user owns."""
        return self._owned_games
    
    def get_owned_game(self, ce_id : str) -> CEUserGame | None :
        """Returns the :class:`CEUserGame` object associated 
        `ce_id`, or `None` if this user doesn't own it."""
        for game in self.owned_games :
            if game.ce_id == ce_id : return game
        return None

    def get_completed_games(self) -> list[CEUserGame] :
        """Returns a list of :class:`CEUserGame`'s that this user has completed.
        This is so fucking inefficient. Please don't use this."""
        completed_games : list[CEUserGame] = []

        for game in self._owned_games :
            if game.get_regular_game().get_total_points() == game.get_user_points() : 
                completed_games.append(game)
        
        return completed_games
    
    def get_completed_games_2(self, database_name : list[CEGame]) -> list[CEGame] :
        """Returns a list of :class:`CEGame`'s that this user has completed."""
        completed_games : list[CEGame] = []
        for game in database_name :
            for user_game in self.owned_games :
                if game.ce_id == user_game.ce_id and game.get_total_points() == user_game.get_user_points() :
                    completed_games.append(game)
        return completed_games
    
    @property
    def current_rolls(self) -> list[CERoll] :
        """Returns an array of :class:`CERoll`'s 
        that this user is currently participating in."""
        return self._current_rolls

    @property
    def completed_rolls(self) -> list[CERoll] :
        """Returns an array of :class:`CERoll`'s
        that this user has previously completed."""
        return self._completed_rolls
    
    @property
    def cooldowns(self) -> list[CECooldown] :
        """Returns an array of :class:`CECooldown`'s
        that this user currently has."""
        return self._cooldowns
    
    @property
    def pending_rolls(self) -> list[CECooldown] :
        """Returns an array of :class:`CECooldown`'s
        that this user stores in their Pending Rolls section."""
        return self._pending_rolls
    

    # ----------- setters -----------

    @discord_id.setter
    def discord_id(self, input : int) -> None :
        """Sets this object's Discord ID according to `input`."""
        self._discord_id = input

    @owned_games.setter
    def owned_games(self, games) :
        """Sets the 'owned games' to `games`."""
        self._owned_games = games

    def add_current_roll(self, roll : CERoll) -> None :
        """Adds `roll` to this user's Current Rolls section."""
        self._current_rolls.append(roll)
    
    def add_completed_roll(self, roll : CERoll) -> None :
        """Adds `roll` to this user's Completed Rolls section."""
        self._completed_rolls.append(roll)
    
    def add_cooldown(self, cooldown : CECooldown) -> None :
        """Adds `cooldown` to this user's Cooldowns section."""
        self._cooldowns.append(cooldown)

    def add_pending(self, pending : CECooldown) -> None :
        """Adds `pending` to this user's Pending section."""
        self._pending_rolls.append(pending)
    

    # ----------- other methods ------------

    def has_completed_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user has completed `roll_name`."""
        for event in self.completed_rolls :
            if event.roll_name == roll_name : return True
        return False
    
    def get_completed_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> CERoll :
        """Returns the `CERoll` associated with `roll_name`."""
        for event in self.completed_rolls :
            if event.roll_name ==roll_name : return event
        return None
    
    def has_current_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user is currently working on `roll_name`."""
        for event in self.current_rolls :
            if event.roll_name == roll_name : return True
        return False
    
    def get_current_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> CERoll :
        "REturns the `CERoll` associated with `roll_name`."
        for event in self.current_rolls :
            if event.roll_name == roll_name : return event
        return None
    
    def has_cooldown(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user is currently on cooldown for `roll_name`."""
        for cooldown in self.cooldowns :
            if cooldown.roll_name == roll_name : return True
        return False
    
    def get_cooldown_time(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> int :
        """Returns the unix timestamp of the date `roll_name`'s cooldown ends
        (or `None` if not applicable.)"""
        for cooldown in self.cooldowns :
            if cooldown.roll_name == roll_name : return cooldown.end_time
        return None
    
    def has_pending(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user is currently on pending for `roll_name`."""
        for pending in self.pending_rolls :
            if pending.roll_name == roll_name : return True
        return False
    
    def has_completed_game(self, game_id : str , database_name : list[CEGame]) :
        "Returns true if this user has completed this game, returns false otherwise."
        for user_game in self.owned_games :
            if user_game.ce_id == game_id :
                for game in database_name :
                    if game.ce_id == user_game.ce_id : return game.get_total_points() == user_game.get_user_points()
        return False

    def owns_game(self, game_id : str) -> bool :
        """Returns true if this user owns the game with 
        Challenge Enthusiast ID `game_id`."""
        for game in self.owned_games :
            if game.ce_id == game_id : return True
        return False
    
    def has_points(self, game_id : str) -> bool :
        """Returns true if this user has points in this game."""
        for game in self.owned_games :
            if game.ce_id == game_id : return game.get_user_points() != 0
        return False
    
    def get_ce_link(self) -> str :
        "Returns the link to this user's Challenge Enthusiasts page."
        return f"https://cedb.me/user/{self.ce_id}"
        
        
        
    

    def to_dict(self) -> dict :
        """Returns this user as a dictionary as used in the MongoDB database."""
        owned_games_array : list[dict] = []
        for game in self.owned_games :
            owned_games_array.append(game.to_dict())
        current_rolls_array : list[CERoll] = []
        for roll in self.current_rolls :
            current_rolls_array.append(roll.to_dict())
        completed_rolls_array : list[CERoll] = []
        for roll in self.completed_rolls :
            completed_rolls_array.append(roll.to_dict())
        cooldowns_array : list[CECooldown] = []
        for cooldown in self.cooldowns :
            cooldowns_array.append(cooldown.to_dict())
        pendings_array : list[CECooldown] = []
        for pending in self.pending_rolls :
            pendings_array.append(pending.to_dict())

        user_dict = {
            "CE ID" : self.ce_id,
            "Discord ID" : self.discord_id,
            "Casino Score" : self.casino_score,
            "Owned Games" : owned_games_array,
            "Current Rolls" : current_rolls_array,
            "Completed Rolls" : completed_rolls_array,
            "Cooldowns" : cooldowns_array,
            "Pending Rolls" : pendings_array
        }

        return user_dict
    
    def __str__(self) :
        "Returns the string representation about this CEUser."

        owned_games_array : list[dict] = []
        for game in self.owned_games :
            owned_games_array.append(game.to_dict())
        current_rolls_array : list[CERoll] = []
        for roll in self.current_rolls :
            current_rolls_array.append(roll.to_dict())
        completed_rolls_array : list[CERoll] = []
        for roll in self.completed_rolls :
            completed_rolls_array.append(roll.to_dict())
        cooldowns_array : list[CECooldown] = []
        for cooldown in self.cooldowns :
            cooldowns_array.append(cooldown.to_dict())
        pendings_array : list[CECooldown] = []
        for pending in self.pending_rolls :
            pendings_array.append(pending.to_dict())

        return (
            "-- CEUser --" +
            "\nCE ID: " + self.ce_id +
            "\nDiscord ID: " + self.discord_id +
            "\nCasino Score: " + self.casino_score +
            "\nOwned Games: " + str(owned_games_array) +
            "\nCurrent Rolls: " + str(current_rolls_array) +
            "\nCompleted Rolls: " + str(completed_rolls_array) +
            "\nCooldowns: " + str(cooldowns_array) +
            "\nPendings: " + str(pendings_array)
        )